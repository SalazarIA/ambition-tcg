from datetime import datetime
import sys
from pathlib import Path

PROJECT_ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORTS))

import traceback

from app import app, db
from models import User
from passlib.hash import pbkdf2_sha256

from services.match_actions_v1 import (
    create_training_match_v1,
    set_intent,
    play_card,
    declare_ready,
)
from services.arena_clean_state import build_arena_clean_state

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = PROJECT_ROOT / "reports" / "qa"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = REPORT_DIR / f"training_stress_{STAMP}.md"

TOTAL_MATCHES = 100
MAX_ROUNDS_PER_MATCH = 12
QA_EMAIL = "qa_training_stress@ambitionz.local"
QA_PASSWORD = "QaStress123!"


def get_or_create_user():
    user = User.query.filter_by(email=QA_EMAIL).first()

    if not user:
        user = User(
            username="qa_training_stress",
            email=QA_EMAIL,
            password_hash=pbkdf2_sha256.hash(QA_PASSWORD),
        )
        db.session.add(user)
        db.session.flush()

    user.username = "qa_training_stress"
    user.email = QA_EMAIL
    user.password_hash = pbkdf2_sha256.hash(QA_PASSWORD)
    user.is_verified = True

    if hasattr(user, "account_status"):
        user.account_status = "active"

    if hasattr(user, "coins"):
        user.coins = max(int(user.coins or 0), 1000)

    db.session.commit()
    return user


def compact_state(match, label):
    state = build_arena_clean_state(match, "p1", message=label)
    me = state.get("me") or {}
    enemy = state.get("enemy") or {}
    legal = state.get("legal_actions") or {}

    return {
        "phase": state.get("phase"),
        "round": state.get("round"),
        "message": state.get("message"),
        "me_hp": me.get("hp"),
        "enemy_hp": enemy.get("hp"),
        "me_energy": me.get("energy"),
        "hand": len(me.get("hand") or []),
        "field": me.get("field"),
        "playable": legal.get("playable_card_ids") or [],
        "can_ready": legal.get("can_ready"),
        "can_play_cards": legal.get("can_play_cards"),
    }


def first_playable_id(state):
    playable = state.get("playable") or []
    return playable[0] if playable else None


def run_one_match(user, match_number):
    logs = []
    result = {
        "match": match_number,
        "status": "PASS",
        "rounds_reached": 0,
        "cards_played": 0,
        "ready_count": 0,
        "errors": [],
        "logs": logs,
    }

    try:
        sid = f"qa_training_stress_sid_{match_number}"
        room_code = f"stress_{match_number:03d}"
        match = create_training_match_v1(user, sid, room_code)

        state = compact_state(match, "initial")
        logs.append(f"initial: {state}")

        if state["hand"] <= 0:
            raise AssertionError("initial hand is empty")

        if state["phase"] not in ("intent", "main"):
            raise AssertionError(f"unexpected initial phase: {state['phase']}")

        intents = ["Strike", "Guard", "Focus"]

        for round_index in range(1, MAX_ROUNDS_PER_MATCH + 1):
            current = compact_state(match, f"round_{round_index}_before")
            result["rounds_reached"] = max(result["rounds_reached"], int(current.get("round") or 0))

            intent = intents[(round_index - 1) % len(intents)]
            ok, msg = set_intent(match, "p1", intent)
            logs.append(f"round={round_index} set_intent {intent}: ok={ok} msg={msg}")

            after_intent = compact_state(match, f"round_{round_index}_after_intent")
            logs.append(f"after_intent: {after_intent}")

            card_id = first_playable_id(after_intent)

            if card_id:
                hand_before = after_intent["hand"]

                ok, msg = play_card(match, "p1", card_id)
                logs.append(f"round={round_index} play_card {card_id}: ok={ok} msg={msg}")

                after_play = compact_state(match, f"round_{round_index}_after_play")
                logs.append(f"after_play: {after_play}")

                if not ok:
                    raise AssertionError(f"play_card rejected playable card {card_id}: {msg}")

                if after_play["hand"] >= hand_before:
                    raise AssertionError(
                        f"hand did not decrease after play. before={hand_before} after={after_play['hand']}"
                    )

                result["cards_played"] += 1
            else:
                logs.append(f"round={round_index} no_playable_card")

            ok, msg = declare_ready(match, "p1")
            logs.append(f"round={round_index} declare_ready: ok={ok} msg={msg}")

            after_ready = compact_state(match, f"round_{round_index}_after_ready")
            logs.append(f"after_ready: {after_ready}")

            if not ok:
                raise AssertionError(f"declare_ready failed: {msg}")

            result["ready_count"] += 1
            result["rounds_reached"] = max(result["rounds_reached"], int(after_ready.get("round") or 0))

            if int(after_ready.get("me_hp") or 0) <= 0 or int(after_ready.get("enemy_hp") or 0) <= 0:
                logs.append("match_finished_by_hp")
                break

            if result["rounds_reached"] >= 4 and result["cards_played"] >= 2:
                logs.append("minimum_stability_target_reached")
                break

        if result["rounds_reached"] < 2:
            raise AssertionError("match did not advance beyond round 1")

        if result["cards_played"] < 1:
            raise AssertionError("no cards played during match")

    except Exception as exc:
        result["status"] = "FAIL"
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["logs"].append(traceback.format_exc())

    return result


def build_report(results):
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    total_cards = sum(r["cards_played"] for r in results)
    total_ready = sum(r["ready_count"] for r in results)
    max_round = max((r["rounds_reached"] for r in results), default=0)

    lines = [
        "# Ambitionz Training Stress QA",
        "",
        f"- Generated: {STAMP}",
        f"- Matches requested: {TOTAL_MATCHES}",
        f"- Passed: {len(passed)}",
        f"- Failed: {len(failed)}",
        f"- Total cards played: {total_cards}",
        f"- Total ready actions: {total_ready}",
        f"- Max round reached: {max_round}",
        f"- Overall: {'PASS' if not failed else 'FAIL'}",
        "",
        "## Summary Matrix",
        "",
        "| Match | Status | Rounds Reached | Cards Played | Ready Count | Errors |",
        "|---:|---:|---:|---:|---:|---|",
    ]

    for r in results:
        errors = " / ".join(r["errors"]) if r["errors"] else ""
        lines.append(
            f"| {r['match']} | {r['status']} | {r['rounds_reached']} | "
            f"{r['cards_played']} | {r['ready_count']} | {errors} |"
        )

    if failed:
        lines.extend([
            "",
            "## Failure Details",
            "",
        ])

        for r in failed:
            lines.extend([
                f"### Match {r['match']}",
                "",
                "```text",
                "\n".join(r["logs"][-80:]),
                "```",
                "",
            ])

    else:
        lines.extend([
            "",
            "## Result",
            "",
            "All stress matches reached the minimum stability target.",
        ])

    REPORT.write_text("\n".join(lines))
    return REPORT, not failed


def main():
    with app.app_context():
        user = get_or_create_user()
        results = []

        for i in range(1, TOTAL_MATCHES + 1):
            result = run_one_match(user, i)
            results.append(result)

            status = result["status"]
            print(
                f"{i:03d}/{TOTAL_MATCHES} {status} "
                f"rounds={result['rounds_reached']} "
                f"cards={result['cards_played']} "
                f"ready={result['ready_count']}"
            )

            db.session.rollback()

        report, ok = build_report(results)
        print("")
        print(f"REPORT={report}")
        print(f"RESULT={'PASS' if ok else 'FAIL'}")

        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()

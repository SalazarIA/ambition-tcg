#!/usr/bin/env python3
"""Drive N full guest battles against the LIVE production API and capture
QA telemetry: timing, turn flow, winners, errors, edge cases.

This is a senior-QA harness — it plays real matches through the same HTTP
contract the browser uses, so engine behavior, pacing and state transitions
are genuine production data (no simulator shortcuts).

Usage:
    .venv/bin/python tools/qa/qa_production_battle_driver.py --base https://ambitionzgame.com --battles 10
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request


def _req(method, url, *, cookie=None, csrf=None, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if csrf:
        headers["X-Rebirth-CSRF"] = csrf
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.perf_counter() - t0) * 1000
            set_cookie = resp.headers.get("Set-Cookie")
            payload = json.loads(resp.read().decode())
            return {"ok": True, "status": resp.status, "ms": elapsed, "json": payload, "set_cookie": set_cookie}
    except urllib.error.HTTPError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        try:
            payload = json.loads(exc.read().decode())
        except Exception:
            payload = {"raw": "unparseable"}
        return {"ok": False, "status": exc.code, "ms": elapsed, "json": payload, "set_cookie": None}
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return {"ok": False, "status": 0, "ms": elapsed, "json": {"error": str(exc)}, "set_cookie": None}


def _cookie_from(resp, current):
    sc = resp.get("set_cookie")
    if not sc:
        return current
    return sc.split(";", 1)[0]


def play_battle(base, index, edge_mode=False):
    log = {"index": index, "errors": [], "actions": 0, "summons": 0, "attacks": 0, "turns": 0,
           "winner": None, "finished": False, "action_ms": [], "edge_attempts": []}

    # CSRF + session
    r = _req("GET", f"{base}/api/rebirth/csrf")
    if not r["ok"]:
        log["errors"].append(f"csrf_failed status={r['status']}")
        return log
    cookie = _cookie_from(r, None)
    csrf = r["json"].get("csrf")

    # Start guest match
    r = _req("POST", f"{base}/api/rebirth/start", cookie=cookie, csrf=csrf, body={"tutorial": False})
    cookie = _cookie_from(r, cookie)
    if not r["ok"]:
        log["errors"].append(f"start_failed status={r['status']} {r['json']}")
        return log
    state = r["json"]["state"]
    match_id = state["match_id"]
    log["bot_profile"] = state.get("bot_profile", {}).get("id")

    # Edge-case probes on battle 1 + 6 — try to break flows
    if edge_mode:
        # 1. Attack with no units (should reject cleanly)
        e = _req("POST", f"{base}/api/rebirth/attack", cookie=cookie, csrf=csrf,
                 body={"match_id": match_id, "attacker_instance_id": "ghost", "target_instance_id": None})
        log["edge_attempts"].append({"probe": "attack_ghost_unit", "status": e["status"], "code": e["json"].get("error", {}).get("code")})
        # 2. Play a card not in hand
        e = _req("POST", f"{base}/api/rebirth/play-card", cookie=cookie, csrf=csrf,
                 body={"match_id": match_id, "card_id": "card_999"})
        log["edge_attempts"].append({"probe": "summon_nonexistent_card", "status": e["status"], "code": e["json"].get("error", {}).get("code")})
        # 3. Inject authoritative combat field (should be rejected)
        e = _req("POST", f"{base}/api/rebirth/play-card", cookie=cookie, csrf=csrf,
                 body={"match_id": match_id, "card_id": "card_001", "damage": 9999, "winner": "player"})
        log["edge_attempts"].append({"probe": "inject_authoritative_fields", "status": e["status"], "code": e["json"].get("error", {}).get("code")})
        # 4. Operate on bogus match_id
        e = _req("POST", f"{base}/api/rebirth/next-turn", cookie=cookie, csrf=csrf, body={"match_id": "does-not-exist"})
        log["edge_attempts"].append({"probe": "bogus_match_id", "status": e["status"], "code": e["json"].get("error", {}).get("code")})

    max_turns = 60
    guard = 0
    while not state.get("is_finished") and guard < max_turns * 4:
        guard += 1
        phase = state.get("phase")
        player = state.get("player", {})
        energy = int(player.get("energy", 0) or 0)
        hand = player.get("hand", [])
        field = [c for c in (player.get("field") or player.get("battlefield") or []) if c]
        bot_field = [c for c in (state.get("bot_field") or (state.get("bot", {}).get("field")) or []) if c]

        acted = False

        # Try to summon the strongest affordable card into an empty slot
        if phase == "choose":
            affordable = sorted(
                [c for c in hand if int(c.get("cost", 1) or 1) <= energy and c.get("card_type", c.get("type")) in (None, "monster", "MONSTER") or int(c.get("attack", 0) or 0) > 0],
                key=lambda c: -int(c.get("attack", 0) or 0),
            )
            occupied = len(field)
            if affordable and occupied < 3:
                card = affordable[0]
                r = _req("POST", f"{base}/api/rebirth/play-card", cookie=cookie, csrf=csrf,
                         body={"match_id": match_id, "card_instance_id": card.get("instance_id"), "field_slot": occupied})
                cookie = _cookie_from(r, cookie)
                log["action_ms"].append(r["ms"])
                log["actions"] += 1
                if r["ok"]:
                    log["summons"] += 1
                    state = r["json"].get("state", state)
                    acted = True
                else:
                    log["errors"].append(f"summon t{state.get('turn')} status={r['status']} {r['json'].get('error',{}).get('code')}")

        # Attack with ready units
        if not acted:
            state_field = [c for c in (state.get("player", {}).get("field") or state.get("player", {}).get("battlefield") or []) if c]
            ready = [c for c in state_field if not c.get("has_attacked") and not c.get("exhausted") and not c.get("has_acted")]
            if ready and state.get("phase") in ("choose", "combat", "main"):
                attacker = ready[0]
                target_field = [c for c in (state.get("bot_field") or state.get("bot", {}).get("field") or []) if c]
                target_id = target_field[0].get("instance_id") if target_field else None
                r = _req("POST", f"{base}/api/rebirth/attack", cookie=cookie, csrf=csrf,
                         body={"match_id": match_id, "attacker_instance_id": attacker.get("instance_id"), "target_instance_id": target_id})
                cookie = _cookie_from(r, cookie)
                log["action_ms"].append(r["ms"])
                log["actions"] += 1
                if r["ok"]:
                    log["attacks"] += 1
                    state = r["json"].get("state", state)
                    acted = True
                else:
                    # attack rejected (e.g. first-turn direct block) — fall through to end turn
                    code = r["json"].get("error", {}).get("code")
                    if code not in ("direct_attack_blocked", "first_turn_no_direct"):
                        log["errors"].append(f"attack t{state.get('turn')} status={r['status']} {code}")

        # End turn
        if not acted:
            r = _req("POST", f"{base}/api/rebirth/next-turn", cookie=cookie, csrf=csrf, body={"match_id": match_id})
            cookie = _cookie_from(r, cookie)
            log["action_ms"].append(r["ms"])
            log["actions"] += 1
            if r["ok"]:
                state = r["json"].get("state", state)
                log["turns"] = state.get("turn", log["turns"])
            else:
                log["errors"].append(f"next_turn t{state.get('turn')} status={r['status']} {r['json'].get('error',{}).get('code')}")
                break

    log["finished"] = bool(state.get("is_finished"))
    log["winner"] = state.get("winner")
    log["turns"] = state.get("turn", log["turns"])
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://ambitionzgame.com")
    ap.add_argument("--battles", type=int, default=10)
    args = ap.parse_args()

    results = []
    for i in range(args.battles):
        edge = i in (0, 5)  # edge probes on battle 1 and 6
        res = play_battle(args.base, i + 1, edge_mode=edge)
        results.append(res)
        status = "FIN" if res["finished"] else "INCOMPLETE"
        print(f"Battle {i+1:2d} [{res.get('bot_profile','?'):>11}]: {status} winner={res['winner']} turns={res['turns']} "
              f"actions={res['actions']} (summon={res['summons']} atk={res['attacks']}) errors={len(res['errors'])}")
        if res["errors"]:
            for e in res["errors"][:3]:
                print(f"        ERR: {e}")
        if res.get("edge_attempts"):
            for ea in res["edge_attempts"]:
                print(f"        EDGE {ea['probe']}: HTTP {ea['status']} code={ea['code']}")

    all_ms = [ms for r in results for ms in r["action_ms"]]
    finished = [r for r in results if r["finished"]]
    turns = [r["turns"] for r in finished]
    player_wins = sum(1 for r in finished if r["winner"] == "player")
    bot_wins = sum(1 for r in finished if r["winner"] == "bot")
    print("\n=== AGGREGATE ===")
    print(f"battles={len(results)} finished={len(finished)} incomplete={len(results)-len(finished)}")
    if turns:
        print(f"turns: avg={statistics.fmean(turns):.1f} min={min(turns)} max={max(turns)}")
    print(f"outcomes: player={player_wins} bot={bot_wins} other={len(finished)-player_wins-bot_wins}")
    if all_ms:
        all_ms.sort()
        print(f"action latency (ms): p50={all_ms[len(all_ms)//2]:.0f} p90={all_ms[int(len(all_ms)*0.9)]:.0f} "
              f"p99={all_ms[int(len(all_ms)*0.99)]:.0f} max={all_ms[-1]:.0f}")
    total_errors = sum(len(r["errors"]) for r in results)
    print(f"total errors: {total_errors}")


if __name__ == "__main__":
    main()

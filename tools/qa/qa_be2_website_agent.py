# =========================================================
# Ambitionz BE2 Website Agent QA
# Tests Arena Clean live Socket.IO flow against Battle Engine V2.
# =========================================================

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import socketio
except Exception as error:
    print("FAIL: python-socketio import failed:", type(error).__name__, error)
    raise SystemExit(1)


SERVER_URL = "http://127.0.0.1:8080"
TIMEOUT = 8


class Agent:
    def __init__(self):
        self.sio = socketio.Client(reconnection=False, logger=False, engineio_logger=False)
        self.states = []
        self.logs = []
        self.errors = []
        self.game_over = []

        @self.sio.event
        def connect():
            print("PASS connected")

        @self.sio.event
        def disconnect():
            print("INFO disconnected")

        @self.sio.on("az48_state")
        def on_az48_state(payload):
            self.states.append(payload)
            me = payload.get("me") or {}
            enemy = payload.get("enemy") or {}
            field = me.get("field") or {}
            enemy_preview = payload.get("enemy_preview") or {}

            print(
                "STATE",
                "engine=", payload.get("engine"),
                "round=", payload.get("round"),
                "phase=", payload.get("phase"),
                "hp=", me.get("hp"),
                "enemy_hp=", enemy.get("hp"),
                "hand=", me.get("hand_count"),
                "active=", ((field.get("monster") or {}).get("name") if field.get("monster") else None),
                "preview=", enemy_preview.get("intent"),
                "winner=", payload.get("winner"),
            )

        @self.sio.on("battle_log")
        def on_battle_log(payload):
            self.logs.append(payload)
            print("LOG", payload)

        @self.sio.on("action_error")
        def on_action_error(payload):
            self.errors.append(payload)
            print("ACTION_ERROR", payload)

        @self.sio.on("game_over")
        def on_game_over(payload):
            self.game_over.append(payload)
            print("GAME_OVER", payload)

    def connect(self):
        self.sio.connect(SERVER_URL, transports=["polling"], wait_timeout=TIMEOUT)

    def emit(self, event, payload=None):
        payload = payload or {}
        print("EMIT", event, payload)
        self.sio.emit(event, payload)
        time.sleep(0.45)

    def latest_state(self):
        if not self.states:
            raise AssertionError("No az48_state received.")
        return self.states[-1]

    def assert_clean_state(self, state):
        assert state.get("schema") == "arena_state_v50", "Invalid schema"
        assert state.get("legacy_schema") == "ambitionz_arena_clean_v50", "Missing legacy schema marker"
        assert state.get("engine") == "battle_engine_v2", f"Not using battle_engine_v2: {state.get('engine')}"
        assert state.get("me"), "Missing me payload"
        assert state.get("enemy"), "Missing enemy payload"
        assert state.get("legal_actions"), "Missing legal_actions payload"
        assert "help" in state, "Missing help payload"

    def choose_intent(self, state):
        me = state.get("me") or {}
        enemy = state.get("enemy") or {}

        if me.get("hp", 0) <= 10:
            return "Guard"

        if me.get("ambition", 0) >= state.get("unleash_cost", 10):
            return "Strike"

        if enemy.get("hp", 0) <= 10:
            return "Strike"

        return "Strike"

    def choose_card(self, state):
        legal = state.get("legal_actions") or {}
        playable = [str(x) for x in (legal.get("playable_card_ids") or [])]
        hand = (state.get("me") or {}).get("hand") or []

        if not playable:
            return None

        playable_cards = [card for card in hand if str(card.get("id")) in playable]

        if not playable_cards:
            return playable[0]

        # Priority for readable card battler flow:
        # 1. summon creature if no active creature
        # 2. lethal/direct damage spell
        # 3. support
        # 4. guard if low HP
        # 5. any strong card
        me = state.get("me") or {}
        field = me.get("field") or {}
        has_active = bool(field.get("monster"))

        if not has_active:
            creatures = [c for c in playable_cards if c.get("kind") == "creature" or c.get("sigil") == "Creature"]
            if creatures:
                creatures.sort(key=lambda c: (c.get("atk", 0) + c.get("max_hp", 0), -c.get("cost", 0)), reverse=True)
                return creatures[0].get("id")

        if me.get("hp", 0) <= 10:
            guards = [c for c in playable_cards if c.get("kind") == "guard" or c.get("sigil") == "Guard"]
            if guards:
                guards.sort(key=lambda c: (c.get("display_stat", 0), -c.get("cost", 0)), reverse=True)
                return guards[0].get("id")

        supports = [c for c in playable_cards if c.get("kind") == "support" or c.get("sigil") == "Support"]
        if supports and not ((field.get("spell") or {}).get("name")):
            return supports[0].get("id")

        playable_cards.sort(key=lambda c: (c.get("display_stat", 0), -c.get("cost", 0)), reverse=True)
        return playable_cards[0].get("id")

    def run(self):
        self.connect()

        self.emit("az48_start_training")
        state = self.latest_state()
        self.assert_clean_state(state)

        assert state["phase"] in {"round_start", "choose_action"}, f"Unexpected phase after start: {state['phase']}"
        assert state["me"]["hand_count"] >= 5, "Expected starting hand"
        assert state["round"] >= 1, "Expected round >= 1"

        rounds_seen = set()
        hp_pairs = []
        active_seen = False

        for step in range(18):
            state = self.latest_state()
            self.assert_clean_state(state)

            if state.get("winner"):
                break

            rounds_seen.add(state.get("round"))
            hp_pairs.append((state["me"]["hp"], state["enemy"]["hp"]))

            me_field = (state.get("me") or {}).get("field") or {}
            if me_field.get("monster"):
                active_seen = True

            legal = state.get("legal_actions") or {}

            if legal.get("can_unleash"):
                self.emit("az48_unleash")

            intent = self.choose_intent(state)
            self.emit("az48_set_intent", {"intent": intent})

            state = self.latest_state()
            card_id = self.choose_card(state)

            if card_id:
                self.emit("az48_play_card", {"card_id": card_id})
            else:
                print("INFO no playable card this round; pressing ready")

            self.emit("az48_declare_ready")

            if self.errors:
                raise AssertionError(f"Action errors received: {self.errors}")

        state = self.latest_state()
        self.assert_clean_state(state)

        assert len(self.states) >= 4, "Too few state updates"
        assert len(rounds_seen) >= 2 or state.get("winner"), "Round did not advance"
        assert self.errors == [], f"Action errors received: {self.errors}"

        hp_changed = any(pair != hp_pairs[0] for pair in hp_pairs[1:]) if len(hp_pairs) > 1 else False
        assert hp_changed or state.get("winner"), "HP did not change during duel"

        summaries = [
            s.get("round_summary") for s in self.states
            if isinstance(s.get("round_summary"), dict) and s.get("round_summary", {}).get("lines")
        ]
        assert summaries, "No round_summary with explanation lines was observed"
        print("ROUND SUMMARY SAMPLE:", summaries[-1].get("short_result"))
        for line in summaries[-1].get("lines", [])[:4]:
            print("SUMMARY LINE:", line)

        if not active_seen:
            final_field = (state.get("me") or {}).get("field") or {}
            active_seen = bool(final_field.get("monster"))

        assert active_seen or state.get("winner"), "No active creature was observed"

        if not state.get("winner"):
            print("WARN match not finished within agent loop, but state advanced correctly")
        else:
            print("PASS match finished with winner:", state.get("winner"), "reason:", state.get("reason"))

        print("")
        print("=== AGENT RESULT ===")
        print("PASS BE2 website socket flow")
        print("states_received:", len(self.states))
        print("logs_received:", len(self.logs))
        print("final_round:", state.get("round"))
        print("final_phase:", state.get("phase"))
        print("final_winner:", state.get("winner"))

        self.sio.disconnect()


if __name__ == "__main__":
    try:
        Agent().run()
    except Exception as error:
        print("")
        print("=== AGENT RESULT ===")
        print("FAIL", type(error).__name__, error)
        raise SystemExit(1)

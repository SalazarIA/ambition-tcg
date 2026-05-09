# =========================================================
# Ambitionz BE1 Website Agent QA
# Tests the live local server through Socket.IO events used by Arena Clean.
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
            print(
                "STATE",
                "engine=", payload.get("engine"),
                "round=", payload.get("round"),
                "phase=", payload.get("phase"),
                "hp=", (payload.get("me") or {}).get("hp"),
                "enemy_hp=", (payload.get("enemy") or {}).get("hp"),
                "hand=", (payload.get("me") or {}).get("hand_count"),
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
        assert state.get("schema") == "ambitionz_arena_clean_v50", "Invalid schema"
        assert state.get("engine") == "battle_engine_v1", "Not using battle_engine_v1"
        assert state.get("me"), "Missing me payload"
        assert state.get("enemy"), "Missing enemy payload"
        assert state.get("legal_actions"), "Missing legal_actions payload"

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

        for step in range(12):
            state = self.latest_state()
            self.assert_clean_state(state)

            if state.get("winner"):
                break

            rounds_seen.add(state.get("round"))
            hp_pairs.append((state["me"]["hp"], state["enemy"]["hp"]))

            self.emit("az48_set_intent", {"intent": "Strike"})

            state = self.latest_state()
            legal = state.get("legal_actions") or {}
            playable = legal.get("playable_card_ids") or []

            if playable:
                self.emit("az48_play_card", {"card_id": playable[0]})
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

        if not state.get("winner"):
            print("WARN match not finished within agent loop, but state advanced correctly")
        else:
            print("PASS match finished with winner:", state.get("winner"), "reason:", state.get("reason"))

        print("")
        print("=== AGENT RESULT ===")
        print("PASS BE1 website socket flow")
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


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_pvp_socket_flow():
    logs = []
    failures = []

    try:
        from app import app, socketio
        from models import User, db
        from passlib.hash import pbkdf2_sha256

        with app.app_context():
            users = []

            for idx in [1, 2]:
                email = f"qa_pvp_{idx}@ambitionz.local"
                username = f"qa_pvp_{idx}"

                user = User.query.filter_by(email=email).first()

                if not user:
                    user = User(username=username, email=email)
                    db.session.add(user)
                    db.session.flush()

                user.username = username
                user.email = email
                user.password_hash = pbkdf2_sha256.hash("QaPvp123!")

                if hasattr(user, "is_verified"):
                    user.is_verified = True

                if hasattr(user, "account_status"):
                    user.account_status = "active"

                try:
                    from services.economy.inventory_migration import repair_user_inventory_and_deck
                    repair_user_inventory_and_deck(user)
                except Exception as exc:
                    logs.append(f"repair_user_{idx}_skip={type(exc).__name__}: {exc}")

                users.append(user)

            db.session.commit()

            u1_id = users[0].id
            u2_id = users[1].id

        flask_client_1 = app.test_client()
        flask_client_2 = app.test_client()

        with flask_client_1.session_transaction() as session:
            session["user_id"] = u1_id

        with flask_client_2.session_transaction() as session:
            session["user_id"] = u2_id

        c1 = socketio.test_client(app, flask_test_client=flask_client_1)
        c2 = socketio.test_client(app, flask_test_client=flask_client_2)

        logs.append(f"c1_connected={c1.is_connected()}")
        logs.append(f"c2_connected={c2.is_connected()}")

        if not c1.is_connected():
            failures.append("socket client 1 failed to connect")

        if not c2.is_connected():
            failures.append("socket client 2 failed to connect")

        # Private room smoke.
        room = "QA77A"

        c1.emit("join_private_room", {"room_code": room, "room": room})
        c2.emit("join_private_room", {"room_code": room, "room": room})

        r1_private = c1.get_received()
        r2_private = c2.get_received()

        logs.append(f"private_room_c1_events={r1_private}")
        logs.append(f"private_room_c2_events={r2_private}")

        # Queue smoke fallback.
        c1.emit("join_queue", {})
        c2.emit("join_queue", {})

        r1_queue = c1.get_received()
        r2_queue = c2.get_received()

        logs.append(f"queue_c1_events={r1_queue}")
        logs.append(f"queue_c2_events={r2_queue}")

        all_events = r1_private + r2_private + r1_queue + r2_queue

        useful_names = {
            "presence_update",
            "queue_update",
            "game_state_update",
            "match_state",
            "az48_state",
            "battle_log",
            "action_error",
        }

        useful = [
            pkt for pkt in all_events
            if pkt.get("name") in useful_names
        ]

        logs.append(f"useful_event_count={len(useful)}")
        logs.append(f"useful_events={useful[:30]}")

        if len(useful) <= 0:
            failures.append("PVP socket generated no useful events")

        action_errors = [pkt for pkt in all_events if pkt.get("name") == "action_error"]
        logs.append(f"action_errors={action_errors}")

        c1.disconnect()
        c2.disconnect()

        return {
            "name": "pvp_socket_flow",
            "status": "FAIL" if failures else "PASS",
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "pvp_socket_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }

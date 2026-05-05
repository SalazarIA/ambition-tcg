import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text

from app import app
from models import db


def table_exists(engine, table_name):
    return table_name in inspect(engine).get_table_names()


def scalar(connection, query, default=0):
    try:
        value = connection.execute(text(query)).scalar()
        return value if value is not None else default
    except Exception:
        return default


def rows(connection, query):
    try:
        return [dict(row._mapping) for row in connection.execute(text(query)).fetchall()]
    except Exception:
        return []


def main():
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = report_dir / f"balance_snapshot_{timestamp}.md"

    with app.app_context():
        engine = db.engine

        with engine.connect() as connection:
            has_match_history = table_exists(engine, "match_history") or table_exists(engine, "match_histories")
            match_table = "match_history" if table_exists(engine, "match_history") else "match_histories"

            total_users = scalar(connection, "SELECT COUNT(*) FROM users", 0) if table_exists(engine, "users") else 0
            total_matches = scalar(connection, f"SELECT COUNT(*) FROM {match_table}", 0) if has_match_history else 0

            result_rows = []
            average_rounds = 0
            recent_matches = []

            if has_match_history:
                result_rows = rows(
                    connection,
                    f"""
                    SELECT result, COUNT(*) AS total
                    FROM {match_table}
                    GROUP BY result
                    ORDER BY total DESC
                    """
                )

                average_rounds = scalar(
                    connection,
                    f"SELECT ROUND(AVG(total_rounds), 2) FROM {match_table}",
                    0,
                )

                recent_matches = rows(
                    connection,
                    f"""
                    SELECT id, player1_name, player2_name, winner_name, result,
                           player1_final_hp, player2_final_hp, total_rounds
                    FROM {match_table}
                    ORDER BY id DESC
                    LIMIT 12
                    """
                )

            lines = []
            lines.append("# Ambitionz Balance Snapshot")
            lines.append("")
            lines.append(f"- Generated UTC: `{timestamp}`")
            lines.append(f"- Total users: **{total_users}**")
            lines.append(f"- Total matches: **{total_matches}**")
            lines.append(f"- Average rounds: **{average_rounds}**")
            lines.append("")

            lines.append("## Result Distribution")
            lines.append("")
            if result_rows:
                lines.append("| Result | Total |")
                lines.append("|---|---:|")
                for row in result_rows:
                    lines.append(f"| {row.get('result') or 'UNKNOWN'} | {row.get('total', 0)} |")
            else:
                lines.append("No match result data yet.")

            lines.append("")
            lines.append("## Recent Matches")
            lines.append("")
            if recent_matches:
                lines.append("| ID | P1 | P2 | Winner | Result | HP | Rounds |")
                lines.append("|---:|---|---|---|---|---|---:|")
                for row in recent_matches:
                    hp = f"{row.get('player1_final_hp', 0)} / {row.get('player2_final_hp', 0)}"
                    lines.append(
                        f"| {row.get('id')} | {row.get('player1_name')} | {row.get('player2_name')} | "
                        f"{row.get('winner_name') or '-'} | {row.get('result')} | {hp} | {row.get('total_rounds')} |"
                    )
            else:
                lines.append("No recent matches yet.")

            lines.append("")
            lines.append("## Balance Reading Guide")
            lines.append("")
            lines.append("- Ideal early beta average match length: **3 to 8 rounds**.")
            lines.append("- Too many 1-2 round matches means damage or tempo may be too high.")
            lines.append("- Too many 10+ round matches means defensive tools, HP or low damage may be too strong.")
            lines.append("- High draw rate means resolution or lethal pressure may need review.")
            lines.append("- Bot win/loss should be reviewed separately by difficulty once enough data exists.")
            lines.append("")

            output_path.write_text("\n".join(lines))

            print(f"Balance snapshot created: {output_path}")


if __name__ == "__main__":
    main()

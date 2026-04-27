from pathlib import Path
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import app
from models import MatchTelemetry


def generate_report():
    with app.app_context():
        rows = MatchTelemetry.query.order_by(MatchTelemetry.id.desc()).limit(500).all()

        total = len(rows)
        modes = Counter(row.mode for row in rows)
        difficulties = Counter(row.bot_difficulty or "none" for row in rows)
        winners = Counter(row.winner_name or "Unknown" for row in rows)
        avg_rounds = round(sum(row.rounds for row in rows) / total, 2) if total else 0

        lines = []
        lines.append("# Ambitionz V1.05 Match Telemetry Report\n")
        lines.append(f"- Matches analyzed: {total}")
        lines.append(f"- Average rounds: {avg_rounds}\n")

        lines.append("## Modes\n")
        for key, value in modes.most_common():
            lines.append(f"- {key}: {value}")

        lines.append("\n## Bot Difficulties\n")
        for key, value in difficulties.most_common():
            lines.append(f"- {key}: {value}")

        lines.append("\n## Top Winners\n")
        for key, value in winners.most_common(20):
            lines.append(f"- {key}: {value}")

        lines.append("\n## Recent Matches\n")
        for row in rows[:50]:
            lines.append(
                f"- #{row.id} mode={row.mode} winner={row.winner_name} loser={row.loser_name} "
                f"rounds={row.rounds} winner_hp={row.winner_hp} loser_hp={row.loser_hp} "
                f"difficulty={row.bot_difficulty} reason={row.ending_reason}"
            )

        return "\n".join(lines) + "\n"


def main():
    output_path = Path("reports/match_telemetry_report_v105.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report()
    output_path.write_text(report, encoding="utf-8")

    print(f"Match telemetry report written to {output_path}")
    print(report)


if __name__ == "__main__":
    main()

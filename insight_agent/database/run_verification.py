"""Execute the six human-readable SQL checks and save tabular evidence."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from .db_connection import connect

CHECK_PATTERN = re.compile(r"^-- check:\s*(.+)$", re.MULTILINE)


def parse_checks(sql_text: str) -> list[tuple[str, str]]:
    matches = list(CHECK_PATTERN.finditer(sql_text))
    checks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(sql_text)
        statement = sql_text[start:end].strip()
        if statement.endswith(";"):
            statement = statement[:-1]
        checks.append((match.group(1).strip(), statement))
    return checks


def execute_checks(sql_path: Path) -> str:
    checks = parse_checks(sql_path.read_text(encoding="utf-8"))
    if len(checks) != 6:
        raise ValueError(f"Expected 6 SQL checks, found {len(checks)}")
    sections: list[str] = []
    connection = connect()
    try:
        with connection.cursor() as cursor:
            for title, statement in checks:
                cursor.execute(statement)
                headers = [column.name for column in cursor.description]
                rows = cursor.fetchall()
                sections.append(f"## {title}")
                sections.append("\t".join(headers))
                sections.extend("\t".join(str(value) for value in row) for row in rows)
                sections.append("")
    finally:
        connection.close()
    return "\n".join(sections).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sql",
        type=Path,
        default=Path(__file__).resolve().parent / "verify_anomalies.sql",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = execute_checks(args.sql)
    print(output, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
import json
import re
import sys
from datetime import date
from pathlib import Path

def main() -> int:
    loop_dir = Path.cwd()
    decisions = (loop_dir / ".." / ".." / ".about" / "decisions").resolve()
    if not decisions.is_dir():
        print(f"decisions directory not found: {decisions}", file=sys.stderr)
        return 1

    status_re = re.compile(r"^status: Proposed", re.MULTILINE)
    heading_re = re.compile(r"^# (Decision Record.*)$", re.MULTILINE)

    headings = []
    for path in sorted(decisions.glob("[0-9]*.md")):
        text = path.read_text(encoding="utf-8")
        if not status_re.search(text):
            continue
        m = heading_re.search(text)
        if m:
            headings.append(m.group(1).rstrip())
        else:
            print(f"no Decision Record heading in {path.name}", file=sys.stderr)
            return 1

    lines = [date.today().isoformat(), str(len(headings)), *headings]
    (loop_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "effects": ["report.md"],
        "summary": f"Wrote report.md with {len(headings)} proposed decision record(s).",
    }))
    return 0

if __name__ == "__main__":
    sys.exit(main())

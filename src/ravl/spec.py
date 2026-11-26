"""Read a loop specification (`ravl.md`).

The specification is plain language. The library reads three things from it and
nothing else: the title, the Intent section, and the Verifier section's criteria.
A criterion may carry a fenced `check` block: a shell script whose exit status
decides the criterion (0 passes). Everything else in the file is for the owner and
for the LLM that performs Act, which is given the whole file.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

SPEC_FILE = "ravl.md"

TEMPLATE = """\
# {name}

## Intent

Describe the outcome that must hold after a run, in plain language. Say what it
is for, so that a run which cannot produce it knows what to ask the owner.

## Verifier

Criteria that decide whether the outcome was achieved, one per bullet. A fenced
`check` block under a criterion is run from the loop directory; exit status 0
means the criterion passes. A criterion without a check is recorded as unchecked.

- Replace this with the first criterion.
  ```check
  false
  ```
"""


class SpecError(Exception):
    """The loop directory holds no readable specification."""


@dataclass
class Criterion:
    id: str
    text: str
    check: str | None


@dataclass
class Spec:
    path: Path
    title: str
    intent: str
    criteria: list[Criterion]
    raw: str


def is_loop(directory: Path) -> bool:
    return (directory / SPEC_FILE).is_file()


def _sections(text: str) -> dict[str, str]:
    """Split on level-2 headings, ignoring headings inside fenced blocks."""
    out: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
        m = None if fenced else re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def _criteria(body: str) -> list[Criterion]:
    items: list[dict] = []
    current: dict | None = None
    fence: str | None = None
    buffer: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if fence is not None:
            if stripped.startswith("```"):
                if fence == "check" and current is not None:
                    current["check"] = textwrap.dedent("\n".join(buffer)).strip()
                fence, buffer = None, []
            else:
                buffer.append(line)
            continue
        if stripped.startswith("```"):
            fence, buffer = stripped[3:].strip().lower(), []
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", line)
        if bullet:
            current = {"text": bullet.group(1).strip(), "check": None}
            items.append(current)
        elif current is not None and stripped and line[:1] in (" ", "\t"):
            current["text"] += " " + stripped
    out = []
    for item in items:
        text = re.sub(r"\s+", " ", item["text"]).strip()
        key = hashlib.sha1(text.lower().encode()).hexdigest()[:8]
        out.append(Criterion(id=f"c-{key}", text=text, check=item["check"] or None))
    return out


def load(loop_dir: Path) -> Spec:
    path = Path(loop_dir) / SPEC_FILE
    if not path.is_file():
        raise SpecError(f"no {SPEC_FILE} in {loop_dir}")
    raw = path.read_text()
    title = next((m.group(1).strip() for m in [re.search(r"(?m)^#\s+(.+)$", raw)] if m),
                 Path(loop_dir).name)
    sections = _sections(raw)
    return Spec(path=path, title=title, intent=sections.get("intent", ""),
                criteria=_criteria(sections.get("verifier", "")), raw=raw)

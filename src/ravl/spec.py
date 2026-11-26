"""Read a loop specification (`ravl.md`).

The specification is plain language. The library reads three things from it and
nothing else: the title, the Intent section, and the Verifier section's criteria.
When the specification gives no criteria, they are read from `verifier.md` beside it,
which the first run derives from the intent and the loop's parent edits afterwards.
A criterion may carry a fenced `check` block: a shell script whose exit status
decides the criterion (0 passes). An optional Act section may carry a fenced `act`
block: the owner's own implementation of Act, run on every run in place of an LLM.
Everything else in the file is for the owner and for the LLM that performs or
repairs Act, which is given the whole file.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path

SPEC_FILE = "ravl.md"
VERIFIER_FILE = "verifier.md"   # criteria assumed from the intent, kept beside the specification

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
    act: str | None = None   # the owner's implementation, when the specification carries one
    verifier_source: str = "none"     # "specification" | "file" | "none"
    verifier_raw: str | None = None   # text of verifier.md when the criteria came from it


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


def _act(body: str) -> str | None:
    """The first fenced `act` block of the Act section: a shell script that performs Act."""
    match = re.search(r"(?ms)^[ \t]*```act[ \t]*\n(.*?)^[ \t]*```[ \t]*$", body)
    if not match:
        return None
    return textwrap.dedent(match.group(1)).strip() or None


def load(loop_dir: Path) -> Spec:
    path = Path(loop_dir) / SPEC_FILE
    if not path.is_file():
        raise SpecError(f"no {SPEC_FILE} in {loop_dir}")
    raw = path.read_text()
    title = next((m.group(1).strip() for m in [re.search(r"(?m)^#\s+(.+)$", raw)] if m),
                 Path(loop_dir).name)
    sections = _sections(raw)
    criteria = _criteria(sections.get("verifier", ""))
    source, verifier_raw = ("specification" if criteria else "none"), None
    verifier_file = Path(loop_dir) / VERIFIER_FILE
    if not criteria and verifier_file.is_file():
        # The specification gives no criteria; the ones kept beside it are used as written.
        verifier_raw = verifier_file.read_text()
        criteria = _criteria(verifier_raw)
        source = "file"
    return Spec(path=path, title=title, intent=sections.get("intent", ""),
                criteria=criteria, raw=raw, act=_act(sections.get("act", "")),
                verifier_source=source, verifier_raw=verifier_raw)


def render_verifier(run_id: str, understood: str, assumptions: list[str], criteria: list[dict]) -> str:
    """The text of verifier.md for criteria assumed from the intent.

    Only the criteria are bullets, because bullets are what `_criteria` reads.
    """
    def one_line(text: str) -> str:
        return re.sub(r"\s+", " ", str(text)).strip()

    lines = [
        "# Verifier (assumed)", "",
        f"Derived from the intent in {SPEC_FILE} by run {run_id}. No person has reviewed it.",
        "Every run uses this file as written. The loop does not change it; its parent does,",
        "by editing the criteria below. A criterion with a `check` block is tested by running",
        "that script from the loop directory: exit status 0 passes. A criterion without one",
        "is recorded as unchecked. Delete this file to have it derived again.", "",
    ]
    if one_line(understood):
        lines += ["## The outcome as understood", "", one_line(understood), ""]
    if assumptions:
        lines += ["## Assumed where the intent does not say", ""]
        lines += [f"{number}. {one_line(text)}" for number, text in enumerate(assumptions, 1)]
        lines += [""]
    lines += ["## Criteria", ""]
    for criterion in criteria:
        lines.append(f"- {one_line(criterion['text'])}")
        check = textwrap.dedent(str(criterion.get("check") or "")).strip()
        if check:
            lines += ["  ```check", *[f"  {line}" if line else "" for line in check.splitlines()], "  ```"]
    return "\n".join(lines) + "\n"

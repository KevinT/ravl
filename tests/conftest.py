"""Test support: a loop in a temporary directory and a scripted stand-in for the LLM.

The stand-in is a command that follows the library's LLM contract (prompt on stdin,
envelope on stdout). What it does in each phase is read from a JSON file the test
edits, and every call is appended to a log, so tests can count LLM calls.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

from ravl import runner
from ravl.store import Store

FAKE = r"""
import json, os, subprocess, sys
path = sys.argv[1]
behaviour = json.load(open(path))
phase = os.environ["RAVL_PHASE"]
prompt = sys.stdin.read()
with open(path + ".calls", "a") as log:
    log.write(json.dumps({"phase": phase}) + "\n")
open(f"{path}.{phase}.prompt", "w").write(prompt)
b = behaviour.get(phase)
if b is None:
    sys.stderr.write("no behaviour for " + phase)
    sys.exit(3)
if phase == "act":
    for command in b.get("do", []):
        subprocess.run(command, shell=True, check=False)
    text = "Work done.\n```json\n" + json.dumps(b.get("report", {})) + "\n```\n"
elif phase == "learn":
    text = json.dumps(b)
else:
    text = b
print(json.dumps({"text": text, "usage": {"model": "fake-1", "input_tokens": len(prompt) // 4,
                                          "output_tokens": len(text) // 4, "cost_usd": 0.01}}))
"""

PRODUCE = """\
# Produce a file

## Intent

A file `out.txt` in the loop directory is written on every run and contains the word ready.

## Verifier

- `out.txt` exists and was modified during this run.
  ```check
  test out.txt -nt "$RAVL_RUN_DIR/started"
  ```
- `out.txt` contains the word ready.
  ```check
  grep -q ready out.txt
  ```
"""

MAINTAIN = """\
# Keep a flag present

## Intent

The file `flag` exists in the loop directory.

## Verifier

- The file `flag` exists.
  ```check
  test -f flag || { echo "flag is missing"; exit 1; }
  ```
"""


def learn(**over) -> dict:
    base = {"classification": None, "fault": None, "reason": "", "steer": "", "hold": False,
            "question": None, "domain": [], "execution": [], "contributed": []}
    return {**base, **over}


def act(do: list[str], effects: list[str], needs_owner: str | None = None) -> dict:
    return {"do": do, "report": {"effects": effects, "summary": "did the work", "procedure": do,
                                 "resources_used": [], "needs_owner": needs_owner}}


ACT_WRITE = act(["echo ready > out.txt"], ["out.txt"])

PROGRAM = "\n".join([
    "```python",
    "# /// script",
    '# requires-python = ">=3.11"',
    "# dependencies = []",
    "# ///",
    "import json",
    "from pathlib import Path",
    'Path("out.txt").write_text("ready\\n")',
    'print(json.dumps({"effects": ["out.txt"], "summary": "wrote out.txt"}))',
    "```",
])


class Harness:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.fake = tmp / "fake_llm.py"
        self.fake.write_text(FAKE)
        self.behaviour = tmp / "behaviour.json"
        self.behave({})
        self.user_config = tmp / "user.toml"
        self.user_config.write_text(
            f'[llm]\ncommand = ["{sys.executable}", "{self.fake}", "{self.behaviour}"]\ntimeout_s = 30\n')
        self.empty_config = tmp / "empty.toml"
        self.empty_config.write_text("")

    def behave(self, behaviour: dict) -> None:
        self.behaviour.write_text(json.dumps(behaviour))

    def loop(self, name: str, spec: str, parent: Path | None = None) -> Path:
        directory = (parent or self.tmp / "tree") / name
        directory.mkdir(parents=True)
        (directory / "ravl.md").write_text(textwrap.dedent(spec))
        return directory

    def run(self, loop_dir: Path, llm: bool = True) -> dict:
        return runner.run(loop_dir, self.user_config if llm else self.empty_config)

    def calls(self) -> list[str]:
        log = Path(str(self.behaviour) + ".calls")
        return [json.loads(l)["phase"] for l in log.read_text().splitlines()] if log.exists() else []

    def prompt(self, phase: str) -> str:
        return Path(f"{self.behaviour}.{phase}.prompt").read_text()

    def store(self, loop_dir: Path) -> Store:
        return Store(loop_dir)


@pytest.fixture
def h(tmp_path: Path) -> Harness:
    return Harness(tmp_path)

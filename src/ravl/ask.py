"""Carrying a loop's questions to its parent.

A question is recorded in the loop (`learnings/steer/questions.json`) whether or not it
is carried anywhere. When the configuration names a command under `[ask]`, that command
is run once for each waiting question that has not been sent. It receives one JSON
object on standard input:

    {"loop": "<loop directory>", "title": "<loop title>", "id": "q-003",
     "text": "<the question>", "asked": "<UTC time>", "run": "<run id>",
     "answer_with": ["ravl", "answer", "<loop directory>", "q-003"]}

Exit status 0 means the question was sent, and it is not sent again. Any other result
is recorded on the question and the next delivery tries again. The command is the
owner's: this module does not know where a question goes or how the answer comes back.
The answer is recorded with `ravl answer`, by a person or by whatever receives the reply.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from . import spec as specmod
from .store import Store, iso, utcnow


def waiting(store: Store) -> list[dict]:
    """Open questions that no command has yet carried."""
    return [q for q in store.open_questions() if not q.get("delivered")]


def deliver(store: Store, cfg: dict) -> list[dict]:
    """Send every waiting, unsent question of one loop. Returns one record per question
    tried: `{"id", "sent": bool, "error"}`. Returns nothing when no command is configured."""
    command = cfg.get("ask", {}).get("command")
    pending = waiting(store)
    if not command or not pending:
        return []
    try:
        title = specmod.load(store.dir).title
    except specmod.SpecError:
        title = store.dir.name
    results = []
    for question in pending:
        payload = {"loop": str(store.dir), "title": title, "id": question["id"],
                   "text": question["text"], "asked": question["asked"], "run": question["run"],
                   "answer_with": ["ravl", "answer", str(store.dir), question["id"]]}
        error = _run([str(part) for part in command], payload, store.dir,
                     int(cfg["ask"].get("timeout_s", 60)))
        if error is None:
            store.mark_question(question["id"], delivered=iso(utcnow()), delivery_error=None)
        else:
            store.mark_question(question["id"], delivery_error=error)
        results.append({"id": question["id"], "sent": error is None, "error": error})
    return results


def _run(command: list[str], payload: dict, loop_dir: Path, timeout_s: int) -> str | None:
    """Run the command for one question. None when it was sent, otherwise why not."""
    env = {**os.environ, "RAVL_LOOP_DIR": payload["loop"], "RAVL_QUESTION_ID": payload["id"]}
    try:
        done = subprocess.run(command, input=json.dumps(payload), capture_output=True, text=True,
                              cwd=loop_dir, env=env, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return f"the ask command did not finish in {timeout_s}s"
    except OSError as exc:
        return f"the ask command could not be started: {exc}"
    if done.returncode == 0:
        return None
    said = (done.stderr or done.stdout or "").strip().splitlines()
    return f"the ask command exited {done.returncode}" + (f": {said[-1][:300]}" if said else "")

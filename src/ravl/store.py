"""The learning store and run records of one loop, and the rule for what it may read.

Layout beside the specification:

    learnings/
      state.json              learned execution mode, streaks, hold; unchanged by a
                              run in which Act did nothing
      domain/learnings.jsonl  facts about the task (context for Reflect)
      execution/constraints.jsonl  constraints on generated code (enforced)
      steer/reflect.md        guidance for this loop's next Reflect
      steer/owner.md          outcome summary and open questions for the owner
      steer/siblings.md       portable domain patterns for sibling loops
      steer/questions.json    questions for the owner and their answers
      generated/act.py        code that performs Act once the loop is code-driven
    runs/<id>/trace.json      one directory per run

A loop writes only inside its own directory. It reads its own learnings, and
those of loops within its read radius: siblings and children at hop 1, one
directory level deeper per further hop. It never reads above its containing
directory, and reads no specification or learnings in that directory itself.
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .spec import is_loop

SKIP = {"runs", "learnings", "config"}


class Busy(Exception):
    """Another run of this loop holds the lock."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def write_atomic(path: Path, text: str) -> None:
    """Replace the file in one step. An unchanged file is left untouched."""
    if path.is_file() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path: Path, value) -> None:
    write_atomic(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


class Store:
    def __init__(self, loop_dir: Path):
        self.dir = Path(loop_dir)
        self.learnings = self.dir / "learnings"
        self.runs = self.dir / "runs"
        self.steer = self.learnings / "steer"
        self.generated = self.learnings / "generated" / "act.py"

    # ---- lock: one run of a loop at a time
    @contextmanager
    def lock(self):
        self.runs.mkdir(parents=True, exist_ok=True)
        handle = open(self.runs / ".lock", "w")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            raise Busy(f"a run of {self.dir} is already in progress") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

    # ---- state
    def state(self) -> dict:
        state = read_json(self.learnings / "state.json", {})
        state.setdefault("mode", "llm")
        for key in ("llm_pass_streak", "code_fail_streak", "codegen_declined"):
            state.setdefault(key, 0)
        state.setdefault("llm_pass_runs", [])
        state.setdefault("relevance", {})
        return state

    def save_state(self, state: dict) -> None:
        write_json(self.learnings / "state.json", state)

    # ---- learnings
    def domain(self) -> list[dict]:
        return read_jsonl(self.learnings / "domain" / "learnings.jsonl")

    def constraints(self) -> list[dict]:
        return read_jsonl(self.learnings / "execution" / "constraints.jsonl")

    def _append_unique(self, path: Path, entries: list[dict]) -> int:
        known = {e.get("text", "").strip().lower() for e in read_jsonl(path)}
        fresh = [e for e in entries
                 if e.get("text", "").strip() and e["text"].strip().lower() not in known]
        if fresh:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as handle:
                for entry in fresh:
                    handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return len(fresh)

    def add_domain(self, entries: list[dict]) -> int:
        return self._append_unique(self.learnings / "domain" / "learnings.jsonl", entries)

    def add_constraints(self, entries: list[dict]) -> int:
        return self._append_unique(self.learnings / "execution" / "constraints.jsonl", entries)

    def steer_text(self, name: str) -> str:
        path = self.steer / name
        return path.read_text().strip() if path.is_file() else ""

    # ---- questions for the owner
    def questions(self) -> list[dict]:
        return read_json(self.steer / "questions.json", [])

    def open_questions(self) -> list[dict]:
        return [q for q in self.questions() if not q.get("answer") and not q.get("closed")]

    def ask(self, condition: str, text: str, run_id: str) -> dict | None:
        """Record a question unless one is already open for the same condition."""
        questions = self.questions()
        if any(q["condition"] == condition for q in questions
               if not q.get("answer") and not q.get("closed")):
            return None
        question = {"id": f"q-{len(questions) + 1:03d}", "condition": condition, "text": text.strip(),
                    "asked": iso(utcnow()), "run": run_id, "answer": None, "answered": None,
                    "closed": None}
        questions.append(question)
        write_json(self.steer / "questions.json", questions)
        return question

    def answer(self, question_id: str, text: str) -> bool:
        questions = self.questions()
        for question in questions:
            if question["id"] == question_id:
                question["answer"], question["answered"] = text.strip(), iso(utcnow())
                write_json(self.steer / "questions.json", questions)
                return True
        return False

    def close_questions(self, reason: str, keep: set[str] = frozenset()) -> int:
        """Close open questions whose condition no longer holds."""
        questions, closed = self.questions(), 0
        for question in questions:
            if not question.get("closed") and question["condition"] not in keep:
                question["closed"] = f"{iso(utcnow())} {reason}"
                closed += 1
        if closed:
            write_json(self.steer / "questions.json", questions)
        return closed

    # ---- runs (a run id starts with its UTC start time, so names sort by time)
    def run_ids(self) -> list[str]:
        if not self.runs.is_dir():
            return []
        return sorted(p.name for p in self.runs.iterdir() if (p / "trace.json").is_file())

    def trace(self, run_id: str) -> dict | None:
        return read_json(self.runs / run_id / "trace.json", None)

    def traces(self, since: datetime | None = None, last: int | None = None) -> list[dict]:
        ids = self.run_ids()
        if since is not None:
            floor = since.strftime("%Y%m%dT%H%M%S")
            ids = [i for i in ids if i >= floor]
        if last is not None:
            ids = ids[-last:]
        return [t for t in (self.trace(i) for i in ids) if t]

    def last_trace(self) -> dict | None:
        traces = self.traces(last=1)
        return traces[0] if traces else None

    def prune(self, keep: int) -> int:
        """Delete the oldest run directories beyond `keep`."""
        ids = self.run_ids()
        doomed = ids[:-keep] if keep > 0 and len(ids) > keep else []
        for run_id in doomed:
            shutil.rmtree(self.runs / run_id, ignore_errors=True)
        return len(doomed)


class Trace:
    """Written after every phase, so a run that stops part-way leaves a record."""

    def __init__(self, store: Store, run_id: str, version: str):
        self.dir = store.runs / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.started = time.time()
        # A marker checks can compare against: `test FILE -nt "$RAVL_RUN_DIR/started"`.
        (self.dir / "started").write_text(iso(utcnow()) + "\n")
        self.data: dict = {
            "run_id": run_id, "loop": str(store.dir), "ravl_version": version,
            "started": iso(utcnow()), "ended": None, "status": "running",
            "cost": {"wall_s": 0.0, "llm_calls": 0, "tokens": {}, "cost_usd": 0.0,
                     "checks_run": 0, "llm_wall_s": 0.0, "network_calls": None},
        }
        self.flush()

    def flush(self) -> None:
        self.data["cost"]["wall_s"] = round(time.time() - self.started, 2)
        write_json(self.dir / "trace.json", self.data)

    def phase(self, name: str, record: dict) -> None:
        self.data[name] = record
        self.flush()

    def charge_llm(self, result) -> None:
        cost = self.data["cost"]
        cost["llm_calls"] += 1
        cost["llm_wall_s"] = round(cost["llm_wall_s"] + result.wall_s, 2)
        usage = result.usage or {}
        if usage:
            model = cost["tokens"].setdefault(str(usage.get("model", "unknown")),
                                              {"input": 0, "output": 0})
            model["input"] += int(usage.get("input_tokens", 0) or 0)
            model["output"] += int(usage.get("output_tokens", 0) or 0)
            cost["cost_usd"] = round(cost["cost_usd"] + float(usage.get("cost_usd", 0) or 0), 4)
        self.flush()

    def save(self, name: str, text: str) -> None:
        write_atomic(self.dir / name, text)

    def finish(self) -> None:
        self.data["ended"] = iso(utcnow())
        self.data["status"] = "complete"
        self.flush()


# ---- topology: discovery and the read radius

def child_loops(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir()
                  if p.is_dir() and p.name not in SKIP and not p.name.startswith(".") and is_loop(p))


def discover(root: Path) -> list[Path]:
    """Every loop at or under `root`, parents before children."""
    found = []

    def walk(directory: Path) -> None:
        if is_loop(directory):
            found.append(directory)
        for entry in sorted(directory.iterdir()):
            if entry.is_dir() and entry.name not in SKIP and not entry.name.startswith("."):
                walk(entry)

    if root.is_dir():
        walk(root)
    return found


def readable(loop_dir: Path, radius: int) -> list[tuple[Path, str]]:
    """Loops whose learnings this loop may read, with their relation to it.

    Hop 1 is the loop's siblings and its children. Each further hop goes one
    level deeper. The containing directory is listed to find siblings; nothing
    in it, and nothing above it, is read.
    """
    if radius < 1:
        return []
    frontier = [(p, "sibling") for p in child_loops(loop_dir.parent) if p != loop_dir]
    frontier += [(p, "child") for p in child_loops(loop_dir)]
    seen, out = set(), []
    for _ in range(radius):
        nxt = []
        for path, relation in frontier:
            if path in seen:
                continue
            seen.add(path)
            out.append((path, relation))
            nxt += [(c, "descendant") for c in child_loops(path)]
        frontier = nxt
    return out


def window_llm_calls(loop_dir: Path, window_hours: float) -> int:
    """LLM calls made by this loop and its descendants inside the rolling window."""
    cutoff = utcnow() - timedelta(hours=window_hours)
    total = 0
    for directory in discover(loop_dir):
        for trace in Store(directory).traces(since=cutoff):
            total += int(trace.get("cost", {}).get("llm_calls", 0))
    return total

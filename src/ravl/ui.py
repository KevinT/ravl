"""Terminal display for the `ravl` command, used when standard output is a terminal.

This is a surface: it reads traces and the events a run reports, and prints. Nothing
here decides anything about a run. When output is piped or captured, the command
prints the plain text in `cli.py` instead, and `--json` prints the trace itself.
"""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console, Group
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

PHASES = {
    "derive": ("·", "Verifier", "deriving criteria from the intent"),
    "reflect": ("R", "Reflect", "running the checks"),
    "act": ("A", "Act", "working"),
    "verify": ("V", "Verify", "running the checks"),
    "learn": ("L", "Learn", "classifying the run"),
}
VERDICT = {"pass": ("PASS", "bold black on green"), "fail": ("FAIL", "bold white on red"),
           "no-verifier": ("NO VERIFIER", "bold black on yellow")}
MARK = {"pass": ("✓", "green"), "fail": ("✗", "red"), "unchecked": ("–", "dim")}


def console() -> Console:
    return Console(highlight=False)


def duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes}m {rest:02d}s"


def count(number: int) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    return f"{number / 1000:.0f}k" if number >= 10_000 else str(number)


def short(path: str | Path) -> str:
    text, home = str(path), str(Path.home())
    return "~" + text[len(home):] if text.startswith(home) else text


def _head(phase: str, summary: Text | str, seconds: float | None = None) -> Text:
    letter, name, _ = PHASES[phase]
    line = Text.assemble((f"{letter}  ", "bold cyan"), (f"{name:<9} ", "bold"))
    line.append_text(summary if isinstance(summary, Text) else Text(summary))
    if seconds is not None:
        line.append(f"  {duration(seconds)}", style="dim")
    return line


def _detail(text: str | Text, style: str = "dim") -> Padding:
    return Padding(Text(text, style=style) if isinstance(text, str) else text, (0, 0, 0, 13))


def _criteria(checks: list[dict], only_failing: bool = False, full: bool = True) -> list:
    """One line per criterion, cut to the width of the terminal. With `full`, a failing
    criterion is printed whole, followed by the last lines its check printed."""
    rows = []
    for check in checks:
        if only_failing and check["status"] == "pass":
            continue
        mark, style = MARK.get(check["status"], ("?", "dim"))
        whole = full and check["status"] == "fail"
        line = Text.assemble((f"{mark} ", style), (check["text"], "" if check["status"] == "fail" else "dim"))
        if check["status"] == "unchecked":
            line = Text.assemble((f"{mark} ", style), ("(no check) ", "dim italic"), (check["text"], "dim"))
        if not whole:
            line.no_wrap, line.overflow = True, "ellipsis"
        rows.append(Padding(line, (0, 0, 0, 13)))
        if whole and check.get("output"):
            for output in check["output"].splitlines()[-6:]:
                rows.append(Padding(Text(output, style="red", no_wrap=True, overflow="ellipsis"), (0, 0, 0, 15)))
    return rows


class _Working:
    """The line shown while a phase runs: its letter, a spinner and the time so far."""

    def __init__(self, phase: str, clock):
        self.phase, self.clock, self.started = phase, clock, clock()
        self.spinner = Spinner("dots", style="cyan")

    def __rich_console__(self, console, options):
        line = _head(self.phase, "")
        frame = self.spinner.render(console.get_time())
        line.append_text(frame if isinstance(frame, Text) else Text(str(frame)))
        line.append(f" {PHASES[self.phase][2]}", style="italic")
        line.append(f"  {duration(self.clock() - self.started)}", style="dim")
        yield line


class RunDisplay:
    """Prints a run as it happens. Given to `runner.run` as its observer."""

    def __init__(self, out: Console, live: bool = True, clock=time.monotonic):
        self.out, self.live_enabled, self.clock = out, live, clock
        self.live: Live | None = None
        self.started: dict[str, float] = {}

    def __call__(self, event: str, phase: str, data: dict) -> None:
        if event == "start":
            self._start(data)
        elif event == "begin":
            self._begin(phase)
        elif event == "end":
            self._stop()
            seconds = self.clock() - self.started[phase] if phase in self.started else None
            getattr(self, f"_{phase}")(data, seconds)
        elif event == "finish":
            self._stop()
            self._finish(data)

    def _stop(self) -> None:
        if self.live is not None:
            self.live.stop()
            self.live = None

    def _begin(self, phase: str) -> None:
        self.started[phase] = self.clock()
        if self.live_enabled:
            self.live = Live(_Working(phase, self.clock), console=self.out, transient=True,
                             refresh_per_second=10)
            self.live.start()

    def _start(self, data: dict) -> None:
        self.out.print()
        self.out.print(Text.assemble(("ravl  ", "bold cyan"), (data["title"], "bold"),
                                     (f"   {short(data['loop'])}", "dim")))
        self.out.print(Text(f"      run {data['run_id']}", style="dim"))
        self.out.print()

    def _derive(self, record: dict, seconds) -> None:
        if record.get("derived"):
            summary = Text.assemble("assumed ", (str(record.get("criteria", "")), "bold"),
                                    " criteria from the intent", (f"  → {record['file']}", "dim"))
            self.out.print(_head("derive", summary, seconds))
            self.out.print(_detail("nobody has reviewed them; the loop's parent edits that file"))
        else:
            self.out.print(_head("derive", Text(f"could not be derived: {record.get('reason')}", style="yellow"),
                                 seconds))

    def _reflect(self, record: dict, seconds) -> None:
        checks = record["world"]["checks"]
        holding = sum(c["status"] == "pass" for c in checks)
        mode = record.get("mode", {})
        label = "code-driven" if mode.get("value") == "code" else "LLM-driven"
        label += f" (set by parent: {mode.get('setting')})" if mode.get("source") == "owner" else ""
        summary = Text.assemble((f"{holding} of {len(checks)}", "bold"), " criteria hold before Act",
                                (f"  ·  {label}", "dim"))
        self.out.print(_head("reflect", summary, seconds))
        if holding != len(checks):
            self.out.print(Group(*_criteria(checks, only_failing=True, full=False)))

    def _act(self, record: dict, seconds) -> None:
        driver = record.get("driver", "?")
        detail = record.get("summary") or record.get("reason") or record.get("error") or ""
        if driver == "none":
            summary = Text("nothing to do: the outcome already holds", style="green")
            detail = ""
        elif driver in ("blocked", "held"):
            summary, detail = Text(f"{driver}: {detail}", style="yellow"), ""
        else:
            source = "the implementation in the specification" if record.get("source") == "owner" else driver
            ok = record.get("ok")
            summary = Text.assemble(("by ", "dim"), (source, "bold"),
                                    ("" if ok is not False else "  did not finish", "red"))
        self.out.print(_head("act", summary, seconds))
        if detail:
            self.out.print(_detail(str(detail), style=""))
        for effect in record.get("effects", []):
            mark, style = {True: ("✓", "green"), False: ("✗", "red"), None: ("·", "dim")}[effect["confirmed"]]
            note = {True: "", False: "  not found after the run", None: "  cannot be confirmed"}[effect["confirmed"]]
            self.out.print(_detail(Text.assemble((f"{mark} ", style), (effect["claim"], "dim"), (note, style))))
        if record.get("restored"):
            self.out.print(_detail(f"changed {' and '.join(record['restored'])}; the change was undone",
                                   style="yellow"))
        if "no LLM command is configured" in str(record.get("reason")):
            self.out.print(_detail("to configure one: ravl config", style="cyan"))

    def _verify(self, record: dict, seconds) -> None:
        checks = record.get("checks", [])
        status = str(record.get("status"))
        word, style = VERDICT.get(status, (status.upper(), "bold"))
        holding = sum(c["status"] == "pass" for c in checks)
        summary = Text.assemble((f" {word} ", style), (f"  {holding} of {len(checks)} criteria hold", ""))
        if record.get("reused_reflect"):
            summary.append("  (as read at Reflect)", style="dim")
        self.out.print(_head("verify", summary, seconds))
        if checks:
            self.out.print(Group(*_criteria(checks)))

    def _learn(self, record: dict, seconds) -> None:
        if record.get("classification"):
            colour = "yellow" if record["classification"] == "world" else "red"
            summary = Text.assemble((f"{record['classification']} failure", f"bold {colour}"))
        else:
            summary = Text("nothing to classify", style="dim")
        self.out.print(_head("learn", summary, seconds))
        if record.get("reason"):
            self.out.print(_detail(str(record["reason"]), style=""))
        if record.get("mode_change"):
            self.out.print(_detail(f"mode: {record['mode_change']}", style="cyan"))
        if record.get("codegen"):
            self.out.print(_detail(f"code generation: {record['codegen']}"))

    def _finish(self, data: dict) -> None:
        trace, cost = data["trace"], data["trace"]["cost"]
        if data.get("steer"):
            self.out.print(_detail(Text.assemble(("steer for the next run  ", "dim italic"), (data["steer"], "dim"))))
        word, style = VERDICT.get(str(trace.get("verify", {}).get("status")), ("?", "bold"))
        tokens_in = sum(m.get("input", 0) for m in cost.get("tokens", {}).values())
        tokens_out = sum(m.get("output", 0) for m in cost.get("tokens", {}).values())
        parts = [f"{cost.get('llm_calls', 0)} LLM calls"]
        if cost.get("tokens"):
            parts += [f"{count(tokens_in)} in / {count(tokens_out)} out", " + ".join(cost["tokens"])]
            parts += [f"${cost.get('cost_usd', 0):.2f}"] if cost.get("cost_usd") else []
        parts += [f"{cost.get('checks_run', 0)} checks", duration(float(cost.get("wall_s", 0)))]
        self.out.print()
        self.out.print(Text.assemble((f" {word} ", style), ("  " + "  ·  ".join(parts), "dim")))
        for question in data.get("questions", []):
            self.out.print()
            self.out.print(question_panel(question, trace["loop"]))
        self.out.print()


def question_panel(question: dict, loop: str) -> Panel:
    body = Group(Text(question["text"]),
                 Text(f'\nto answer:  ravl answer {short(loop)} {question["id"]} "…"', style="dim"))
    sent = " · sent" if question.get("delivered") else ""
    return Panel(body, title=f"question for the loop's parent · {question['id']}{sent}", title_align="left",
                 border_style="yellow", padding=(0, 1))


def replay(out: Console, trace: dict, title: str, steer: str, questions: list[dict]) -> None:
    """Print a finished run from its trace, in the form it had while running."""
    display = RunDisplay(out, live=False)
    display("start", "", {"title": title, "loop": trace["loop"], "run_id": trace["run_id"]})
    verifier = trace.get("verifier", {})
    if "derived" in verifier:
        display("end", "derive", dict(verifier))
    for phase in ("reflect", "act", "verify", "learn"):
        if phase in trace:
            display("end", phase, dict(trace[phase]))
    display("finish", "", {"trace": trace, "steer": steer, "questions": questions})


def _status(value: str | None) -> Text:
    word, style = VERDICT.get(value or "", ("NEVER RUN", "dim"))
    return Text(f" {word} ", style=style)


def listing(out: Console, rows: list[dict], root: Path) -> None:
    table = Table(box=None, padding=(0, 2, 0, 0), header_style="dim")
    for column in ("", "loop", "mode", "verifier", "last run", "waiting"):
        table.add_column(column)
    for row in rows:
        path = Path(row["loop"])
        verifier = row["verifier"]
        where = {"specification": "written", "file": "assumed", "none": "none"}[verifier["source"]]
        waiting = Text(f"{len(row['questions'])} question(s)", style="yellow") if row["questions"] else Text("")
        if row["hold"]:
            waiting.append("  held", style="yellow")
        table.add_row(_status(row["last_verify"]),
                      Text(str(path.relative_to(root)) if path != root else ".", style="bold"),
                      Text(row["mode"], style="dim"),
                      Text(f"{verifier['criteria']} criteria, {where}", style="dim"),
                      Text(row["last_run"] or "", style="dim"), waiting)
    out.print(table if rows else Text(f"no loops under {root}", style="dim"))


def show(out: Console, row: dict) -> None:
    out.print()
    out.print(Text.assemble(("ravl  ", "bold cyan"), (row["title"], "bold"), (f"   {short(row['loop'])}", "dim")))
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", min_width=9)
    grid.add_column()
    verifier = row["verifier"]
    where = {"specification": "written in ravl.md", "file": "assumed, in verifier.md", "none": "none yet"}[
        verifier["source"]]
    last = Text.assemble(_status(row["last_verify"]), (f"  act {row['last_act']}  ·  {row['last_run']}", "dim")) \
        if row["last_run"] else Text("never run", style="dim")
    grid.add_row("last run", last)
    grid.add_row("mode", row["mode"])
    grid.add_row("verifier", f"{verifier['criteria']} criteria, {verifier['with_check']} with a check  ·  {where}")
    grid.add_row("runs", f"{row['runs_kept']} kept  ·  {row['consecutive_passes']} consecutive passes")
    if row["hold"]:
        grid.add_row("hold", Text(f"since {row['hold']['since']}: {row['hold']['reason']}", style="yellow"))
    if row["steer"]:
        grid.add_row("steer", Text(" ".join(l for l in row["steer"].splitlines() if not l.startswith("<!--")),
                                   style="dim"))
    out.print(Padding(grid, (1, 0, 0, 6)))
    for text in row["failing"]:
        out.print(Padding(Text.assemble(("✗ ", "red"), text), (0, 0, 0, 6)))
    for question in row["questions"]:
        out.print()
        out.print(question_panel(question, row["loop"]))
    out.print()


def config(out: Console, directory: Path, layers: list[tuple[str, str, str]], in_effect: list[tuple[str, str]],
           found: list[dict], notice: str, usage: str) -> None:
    """`layers` are (level, path, what the file sets); `in_effect` are (phase label, text)."""
    out.print()
    out.print(Text.assemble(("Settings files that apply in ", "bold"), (short(directory), "bold cyan"),
                            ("   later overriding earlier", "dim")))
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", min_width=9)
    grid.add_column()
    grid.add_column(style="dim")
    for level, path, text in layers:
        grid.add_row(level, short(path), text)
    out.print(Padding(grid, (0, 0, 0, 2)))
    out.print(Text("In effect", style="bold"))
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", min_width=11)
    grid.add_column()
    for label, text in in_effect:
        unset = "not configured" in text or "no model set" in text
        grid.add_row(label, Text(text, style="yellow" if unset else "green"))
    out.print(Padding(grid, (0, 0, 1, 2)))
    out.print(Text("Agent programs ravl has a backend for", style="bold"))
    for number, row in enumerate(found, 1):
        program = (("✓ ", "green"), ("on PATH", "")) if row["program"] else (("✗ ", "red"), ("not on PATH", ""))
        signin = ((("✓ ", "green"), ("sign-in found", "")) if row["signin"]
                  else (("– ", "yellow"), (f"no sign-in found, to sign in: {row['signin_hint']}", "")))
        out.print(Text.assemble((f"  {number}. ", "dim"), (f"{row['name']:<8}", "bold cyan"), (f"{row['title']:<13}", ""),
                                *program, ("    ", ""), *signin))
        out.print(Padding(Text(f"during Act: {row['confines_act']}", style="dim"), (0, 0, 0, 13)))
        if row["note"]:
            out.print(Padding(Text(row["note"], style="dim italic"), (0, 0, 0, 13)))
    out.print()
    out.print(Text(notice, style="yellow"))
    out.print(Text(usage, style="dim"))
    out.print()

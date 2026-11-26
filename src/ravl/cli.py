"""The command line: the surface through which a loop is developed and run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config, runner, spec as specmod
from .store import Busy, Store, discover


def _mode_label(cfg_mode: str, state: dict) -> str:
    if cfg_mode == "lock":
        return "code-driven (owner: lock)"
    if cfg_mode == "never-lock":
        return "LLM-driven (owner: never-lock)"
    return ("code-driven" if state["mode"] == "code" else "LLM-driven") + " (learned)"


def summary(loop_dir: Path) -> dict:
    """The state of a loop without running it."""
    store = Store(loop_dir)
    try:
        initial = "code" if specmod.load(loop_dir).act else "llm"
    except specmod.SpecError:
        initial = "llm"
    state, traces = store.state(initial), store.traces()
    last = traces[-1] if traces else None
    passes = 0
    for trace in reversed(traces):
        if trace.get("verify", {}).get("status") != "pass":
            break
        passes += 1
    try:
        title = specmod.load(loop_dir).title
        mode = _mode_label(config.owner_mode(loop_dir), state)
    except (specmod.SpecError, config.ConfigError) as exc:
        title, mode = loop_dir.name, f"unreadable: {exc}"
    return {
        "loop": str(loop_dir), "title": title, "mode": mode,
        "runs_kept": len(traces), "consecutive_passes": passes,
        "last_run": last["run_id"] if last else None,
        "last_status": last.get("status") if last else None,
        "last_verify": last.get("verify", {}).get("status") if last else None,
        "last_act": last.get("act", {}).get("driver") if last else None,
        "failing": [c["text"] for c in last.get("verify", {}).get("checks", [])
                    if c["status"] == "fail"] if last else [],
        "hold": state.get("hold"),
        "questions": store.open_questions(),
        "steer": store.steer_text("reflect.md"),
    }


def _print_run(trace: dict, loop_dir: Path) -> None:
    reflect, act = trace.get("reflect", {}), trace.get("act", {})
    post, learn, cost = trace.get("verify", {}), trace.get("learn", {}), trace["cost"]
    mode = reflect.get("mode", {})
    world = reflect.get("world", {})
    print(f"loop     {loop_dir}")
    print(f"run      {trace['run_id']}")
    print(f"mode     {'code-driven' if mode.get('value') == 'code' else 'LLM-driven'} "
          f"({'set by owner: ' + mode.get('setting', '') if mode.get('source') == 'owner' else 'learned'})")
    checks = world.get("checks", [])
    print(f"reflect  {sum(c['status'] == 'pass' for c in checks)} of {len(checks)} criteria hold before Act")
    detail = act.get("summary") or act.get("reason") or act.get("error") or ""
    print(f"act      {act.get('driver', 'not reached')}" + (f": {detail}" if detail else ""))
    for effect in act.get("effects", []):
        mark = {True: "confirmed", False: "NOT PRODUCED", None: "unconfirmable"}[effect["confirmed"]]
        print(f"           effect {effect['claim']} [{mark}]")
    print(f"verify   {post.get('status', 'not reached').upper()}")
    for check in post.get("checks", []):
        if check["status"] != "pass":
            print(f"           {check['status']}: {check['text']}")
    line = "learn    "
    if learn.get("classification"):
        line += f"{learn['classification']} failure"
        line += f" ({learn['reason']})" if learn.get("reason") else ""
    else:
        line += "nothing to classify"
    print(line)
    if learn.get("mode_change"):
        print(f"           mode change: {learn['mode_change']}")
    if learn.get("codegen"):
        print(f"           code generation: {learn['codegen']}")
    store = Store(loop_dir)
    steer = store.steer_text("reflect.md")
    if steer:
        print("steer    " + " ".join(l for l in steer.splitlines() if not l.startswith("<!--")))
    for question in store.open_questions():
        print(f"question {question['id']}: {question['text']}")
    tokens = ", ".join(f"{m} {t['input']}/{t['output']}" for m, t in cost["tokens"].items()) or "not reported"
    print(f"cost     wall {cost['wall_s']}s · LLM calls {cost['llm_calls']} · tokens in/out {tokens}"
          f" · ${cost['cost_usd']} · checks {cost['checks_run']}")


def cmd_new(args) -> int:
    target = Path(args.dir)
    if (target / specmod.SPEC_FILE).exists():
        print(f"{target / specmod.SPEC_FILE} already exists", file=sys.stderr)
        return 2
    target.mkdir(parents=True, exist_ok=True)
    (target / specmod.SPEC_FILE).write_text(specmod.TEMPLATE.format(name=target.resolve().name))
    print(f"wrote {target / specmod.SPEC_FILE}")
    return 0


def cmd_run(args) -> int:
    loop_dir = Path(args.dir).resolve()
    try:
        trace = runner.run(loop_dir, Path(args.user_config) if args.user_config else None)
    except (specmod.SpecError, config.ConfigError) as exc:
        print(f"ravl: {exc}", file=sys.stderr)
        return 2
    except Busy as exc:
        print(f"ravl: {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(trace, indent=2))
    else:
        _print_run(trace, loop_dir)
    return 0 if trace["verify"]["status"] == "pass" else 1


def cmd_list(args) -> int:
    root = Path(args.dir).resolve()
    rows = [summary(p) for p in discover(root)]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        rel = Path(row["loop"]).relative_to(root) if Path(row["loop"]) != root else Path(".")
        verify = (row["last_verify"] or "never run").upper()
        held = " held" if row["hold"] else ""
        print(f"{verify:<12} {str(rel):<40} {row['mode']:<32} questions: {len(row['questions'])}{held}")
    if not rows:
        print(f"no loops under {root}")
    return 0


def cmd_show(args) -> int:
    loop_dir = Path(args.dir).resolve()
    row = summary(loop_dir)
    if args.json:
        print(json.dumps(row, indent=2))
        return 0
    print(f"{row['title']}  ({row['loop']})")
    print(f"mode       {row['mode']}")
    print(f"runs       {row['runs_kept']} kept; consecutive passes {row['consecutive_passes']}")
    print(f"last run   {row['last_run']} · act {row['last_act']} · verify {row['last_verify']}")
    for text in row["failing"]:
        print(f"  failing: {text}")
    if row["hold"]:
        print(f"hold       since {row['hold']['since']}: {row['hold']['reason']}")
    if row["steer"]:
        print("steer      " + " ".join(l for l in row["steer"].splitlines() if not l.startswith("<!--")))
    for question in row["questions"]:
        print(f"question   {question['id']} ({question['asked']}): {question['text']}")
    return 0


def cmd_runs(args) -> int:
    store = Store(Path(args.dir).resolve())
    if args.run_id:
        trace = store.trace(args.run_id)
        if not trace:
            print(f"no run {args.run_id}", file=sys.stderr)
            return 2
        print(json.dumps(trace, indent=2))
        return 0
    for trace in store.traces(last=args.last):
        cost = trace.get("cost", {})
        print(f"{trace['run_id']}  {trace.get('status', '?'):<9} act {trace.get('act', {}).get('driver', '-'):<8}"
              f" verify {trace.get('verify', {}).get('status', '-'):<12}"
              f" llm {cost.get('llm_calls', 0)}  {cost.get('wall_s', 0)}s")
    return 0


def cmd_set(args) -> int:
    loop_dir = Path(args.dir).resolve()
    specmod.load(loop_dir)
    config.set_owner_mode(loop_dir, args.mode)
    print(f"{loop_dir}: mode set to {args.mode}")
    return 0


def cmd_answer(args) -> int:
    store = Store(Path(args.dir).resolve())
    if args.question_id:
        if not args.text:
            print("give the answer text after the question id", file=sys.stderr)
            return 2
        if not store.answer(args.question_id, " ".join(args.text)):
            print(f"no question {args.question_id}", file=sys.stderr)
            return 2
        print(f"recorded answer to {args.question_id}; the next run reads it")
        return 0
    questions = store.open_questions()
    if not questions:
        print("no open questions")
        return 0
    for question in questions:
        print(f"\n{question['id']} ({question['asked']})\n{question['text']}")
        reply = input("answer (empty to skip): ").strip()
        if reply:
            store.answer(question["id"], reply)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ravl", description="Reflect, Act, Verify, Learn.")
    parser.add_argument("--version", action="version", version=f"ravl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a loop directory with a template ravl.md")
    p.add_argument("dir"); p.set_defaults(func=cmd_new)

    p = sub.add_parser("run", help="one run of the loop in DIR; exit 0 when Verify passes")
    p.add_argument("dir"); p.add_argument("--json", action="store_true")
    p.add_argument("--user-config", help="read this file in place of ~/.config/ravl/config.toml")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list", help="every loop under DIR with its mode, last result and open questions")
    p.add_argument("dir", nargs="?", default="."); p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="the state of one loop without running it")
    p.add_argument("dir"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_show)

    p = sub.add_parser("runs", help="list runs, or print one trace")
    p.add_argument("dir"); p.add_argument("run_id", nargs="?")
    p.add_argument("--last", type=int, default=20); p.set_defaults(func=cmd_runs)

    p = sub.add_parser("set", help="owner setting for the execution mode")
    p.add_argument("dir"); p.add_argument("mode", choices=config.MODES); p.set_defaults(func=cmd_set)

    p = sub.add_parser("answer", help="answer the loop's open questions for its owner")
    p.add_argument("dir"); p.add_argument("question_id", nargs="?"); p.add_argument("text", nargs="*")
    p.set_defaults(func=cmd_answer)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (specmod.SpecError, config.ConfigError) as exc:
        print(f"ravl: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

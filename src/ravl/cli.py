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


def _verifier(loop_dir: Path) -> dict:
    try:
        spec = specmod.load(loop_dir)
    except specmod.SpecError:
        return {"source": "none", "criteria": 0, "with_check": 0}
    return {"source": spec.verifier_source, "criteria": len(spec.criteria),
            "with_check": sum(1 for c in spec.criteria if c.check)}


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
        "verifier": _verifier(loop_dir),
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
    if "no LLM command is configured" in (detail, trace.get("verifier", {}).get("reason")):
        print("           to configure one: ravl config")
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


def _terminal():
    """A rich console when standard output is a terminal; otherwise None and plain text is printed."""
    if not sys.stdout.isatty():
        return None
    from . import ui   # the display is loaded only when there is a terminal to draw on
    return ui.console()


def cmd_run(args) -> int:
    loop_dir = Path(args.dir).resolve()
    out = None if args.json else _terminal()
    observe = None
    if out is not None:
        from . import ui
        observe = ui.RunDisplay(out)
    try:
        trace = runner.run(loop_dir, Path(args.user_config) if args.user_config else None, observe)
    except (specmod.SpecError, config.ConfigError) as exc:
        print(f"ravl: {exc}", file=sys.stderr)
        return 2
    except Busy as exc:
        print(f"ravl: {exc}", file=sys.stderr)
        return 3
    if args.json:
        print(json.dumps(trace, indent=2))
    elif out is None:
        _print_run(trace, loop_dir)
    return 0 if trace["verify"]["status"] == "pass" else 1


def cmd_list(args) -> int:
    root = Path(args.dir).resolve()
    rows = [summary(p) for p in discover(root)]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    out = _terminal()
    if out is not None:
        from . import ui
        ui.listing(out, rows, root)
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
    out = _terminal()
    if out is not None:
        from . import ui
        ui.show(out, row)
        return 0
    print(f"{row['title']}  ({row['loop']})")
    print(f"mode       {row['mode']}")
    where = {"specification": "written in ravl.md", "file": f"in {specmod.VERIFIER_FILE}",
             "none": "none yet"}[row["verifier"]["source"]]
    print(f"verifier   {where}: {row['verifier']['criteria']} criteria, "
          f"{row['verifier']['with_check']} with a check")
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
        out = None if args.json else _terminal()
        if out is None:
            print(json.dumps(trace, indent=2))
            return 0
        from . import ui
        try:
            title = specmod.load(store.dir).title
        except specmod.SpecError:
            title = store.dir.name
        latest = store.last_trace() or {}
        current = latest.get("run_id") == trace["run_id"]
        # Steer and open questions belong to the loop as it is now, so they are shown
        # only with its latest run.
        ui.replay(out, trace, title, runner._steer_line(store) if current else "",
                  store.open_questions() if current else [])
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


NO_CONFINEMENT = ("In Act the agent runs with its approval prompts off, because nobody is present to "
                  "answer them.\nravl does not confine a run yet.")


def _phase_lines(effective: dict) -> list[tuple[str, str]]:
    """The settings in effect as (label, text) lines: one line when every phase is the same."""
    def text(row: dict) -> str:
        if row["via"] is None:
            return "not configured: a run performs no Act and derives no verifier"
        if row["via"] == "command":
            return f"command: {row['name']}"
        return f"{row['name']}, " + (f"model {row['model']}" if row["model"] else
                                     "no model set: the program uses its own default")
    rows = [(phase, text(effective[phase])) for phase in config.PHASES]
    return [("every phase", rows[0][1])] if len({t for _, t in rows}) == 1 else rows


def _layer_text(llm: dict) -> str:
    parts = [f"{key} {' '.join(map(str, llm[key])) if key == 'command' else llm[key]}"
             for key in ("command", "backend", "model") if llm.get(key)]
    parts += [f"{phase}: " + ", ".join(f"{k} {v}" for k, v in llm[phase].items())
              for phase in config.PHASES if isinstance(llm.get(phase), dict) and llm[phase]]
    return "; ".join(parts) or "no LLM settings"


def _config_show(user: Path, directory: Path) -> tuple[dict, list[dict]]:
    from . import backends   # the registry is read here and by the adapter process, not by a run
    layers = config.layers(directory, user)
    effective = config.effective(config.load(directory, user))
    found = backends.look_all()
    out = _terminal()
    if out is not None:
        from . import ui
        rows = [(layer["level"], layer["path"],
                 _layer_text(layer["llm"]) if layer["exists"] else "not written yet") for layer in layers]
        ui.config(out, directory, rows, _phase_lines(effective), found, NO_CONFINEMENT, CONFIG_USAGE)
        return layers[0]["llm"], found
    print(f"Settings files that apply in {directory}, later overriding earlier:")
    for layer in layers:
        print(f"  {layer['level']:<8} {layer['path']}  "
              + (_layer_text(layer["llm"]) if layer["exists"] else "(not written yet)"))
    print("In effect:")
    for label, text in _phase_lines(effective):
        print(f"  {label:<12} {text}")
    print("\nAgent programs ravl has a backend for:")
    for number, row in enumerate(found, 1):
        program = f"on PATH ({row['program']})" if row["program"] else "not on PATH"
        signin = (f"sign-in found ({', '.join(row['signin'])})" if row["signin"]
                  else f"no sign-in found (to sign in: {row['signin_hint']})")
        print(f"  {number}. {row['name']:<7} {row['title']:<12} {program}; {signin}")
        print(f"     during Act: {row['confines_act']}")
        if row["note"]:
            print(f"     note: {row['note']}")
    print("\n" + NO_CONFINEMENT)
    print(CONFIG_USAGE)
    print("Any other agent: set `command` under [llm] in the settings file to a program that reads a\n"
          "                prompt on standard input and writes the reply on standard output.")
    return layers[0]["llm"], found


CONFIG_USAGE = ("For this machine:          ravl config set NAME --model MODEL     (or only --model MODEL)\n"
                "For a folder and below:    ravl config set [NAME] --model MODEL --dir FOLDER")


def _ask_model(backend) -> str | None:
    """Ask which model the agent program is to use. Returns its name, "" for the
    program's own default, or None when nothing was chosen."""
    print(f"\nModel for {backend.title}. ravl passes the name on and does not check it.")
    for number, name in enumerate(backend.models, 1):
        print(f"  {number}. {name}")
    print("  d. the program's own default, whichever model that is at each run")
    reply = input("Which? [a number, d, or another model name; Enter writes nothing]: ").strip()
    if not reply:
        return None
    if reply.lower() == "d":
        return ""
    if reply.isdigit():
        return backend.models[int(reply) - 1] if 1 <= int(reply) <= len(backend.models) else None
    return reply


def _config_set(args, user: Path, directory: Path | None) -> int:
    from . import backends
    usage = "ravl config set [NAME] [--model MODEL] [--dir FOLDER]"
    if not args.name and not args.model:
        print(f"give an agent program, a model, or both: {usage}", file=sys.stderr)
        return 2
    backend = None
    if args.name:
        backend = backends.BACKENDS.get(args.name)
        if backend is None:
            print(f"no backend named {args.name!r}; known: {', '.join(backends.BACKENDS)}", file=sys.stderr)
            return 2
    target = directory / config.TREE_FILE if directory else user
    view = directory or Path.cwd()
    if backend is None:
        # A model alone: it must have an agent program to be passed to.
        current = config.effective(config.load(view, user))["act"]
        if current["via"] != "backend":
            print("a model is passed to an agent program, and "
                  + ("the settings name a command instead" if current["via"] else "none is chosen yet")
                  + f": {usage}", file=sys.stderr)
            return 2
    config.write_llm(target, backend.name if backend else None, args.model)
    wrote = ", ".join(([f"backend {backend.name}"] if backend else [])
                      + ([f"model {args.model}"] if args.model else ["the program's default model"]))
    print(f"wrote {target}: {wrote}")
    if directory:
        print(f"In effect in {directory} and every folder below it that sets nothing else:")
        for label, text in _phase_lines(config.effective(config.load(directory, user))):
            print(f"  {label:<12} {text}")
    if backend:
        seen = backends.look(backend)
        if not seen["program"]:
            print(f"warning: `{backend.program}` is not on PATH; runs will fail until it is installed")
        elif not seen["signin"]:
            print(f"warning: no sign-in was found for {backend.title}; to sign in: {backend.signin_hint}")
        if backend.note:
            print(f"note: {backend.note}")
        print(NO_CONFINEMENT + f" With {backend.title}, {backend.confines_act}.")
    return 0


def cmd_config(args) -> int:
    from . import backends
    user = Path(args.user_config) if args.user_config else config.USER_CONFIG
    directory = Path(args.dir).resolve() if args.dir else None
    if directory is not None and not directory.is_dir():
        print(f"ravl: no folder {directory}", file=sys.stderr)
        return 2
    if args.action == "set":
        return _config_set(args, user, directory)
    llm, found = _config_show(user, directory or Path.cwd())
    usable = [row for row in found if row["program"]]
    if directory or llm.get("command") or llm.get("backend") or not usable or not sys.stdin.isatty():
        return 0
    # Nothing is chosen for this machine and a person is present: ask for the agent
    # program and then for the model, and write both together or neither.
    reply = input(f"\nUse which one? [1-{len(found)}, Enter to leave unset]: ").strip()
    if not reply:
        return 0
    if not reply.isdigit() or not 1 <= int(reply) <= len(found):
        print("not a number in the list; nothing was changed", file=sys.stderr)
        return 2
    backend = backends.BACKENDS[found[int(reply) - 1]["name"]]
    model = _ask_model(backend)
    if model is None:
        print("no model was chosen; nothing was changed")
        return 0
    args.name, args.model = backend.name, model or None
    return _config_set(args, user, None)


def cmd_ask(args) -> int:
    """Send the waiting questions of every loop under a directory to their parent."""
    from . import ask
    root = Path(args.dir).resolve()
    user = Path(args.user_config) if args.user_config else None
    rows, failed, unconfigured = [], 0, 0
    for loop_dir in discover(root):
        store = Store(loop_dir)
        try:
            cfg = config.load(loop_dir, user)
        except config.ConfigError as exc:
            print(f"ravl: {loop_dir}: {exc}", file=sys.stderr)
            failed += 1
            continue
        results = {} if args.list else {r["id"]: r for r in ask.deliver(store, cfg)}
        for question in store.open_questions():
            result = results.get(question["id"])
            if result and result["sent"]:
                state = "sent now"
            elif result:
                state, failed = f"not sent: {result['error']}", failed + 1
            elif question.get("delivered"):
                state = f"sent {question['delivered']}"
            elif not cfg["ask"].get("command"):
                state, unconfigured = "waiting: no ask command is configured", unconfigured + 1
            else:
                state = "waiting" + (f": last attempt failed ({question['delivery_error']})"
                                     if question.get("delivery_error") else "")
            rows.append({"loop": str(loop_dir), "id": question["id"], "asked": question["asked"],
                         "state": state, "text": question["text"]})
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            rel = Path(row["loop"]).relative_to(root) if Path(row["loop"]) != root else Path(".")
            print(f"{rel}  {row['id']}  {row['state']}\n    {row['text']}")
        if not rows:
            print("no open questions")
        if unconfigured:
            print("\nTo have questions carried to you, name a command under [ask] in a settings file:\n"
                  '    [ask]\n    command = ["/path/to/a/program"]\n'
                  "It receives each question as JSON on standard input. Answer with: ravl answer DIR ID \"...\"")
    return 1 if failed else 0


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
    p.add_argument("--json", action="store_true", help="with a run id: print the trace itself")
    p.add_argument("--last", type=int, default=20); p.set_defaults(func=cmd_runs)

    p = sub.add_parser("set", help="owner setting for the execution mode")
    p.add_argument("dir"); p.add_argument("mode", choices=config.MODES); p.set_defaults(func=cmd_set)

    p = sub.add_parser("config", help="show or choose the agent program and model: for this machine, or for a folder")
    p.add_argument("action", nargs="?", choices=["set"]); p.add_argument("name", nargs="?")
    p.add_argument("--model", help="model name passed to the agent program")
    p.add_argument("--dir", help="a folder: show what applies there, or with `set` write its ravl.toml, "
                                 "which applies to every loop in it and below")
    p.add_argument("--user-config", help="write this file in place of ~/.config/ravl/config.toml")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("ask", help="send waiting questions to the loops' parent through the configured command")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--list", action="store_true", help="show the open questions and whether each was sent; send nothing")
    p.add_argument("--json", action="store_true")
    p.add_argument("--user-config", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_ask)

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

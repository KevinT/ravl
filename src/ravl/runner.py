"""One run of a loop: Reflect, Act, Verify, Learn, each performed once.

There is no branch back to an earlier phase and no retry. A run that does not
produce the outcome is recorded, and the record is the next run's input.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import timedelta
from pathlib import Path

from . import __version__, codegen, config, llm, prompts, spec as specmod, verify
from .store import Store, Trace, iso, parse_iso, readable, utcnow, window_llm_calls, write_atomic


def run(loop_dir: Path, user_config: Path | None = None) -> dict:
    """Perform one run and return its trace."""
    loop_dir = Path(loop_dir).resolve()
    spec = specmod.load(loop_dir)
    cfg = config.load(loop_dir, user_config)
    store = Store(loop_dir)
    with store.lock():
        # Sortable by start time to the millisecond; runs of one loop never overlap.
        moment = time.time()
        run_id = (time.strftime("%Y%m%dT%H%M%S", time.gmtime(moment))
                  + f"{int(moment * 1000) % 1000:03d}Z-" + os.urandom(2).hex())
        previous = _close_crashed(store)
        trace = Trace(store, run_id, __version__)
        state = store.state()
        env = {"RAVL_LOOP_DIR": str(loop_dir), "RAVL_RUN_ID": run_id,
               "RAVL_RUN_DIR": str(trace.dir), "RAVL_RUN_STARTED": str(int(trace.started))}

        reflect = _reflect(spec, cfg, store, state, previous, env, trace)
        act = _act(spec, cfg, store, state, reflect, env, trace)
        post = _verify(spec, cfg, loop_dir, reflect, act, env, trace)
        _learn(spec, cfg, store, state, reflect, act, post, env, trace)

        trace.finish()
        store.prune(int(cfg["run"].get("keep_runs", 200)))
        return trace.data


def _close_crashed(store: Store) -> dict | None:
    """A previous trace still marked running, with the lock free, is a run that died."""
    previous = store.last_trace()
    if previous and previous.get("status") == "running":
        previous["status"] = "crashed"
        write_atomic(store.runs / previous["run_id"] / "trace.json",
                     json.dumps(previous, indent=2, sort_keys=True) + "\n")
    return previous


# ------------------------------------------------------------------ REFLECT

def _reflect(spec, cfg, store, state, previous, env, trace) -> dict:
    """Read the world, the steer this loop may read, the budget and the mode. No decision."""
    owner = cfg["mode"]
    if owner == "lock":
        mode = {"value": "code", "source": "owner", "setting": "lock"}
    elif owner == "never-lock":
        mode = {"value": "llm", "source": "owner", "setting": "never-lock"}
    else:
        mode = {"value": state["mode"], "source": "learned", "setting": "learned"}

    checks = verify.run_checks(spec, store.dir, {**env, "RAVL_PHASE": "reflect"},
                               int(cfg["run"]["check_timeout_s"]))
    trace.data["cost"]["checks_run"] += sum(1 for c in checks if c["status"] != "unchecked")
    world = verify.summarize(checks)

    neighbours = []
    for path, relation in readable(store.dir, int(cfg["read"]["radius"])):
        key = path.name
        seen = state["relevance"].get(key, {"offered": 0, "contributed": 0})
        if seen["offered"] >= 5 and seen["contributed"] == 0 and relation != "child":
            continue  # narrowed by learned relevance: offered five times, never used
        other = Store(path)
        entries = [f"[{key}] {d['text']}" for d in other.domain()
                   if d.get("scope") == "portable" or relation != "sibling"]
        if relation in ("child", "descendant"):
            last = other.last_trace()
            status = last.get("verify", {}).get("status", "?") if last else "never run"
            entries.insert(0, f"[{key}] {relation} loop; last verify: {status}; mode: {other.state()['mode']}")
            entries += [f"[{key}] question for you as its owner ({q['id']}): {q['text']}"
                        for q in other.open_questions()]
        if entries:
            neighbours.append({"loop": key, "relation": relation, "entries": entries})

    budget = cfg["budget"]
    spent = window_llm_calls(store.dir, float(budget["window_hours"]))
    last_run = "This is the first run."
    if previous:
        last_run = (f"Run {previous['run_id']} {previous.get('status')}; "
                    f"verify: {previous.get('verify', {}).get('status', 'not reached')}; "
                    f"act: {previous.get('act', {}).get('driver', 'not reached')}.")
        if previous.get("status") == "crashed":
            last_run += " It stopped before finishing; its trace shows the last phase reached."

    record = {
        "mode": mode,
        "world": {**world, "checks": checks},
        "last_run": last_run,
        "steer": store.steer_text("reflect.md"),
        "answers": [f"{q['text']} -> {q['answer']}" for q in store.questions() if q.get("answer")][-10:],
        "domain": [d["text"] for d in store.domain()][-40:],
        "constraints": store.constraints(),
        "neighbours": neighbours,
        "resources": {str(k): str(v) for k, v in cfg.get("resources", {}).items()},
        "budget": {"llm_calls_in_window": spent, "limit": int(budget["llm_calls_per_window"]),
                   "window_hours": budget["window_hours"]},
    }
    trace.phase("reflect", record)
    return record


# ---------------------------------------------------------------------- ACT

def _act(spec, cfg, store, state, reflect, env, trace) -> dict:
    record = _act_inner(spec, cfg, store, state, reflect, env, trace)
    trace.phase("act", record)
    return record


def _hold_in_force(store, state, cfg, fingerprint) -> bool:
    hold = state.get("hold")
    if not hold or hold.get("fingerprint") != fingerprint:
        return False
    since = parse_iso(hold["since"])
    if utcnow() - since > timedelta(hours=float(cfg["learn"]["hold_hours"])):
        return False
    answered = [q for q in store.questions() if q.get("answered") and parse_iso(q["answered"]) >= since]
    return not answered


def _act_inner(spec, cfg, store, state, reflect, env, trace) -> dict:
    world, mode = reflect["world"], reflect["mode"]
    if world["status"] == "pass":
        return {"driver": "none", "reason": "the outcome already holds"}
    if world["status"] == "fail" and _hold_in_force(store, state, cfg, world["fingerprint"]):
        return {"driver": "held", "reason": state["hold"].get("reason", "held by the last Learn")}

    if mode["value"] == "code":
        if store.generated.is_file():
            problems = codegen.validate(store.generated.read_text(),
                                        cfg["codegen"]["whitelist"], reflect["constraints"])
            if problems:
                return {"driver": "code", "ok": False, "rejected": problems,
                        "error": "generated code rejected before running: " + "; ".join(problems)}
            result = codegen.run(store.generated, store.dir, {**env, "RAVL_PHASE": "act"},
                                 int(cfg["run"]["code_timeout_s"]))
            return {"driver": "code", **result,
                    "effects": _confirm(result.get("claims", []), store.dir, trace.started)}
        if mode["source"] == "owner":
            return {"driver": "blocked", "world": False,
                    "reason": "mode is set to lock and no generated code exists"}

    command = config.llm_command(cfg, "act")
    if not command:
        return {"driver": "blocked", "world": True, "reason": "no LLM command is configured"}
    budget = reflect["budget"]
    if budget["llm_calls_in_window"] >= budget["limit"]:
        return {"driver": "blocked", "world": True, "budget": True,
                "reason": f"budget of {budget['limit']} LLM calls per {budget['window_hours']}h is spent"}

    prompt = prompts.act({
        "loop_dir": str(store.dir), "spec_raw": spec.raw, "precheck": world["checks"],
        "last_run": reflect["last_run"], "steer": reflect["steer"], "answers": reflect["answers"],
        "domain": reflect["domain"],
        "neighbours": [e for n in reflect["neighbours"] for e in n["entries"]],
        "constraints": [c["text"] for c in reflect["constraints"]],
        "resources": [f"{k}: {v}" for k, v in reflect["resources"].items()],
        "children_editable": bool(cfg["children"]["editable"]),
    })
    trace.save("act-prompt.md", prompt)
    result = llm.call(command, prompt, store.dir, {**env, "RAVL_PHASE": "act"},
                      int(cfg["llm"]["timeout_s"]))
    trace.charge_llm(result)
    trace.save("act-response.md", result.text or "")
    report = llm.last_json(result.text) or {}
    return {
        "driver": "llm", "ok": result.ok, "error": result.error,
        "reported": bool(report),
        "summary": str(report.get("summary", ""))[:1000],
        "procedure": [str(s) for s in report.get("procedure", [])][:60],
        "resources_used": [str(s) for s in report.get("resources_used", [])],
        "needs_owner": report.get("needs_owner") or None,
        "effects": _confirm([str(e) for e in report.get("effects", [])], store.dir, trace.started),
    }


def _confirm(claims: list[str], loop_dir: Path, started: float) -> list[dict]:
    """Check that each file Act claims to have written exists and changed during this run."""
    out = []
    for claim in claims:
        if claim.lower().startswith("action:"):
            out.append({"claim": claim, "confirmed": None, "note": "not a file; cannot be confirmed"})
            continue
        path = Path(claim) if os.path.isabs(claim) else loop_dir / claim
        if not path.exists():
            out.append({"claim": claim, "confirmed": False, "note": "does not exist"})
        elif path.stat().st_mtime < started - 1:
            out.append({"claim": claim, "confirmed": False, "note": "exists but was not changed during this run"})
        else:
            out.append({"claim": claim, "confirmed": True})
    return out


# ------------------------------------------------------------------- VERIFY

def _verify(spec, cfg, loop_dir, reflect, act, env, trace) -> dict:
    """Compare the effect against the owner's criteria. Takes no action."""
    if act["driver"] in ("none", "held", "blocked"):
        # Nothing was done, so the world Reflect read is the result.
        checks, reused = reflect["world"]["checks"], True
    else:
        checks = verify.run_checks(spec, loop_dir, {**env, "RAVL_PHASE": "verify"},
                                   int(cfg["run"]["check_timeout_s"]))
        trace.data["cost"]["checks_run"] += sum(1 for c in checks if c["status"] != "unchecked")
        reused = False
    record = {**verify.summarize(checks), "checks": checks, "reused_reflect": reused}
    trace.phase("verify", record)
    return record


# -------------------------------------------------------------------- LEARN

def _learn(spec, cfg, store, state, reflect, act, post, env, trace) -> dict:
    """Classify the run, decide whether the execution mode changes, write steer."""
    driver, status, mode = act["driver"], post["status"], reflect["mode"]
    record: dict = {"llm": False, "classification": None, "mode_change": None, "question": None}
    criteria = {c["id"]: c["text"] for c in post["checks"]}
    failing_text = "; ".join(criteria[i] for i in post["failing"])
    condition = post["fingerprint"] or "none"
    unconfirmed = [e["claim"] for e in act.get("effects", []) if e["confirmed"] is False]
    if unconfirmed:
        record["effect"] = "claimed but not produced: " + ", ".join(unconfirmed)

    judgement: dict = {}
    if driver in ("llm", "code") and status in ("pass", "fail") and (status == "fail" or driver == "llm"):
        judgement = _ask_learn(spec, cfg, store, reflect, act, post, env, trace, record)

    if status == "pass":
        state.pop("hold", None)
        store.close_questions("the outcome holds again", keep={"never-lock"})
    elif status == "fail":
        store.close_questions("the failing condition changed",
                              keep={condition, "never-lock"} | ({"budget"} if act.get("budget") else set()))

    # Question 8: world or solution. Without an LLM judgement, only what the trace shows.
    classification = judgement.get("classification")
    if status == "fail" and classification not in ("world", "solution"):
        if driver == "blocked" or act.get("ok") is False:
            classification = "world" if act.get("world", True) else "solution"
        elif driver == "held":
            classification = state.get("hold", {}).get("classification", "world")
        else:
            classification = "unclassified"
    record["classification"] = classification if status == "fail" else None
    record["fault"] = judgement.get("fault") if status == "fail" else None
    record["reason"] = str(judgement.get("reason", ""))[:500]

    # Streaks that drive the execution mode.
    if driver == "llm":
        if status == "pass":
            state["llm_pass_streak"] += 1
            state["llm_pass_runs"] = (state["llm_pass_runs"] + [trace.data["run_id"]])[-10:]
        else:
            state["llm_pass_streak"], state["llm_pass_runs"] = 0, []
    if driver == "code":
        state["code_fail_streak"] = 0 if status == "pass" else state["code_fail_streak"] + 1

    # Questions 8-9: a solution failure on code moves the loop back to LLM-driven.
    if (driver == "code" and status == "fail" and mode["source"] == "learned"
            and (classification == "solution" or act.get("rejected") or state["code_fail_streak"] >= 2)):
        rejected = store.generated.parent / "rejected" / f"act-{trace.data['run_id']}.py"
        rejected.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(store.generated), str(rejected))
        state.update(mode="llm", code_fail_streak=0, llm_pass_streak=0, llm_pass_runs=[])
        record["mode_change"] = "code-driven -> LLM-driven: the generated code no longer meets the verifier"

    # Hold and question for the owner.
    question = judgement.get("question") or act.get("needs_owner")
    if status == "fail" and driver == "blocked":
        if act.get("budget"):
            condition = "budget"
        question = (f"Verifier fails ({failing_text}) and Act could not run: {act['reason']}. "
                    "Either act on the failing criteria yourself or change this loop's configuration.")
    if status == "fail" and driver in ("llm", "code") and not judgement and not question:
        question = (f"Verifier fails ({failing_text}) after Act, and Learn could not classify the "
                    f"failure because the LLM was unavailable ({record.get('llm_error', 'no LLM command')}).")
    if status == "fail" and driver != "held":
        if judgement.get("hold") or act.get("needs_owner"):
            state["hold"] = {"fingerprint": post["fingerprint"], "since": iso(utcnow()),
                             "classification": classification,
                             "reason": str(judgement.get("reason") or act.get("reason")
                                           or "waiting for the owner")[:300]}
        else:
            state.pop("hold", None)
    if status == "fail" and question:
        asked = store.ask(condition, str(question), trace.data["run_id"])
        record["question"] = asked["id"] if asked else None
    if status == "no-verifier":
        store.ask("no-verifier", "No criterion in the Verifier section has a check, so this loop "
                  "cannot tell whether its outcome holds. Add a `check` block to at least one "
                  "criterion in ravl.md.", trace.data["run_id"])

    # Learnings, kept apart: domain is context, execution is enforced.
    if judgement:
        stamp = {"run": trace.data["run_id"], "at": iso(utcnow())}
        record["domain_added"] = store.add_domain(
            [{"text": str(d.get("text", "")), "scope": d.get("scope", "local"), **stamp}
             for d in judgement.get("domain", []) if isinstance(d, dict)])
        record["execution_added"] = store.add_constraints(
            [{"text": str(e.get("text", "")), "forbid": e.get("forbid") or None, **stamp}
             for e in judgement.get("execution", []) if isinstance(e, dict)])
        used = {str(c) for c in judgement.get("contributed", [])} | set(act.get("resources_used", []))
        for neighbour in reflect["neighbours"]:
            seen = state["relevance"].setdefault(neighbour["loop"], {"offered": 0, "contributed": 0})
            seen["offered"] += 1
            seen["contributed"] += 1 if neighbour["loop"] in used else 0
        if status == "pass" and driver == "llm":
            state["resources_contributed"] = sorted(used & set(reflect["resources"]))

    # Question 10: ready to move toward code-driven?
    if (driver == "llm" and status == "pass" and mode["source"] == "learned"
            and state["llm_pass_streak"] >= int(cfg["learn"]["promote_after"])):
        _generate(spec, cfg, store, state, reflect, env, trace, record)

    store.save_state(state)
    _write_steer(spec, store, state, reflect, act, post, record, judgement, trace)
    trace.phase("learn", record)
    return record


def _ask_learn(spec, cfg, store, reflect, act, post, env, trace, record) -> dict:
    command = config.llm_command(cfg, "learn")
    if not command:
        return {}
    prompt = prompts.learn({
        "intent": spec.intent, "driver": act["driver"], "precheck": reflect["world"]["checks"],
        "act": {k: v for k, v in act.items() if k != "driver"},
        "postcheck": post["checks"], "steer": reflect["steer"],
        "domain": reflect["domain"], "constraints": [c["text"] for c in reflect["constraints"]],
    })
    trace.save("learn-prompt.md", prompt)
    result = llm.call(command, prompt, store.dir, {**env, "RAVL_PHASE": "learn"},
                      int(cfg["llm"]["timeout_s"]))
    trace.charge_llm(result)
    trace.save("learn-response.md", result.text or "")
    record["llm"] = True
    judgement = llm.last_json(result.text) if result.ok else None
    if not judgement:
        record["llm_error"] = result.error or "reply was not a JSON object"
        return {}
    return judgement


def _generate(spec, cfg, store, state, reflect, env, trace, record) -> None:
    """Ask for code that performs Act; accept it only if it passes validation."""
    command = config.llm_command(cfg, "codegen")
    if not command:
        return
    runs = []
    for run_id in state["llm_pass_runs"][-int(cfg["learn"]["promote_after"]):]:
        act = trace.data["act"] if run_id == trace.data["run_id"] else (store.trace(run_id) or {}).get("act", {})
        runs.append({"run_id": run_id, "summary": act.get("summary", ""),
                     "procedure": act.get("procedure", []),
                     "effects": [e["claim"] for e in act.get("effects", [])]})
    contributed = state.get("resources_contributed", [])
    prompt = prompts.codegen({
        "spec_raw": spec.raw, "runs": runs,
        "constraints": [c["text"] for c in reflect["constraints"]],
        "resources": [f"{k}: {v}" for k, v in reflect["resources"].items()
                      if not contributed or k in contributed],
        "whitelist": ", ".join(cfg["codegen"]["whitelist"]),
    })
    trace.save("codegen-prompt.md", prompt)
    result = llm.call(command, prompt, store.dir, {**env, "RAVL_PHASE": "codegen"},
                      int(cfg["llm"]["timeout_s"]))
    trace.charge_llm(result)
    trace.save("codegen-response.md", result.text or "")
    if not result.ok:
        record["codegen"] = {"result": "failed", "error": result.error}
        return
    program = codegen.extract_program(result.text)
    if program is None:
        verdict = llm.last_json(result.text) or {}
        state["codegen_declined"] += 1
        state["llm_pass_streak"], state["llm_pass_runs"] = 0, []
        record["codegen"] = {"result": "declined", "reason": str(verdict.get("reason", ""))[:300]}
        if state["codegen_declined"] >= int(cfg["learn"]["never_lock_after"]):
            store.ask("never-lock", "This loop has not converged on a repeatable procedure after "
                      f"{state['codegen_declined']} attempts to generate code "
                      f"({record['codegen']['reason']}). Set it to never-lock?", trace.data["run_id"])
        return
    problems = codegen.validate(program, cfg["codegen"]["whitelist"], store.constraints())
    if problems:
        trace.save("codegen-rejected.py", program)
        record["codegen"] = {"result": "rejected", "problems": problems}
        return
    write_atomic(store.generated, program)
    state.update(mode="code", code_fail_streak=0, codegen_declined=0)
    record["codegen"] = {"result": "accepted", "path": str(store.generated.relative_to(store.dir))}
    record["mode_change"] = (f"LLM-driven -> code-driven after {state['llm_pass_streak']} "
                             "consecutive LLM-driven passes")


def _write_steer(spec, store, state, reflect, act, post, record, judgement, trace) -> None:
    """Steer is short and addressed: next Reflect, the owner, sibling loops."""
    run_id, status, driver = trace.data["run_id"], post["status"], act["driver"]
    if judgement.get("steer"):
        write_atomic(store.steer / "reflect.md",
                     f"<!-- written by Learn, run {run_id} -->\n{str(judgement['steer']).strip()}\n")
    elif status == "pass" and driver == "none" and store.steer_text("reflect.md"):
        pass  # nothing new was learned; earlier steer stays in force

    criteria = {c["id"]: c["text"] for c in post["checks"]}
    # No run id, time or counter: a run that changes nothing leaves this file unchanged.
    lines = [f"# {spec.title}: for the owner", "",
             f"- Verify: {status}" + (f" ({'; '.join(criteria[i] for i in post['failing'])})" if post["failing"] else ""),
             f"- Act: {driver}" + (f" ({act.get('summary') or act.get('reason') or act.get('error') or ''})".replace(" ()", "")),
             f"- Execution mode: {'code-driven' if state['mode'] == 'code' else 'LLM-driven'} "
             f"({reflect['mode']['setting']})"]
    if record.get("classification"):
        lines.append(f"- Failure classified as: {record['classification']}"
                     + (f" ({record['reason']})" if record.get("reason") else ""))
    if record.get("mode_change"):
        lines.append(f"- Mode change: {record['mode_change']}")
    if record.get("effect"):
        lines.append(f"- Effect: {record['effect']}")
    if post["unchecked"]:
        lines.append("- Criteria with no check (not verified): "
                     + "; ".join(criteria[i] for i in post["unchecked"]))
    open_questions = store.open_questions()
    lines += ["", "## Open questions", ""]
    lines += [f"- **{q['id']}** ({q['asked']}): {q['text']}" for q in open_questions] or ["None."]
    write_atomic(store.steer / "owner.md", "\n".join(lines) + "\n")

    portable = [d["text"] for d in store.domain() if d.get("scope") == "portable"]
    if portable:
        write_atomic(store.steer / "siblings.md",
                     f"# {spec.title}: patterns that may apply to sibling loops\n\n"
                     + "\n".join(f"- {text}" for text in portable) + "\n")

"""The phase contract: what one run does, in each of the situations the model names."""

import json

from conftest import ACT_WRITE, MAINTAIN, PRODUCE, PROGRAM, act, learn
from ravl import cli


def test_outcome_that_already_holds_costs_no_llm_call(h):
    loop = h.loop("flag", MAINTAIN)
    (loop / "flag").touch()
    trace = h.run(loop)
    assert trace["act"]["driver"] == "none"
    assert trace["verify"]["status"] == "pass" and trace["verify"]["reused_reflect"]
    assert trace["cost"]["llm_calls"] == 0 and h.calls() == []
    assert trace["status"] == "complete"


def test_a_run_that_changes_nothing_leaves_the_learnings_untouched(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learn(steer="touch the flag")})
    h.run(loop)

    def snapshot():
        return {p.relative_to(loop): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in sorted((loop / "learnings").rglob("*")) if p.is_file()}

    h.run(loop)  # the first run after a repair records that Act was no longer needed
    before = snapshot()
    for _ in range(3):
        assert h.run(loop)["act"]["driver"] == "none"
    assert snapshot() == before  # so learnings can be version-controlled without churn


def test_llm_driven_act_repairs_and_the_effect_is_confirmed(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learn(steer="Recreate the flag with touch.")})
    trace = h.run(loop)
    assert trace["reflect"]["world"]["status"] == "fail"
    assert "flag is missing" in h.prompt("act")  # the failing check's output is Act's evidence
    assert trace["act"]["driver"] == "llm"
    assert trace["act"]["effects"] == [{"claim": "flag", "confirmed": True}]
    assert trace["verify"]["status"] == "pass" and not trace["verify"]["reused_reflect"]
    assert h.calls() == ["act", "learn"]
    assert trace["cost"]["llm_calls"] == 2
    assert trace["cost"]["tokens"]["fake-1"]["input"] > 0 and trace["cost"]["cost_usd"] == 0.02


def test_second_run_reads_the_first_runs_steer(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "learn": learn(steer="Write out.txt with a single echo.")})
    h.run(loop)
    second = h.run(loop)
    assert "Write out.txt with a single echo." in second["reflect"]["steer"]
    assert "Write out.txt with a single echo." in h.prompt("act")
    assert second["reflect"]["last_run"].startswith("Run ") and "verify: pass" in second["reflect"]["last_run"]


def test_a_claimed_effect_that_was_not_produced_is_recorded_as_such(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act([], ["flag"]), "learn": learn(classification="solution", fault="derivation",
                                                       reason="claimed a write that did not happen")})
    trace = h.run(loop)
    assert trace["act"]["effects"] == [{"claim": "flag", "confirmed": False, "note": "does not exist"}]
    assert trace["learn"]["effect"] == "claimed but not produced: flag"
    assert trace["verify"]["status"] == "fail" and trace["learn"]["classification"] == "solution"


def test_one_attempt_per_run_no_retry_when_verify_fails(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act([], []), "learn": learn(classification="solution", fault="derivation")})
    h.run(loop)
    assert h.calls() == ["act", "learn"]  # Act ran once although Verify failed


def test_world_failure_holds_asks_the_owner_once_and_waits(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act([], [], needs_owner="Run `login` on the host; the session expired."),
              "learn": learn(classification="world", reason="credential expired", hold=True,
                             question="The session expired. Run `login` on the host.")})
    first = h.run(loop)
    assert first["learn"]["classification"] == "world" and first["learn"]["question"] == "q-001"
    second = h.run(loop)
    third = h.run(loop)
    assert second["act"]["driver"] == "held" and third["act"]["driver"] == "held"
    assert second["cost"]["llm_calls"] == 0 and h.calls() == ["act", "learn"]
    assert second["learn"]["classification"] == "world"  # carried from the hold, not re-judged
    questions = h.store(loop).questions()
    assert len(questions) == 1 and questions[0]["text"].startswith("The session expired")
    assert h.store(loop).state()["mode"] == "llm"  # a world failure changes no mode


def test_an_owner_answer_releases_the_hold(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act([], [], needs_owner="need a login"),
              "learn": learn(classification="world", hold=True, question="Log in please.")})
    h.run(loop)
    assert cli.main(["answer", str(loop), "q-001", "done,", "logged", "in"]) == 0
    h.behave({"act": act(["touch flag"], ["flag"]), "learn": learn()})
    trace = h.run(loop)
    assert trace["act"]["driver"] == "llm" and trace["verify"]["status"] == "pass"
    assert "Log in please. -> done, logged in" in h.prompt("act")
    assert h.store(loop).open_questions() == []
    assert "hold" not in h.store(loop).state()


def test_recovery_closes_the_open_question(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({"act": act([], [], needs_owner="x"), "learn": learn(classification="world", hold=True, question="Fix it.")})
    h.run(loop)
    (loop / "flag").touch()  # the world recovers without the loop
    trace = h.run(loop)
    assert trace["act"]["driver"] == "none" and trace["verify"]["status"] == "pass"
    question = h.store(loop).questions()[0]
    assert "the outcome holds again" in question["closed"]


def test_without_an_llm_the_failure_is_still_detected_and_escalated(h):
    loop = h.loop("flag", MAINTAIN)
    trace = h.run(loop, llm=False)
    assert trace["act"]["driver"] == "blocked" and trace["verify"]["status"] == "fail"
    assert trace["learn"]["classification"] == "world"
    text = h.store(loop).open_questions()[0]["text"]
    assert "The file `flag` exists." in text and "no LLM command is configured" in text
    h.run(loop, llm=False)
    assert len(h.store(loop).questions()) == 1  # same condition, one question


def test_llm_outage_during_act_is_a_world_failure_with_a_question(h):
    loop = h.loop("flag", MAINTAIN)
    h.behave({})  # the stand-in exits non-zero in every phase
    trace = h.run(loop)
    assert trace["act"]["driver"] == "llm" and trace["act"]["ok"] is False
    assert trace["learn"]["classification"] == "world"
    assert "Learn could not classify" in h.store(loop).open_questions()[0]["text"]


def test_budget_exhaustion_blocks_llm_driven_act(h):
    loop = h.loop("flag", MAINTAIN)
    (loop / "config").mkdir()
    (loop / "config" / "loop.toml").write_text("[budget]\nllm_calls_per_window = 2\n")
    h.behave({"act": act([], []), "learn": learn(classification="solution", fault="derivation")})
    h.run(loop)
    trace = h.run(loop)
    assert trace["act"]["driver"] == "blocked" and trace["act"]["budget"] is True
    assert trace["learn"]["classification"] == "world"
    assert h.calls() == ["act", "learn"]
    assert [q["condition"] for q in h.store(loop).open_questions()] == ["budget"]


def test_loop_without_a_check_is_in_the_red_phase_not_failed(h):
    loop = h.loop("bare", "# Bare\n\n## Intent\n\nWrite out.txt.\n\n## Verifier\n\n- It looks right.\n")
    h.behave({"act": ACT_WRITE})
    trace = h.run(loop)
    assert trace["act"]["driver"] == "llm" and trace["verify"]["status"] == "no-verifier"
    assert trace["learn"]["classification"] is None
    assert h.store(loop).open_questions()[0]["condition"] == "no-verifier"


def test_a_run_that_died_is_marked_crashed_and_is_the_next_runs_first_input(h):
    loop = h.loop("flag", MAINTAIN)
    (loop / "flag").touch()
    dead = loop / "runs" / "20200101T000000Z-dead"
    dead.mkdir(parents=True)
    (dead / "trace.json").write_text(json.dumps(
        {"run_id": "20200101T000000Z-dead", "status": "running", "started": "2020-01-01T00:00:00Z",
         "reflect": {}, "cost": {"llm_calls": 0}}))
    trace = h.run(loop)
    assert json.loads((dead / "trace.json").read_text())["status"] == "crashed"
    assert "crashed" in trace["reflect"]["last_run"] and "stopped before finishing" in trace["reflect"]["last_run"]


def test_cli_run_exit_status_and_list(h, capsys):
    loop = h.loop("flag", MAINTAIN)
    assert cli.main(["run", str(loop), "--user-config", str(h.empty_config)]) == 1
    (loop / "flag").touch()
    assert cli.main(["run", str(loop), "--user-config", str(h.empty_config)]) == 0
    capsys.readouterr()
    assert cli.main(["list", str(h.tmp / "tree"), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["last_verify"] == "pass" and rows[0]["questions"] == []
    assert cli.main(["run", str(h.tmp / "nowhere")]) == 2


# ---- execution mode: learned, and settable by the owner

def _promote(h, loop):
    h.behave({"act": ACT_WRITE, "learn": learn(steer="echo ready > out.txt"), "codegen": PROGRAM})
    return [h.run(loop) for _ in range(3)]


def test_three_llm_driven_passes_generate_code_and_llm_calls_drop_to_zero(h):
    loop = h.loop("produce", PRODUCE)
    traces = _promote(h, loop)
    assert [t["act"]["driver"] for t in traces] == ["llm", "llm", "llm"]
    assert traces[1]["learn"].get("codegen") is None
    assert traces[2]["learn"]["codegen"]["result"] == "accepted"
    assert "LLM-driven -> code-driven" in traces[2]["learn"]["mode_change"]
    assert (loop / "learnings" / "generated" / "act.py").is_file()
    assert "echo ready > out.txt" in h.prompt("codegen")  # the passing runs' procedure is the input

    before = len(h.calls())
    fourth = h.run(loop)
    assert fourth["reflect"]["mode"] == {"value": "code", "source": "learned", "setting": "learned"}
    assert fourth["act"]["driver"] == "code" and fourth["act"]["effects"][0]["confirmed"] is True
    assert fourth["verify"]["status"] == "pass"
    assert fourth["cost"]["llm_calls"] == 0 and len(h.calls()) == before


def test_solution_failure_of_generated_code_returns_the_loop_to_llm_driven(h):
    loop = h.loop("produce", PRODUCE)
    _promote(h, loop)
    # The world changes so the generated procedure no longer meets the verifier.
    spec = (loop / "ravl.md").read_text().replace("grep -q ready out.txt", "grep -q steady out.txt")
    (loop / "ravl.md").write_text(spec)
    h.behave({"learn": learn(classification="solution", fault="derivation", reason="the code writes the old word"),
              "act": act(["echo steady > out.txt"], ["out.txt"]), "codegen": PROGRAM})
    failed = h.run(loop)
    assert failed["act"]["driver"] == "code" and failed["verify"]["status"] == "fail"
    assert failed["learn"]["classification"] == "solution"
    assert "code-driven -> LLM-driven" in failed["learn"]["mode_change"]
    assert not (loop / "learnings" / "generated" / "act.py").exists()
    assert list((loop / "learnings" / "generated" / "rejected").glob("act-*.py"))
    again = h.run(loop)
    assert again["act"]["driver"] == "llm" and again["verify"]["status"] == "pass"


def test_world_failure_of_generated_code_changes_no_mode(h):
    loop = h.loop("produce", PRODUCE)
    _promote(h, loop)
    (loop / "ravl.md").write_text((loop / "ravl.md").read_text().replace("grep -q ready", "grep -q steady"))
    h.behave({"learn": learn(classification="world", reason="upstream is down")})
    failed = h.run(loop)
    assert failed["learn"]["classification"] == "world" and failed["learn"]["mode_change"] is None
    assert h.store(loop).state()["mode"] == "code"


def test_never_lock_keeps_the_loop_llm_driven(h):
    loop = h.loop("produce", PRODUCE)
    assert cli.main(["set", str(loop), "never-lock"]) == 0
    traces = _promote(h, loop) + [h.run(loop)]
    assert all(t["act"]["driver"] == "llm" for t in traces)
    assert all(t["learn"].get("codegen") is None for t in traces)
    assert traces[0]["reflect"]["mode"]["source"] == "owner"


def test_lock_runs_the_current_code_and_a_failure_does_not_unlock_it(h):
    loop = h.loop("produce", PRODUCE)
    _promote(h, loop)
    cli.main(["set", str(loop), "lock"])
    (loop / "ravl.md").write_text((loop / "ravl.md").read_text().replace("grep -q ready", "grep -q steady"))
    h.behave({"learn": learn(classification="solution", fault="derivation")})
    trace = h.run(loop)
    assert trace["reflect"]["mode"] == {"value": "code", "source": "owner", "setting": "lock"}
    assert trace["act"]["driver"] == "code" and trace["verify"]["status"] == "fail"
    assert trace["learn"]["mode_change"] is None
    assert (loop / "learnings" / "generated" / "act.py").is_file()


def test_lock_without_code_is_reported_not_improvised(h):
    loop = h.loop("produce", PRODUCE)
    cli.main(["set", str(loop), "lock"])
    trace = h.run(loop)
    assert trace["act"]["driver"] == "blocked" and "no generated code" in trace["act"]["reason"]
    assert h.calls() == []


def test_a_procedure_that_is_not_repeatable_is_not_turned_into_code(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "learn": learn(),
              "codegen": json.dumps({"repeatable": False, "reason": "each run needed a different fix"})})
    traces = [h.run(loop) for _ in range(3)]
    assert traces[2]["learn"]["codegen"]["result"] == "declined"
    state = h.store(loop).state()
    assert state["mode"] == "llm" and state["llm_pass_streak"] == 0 and state["codegen_declined"] == 1

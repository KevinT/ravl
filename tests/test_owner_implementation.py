"""A specification that carries its implementation: a scheduled job stated as a loop.

The implementation runs on every run. When it stops meeting the verifier, repair by
an LLM is attempted a bounded number of times, and then the owner is asked.
"""

import json

from conftest import act, learn
from ravl import spec as specmod

JOB = """\
# Copy the source

## Intent

`out` is a copy of `source`, refreshed on every run.

## Act

```act
cp source out
```

## Verifier

- The implementation ran to completion in this run.
  ```check
  test -e "$RAVL_RUN_DIR/act-ok"
  ```
- `out` matches `source`.
  ```check
  cmp -s source out
  ```
"""

SOLUTION = dict(classification="solution", fault="derivation", reason="the source file is missing")
REPAIR = act(["echo data > source", "cp source out"], ["out"])


def _job(h):
    loop = h.loop("job", JOB)
    (loop / "source").write_text("v1\n")
    return loop


def _state(h, loop):
    return json.loads((loop / "learnings" / "state.json").read_text())


def test_the_act_block_is_read_from_the_specification(h):
    loop = _job(h)
    assert specmod.load(loop).act == "cp source out"
    assert specmod.load(h.loop("other", "# X\n## Intent\nx\n## Verifier\n- y\n")).act is None


def test_the_implementation_runs_on_every_run_with_no_llm(h):
    loop = _job(h)
    first = h.run(loop)
    (loop / "source").write_text("v2\n")
    second = h.run(loop)
    for trace in (first, second):
        assert trace["reflect"]["mode"]["value"] == "code"
        assert trace["act"]["driver"] == "code" and trace["act"]["source"] == "owner"
        assert trace["verify"]["status"] == "pass" and trace["cost"]["llm_calls"] == 0
    assert (loop / "out").read_text() == "v2\n"   # not skipped although `out` existed already
    assert h.calls() == []


def test_solution_failure_gets_one_llm_repair_then_the_implementation_runs_again(h):
    loop = _job(h)
    (loop / "source").unlink()
    h.behave({"learn": learn(**SOLUTION), "act": REPAIR})
    failed = h.run(loop)
    assert failed["act"]["driver"] == "code" and failed["act"]["exit"] == 1
    assert "No such file" in failed["act"]["output"]
    assert failed["learn"]["classification"] == "solution"
    assert "next Act is a repair attempt" in failed["learn"]["mode_change"]
    assert h.calls() == ["learn"]

    h.behave({"learn": learn(), "act": REPAIR})
    repaired = h.run(loop)
    assert repaired["act"]["driver"] == "llm" and repaired["verify"]["status"] == "pass"
    prompt = h.prompt("act")
    assert "This is a repair attempt (1 of 2)" in prompt and "No such file" in prompt
    assert "owner's implementation runs again" in repaired["learn"]["mode_change"]
    assert not (loop / "learnings" / "generated").exists()   # nothing is generated over the owner's code

    before = len(h.calls())
    after = h.run(loop)
    assert after["act"]["driver"] == "code" and after["verify"]["status"] == "pass"
    assert len(h.calls()) == before


def test_world_failure_keeps_running_the_implementation_and_is_judged_once(h):
    loop = _job(h)
    (loop / "source").unlink()
    h.behave({"learn": learn(classification="world", reason="the upstream has not published yet")})
    traces = [h.run(loop) for _ in range(4)]
    assert all(t["act"]["driver"] == "code" for t in traces)       # still attempted every run
    assert all(t["learn"]["classification"] == "world" for t in traces)
    assert h.calls() == ["learn"]                                  # same failure, one judgement
    assert traces[1]["learn"]["judgement"] == "reused"
    assert _state(h, loop)["mode"] == "code" and h.store(loop).open_questions() == []

    (loop / "source").write_text("v1\n")                           # the world recovers
    assert h.run(loop)["verify"]["status"] == "pass"
    assert "judged" not in _state(h, loop) and "failing_since" not in _state(h, loop)


def test_repair_is_bounded_then_the_owner_is_asked_and_the_job_keeps_running(h):
    loop = _job(h)
    (loop / "source").unlink()
    h.behave({"learn": learn(**SOLUTION), "act": act([], [])})     # the repair agent achieves nothing
    kinds = [h.run(loop)["act"]["driver"] for _ in range(3)]
    assert kinds == ["code", "llm", "llm"]
    state = _state(h, loop)
    assert state["repair"]["attempts"] == 2 and "hold" in state
    questions = h.store(loop).open_questions()
    assert len(questions) == 1 and "2 repair attempts did not restore the outcome" in questions[0]["text"]

    spent = len(h.calls())
    held = [h.run(loop) for _ in range(3)]
    assert all(t["act"]["driver"] == "code" and t["act"]["held"] for t in held)   # the job itself still runs
    assert len(h.calls()) == spent and len(h.store(loop).questions()) == 1       # no LLM, no second question

    (loop / "source").write_text("v1\n")                            # the owner removes the cause, says nothing
    recovered = h.run(loop)
    assert recovered["verify"]["status"] == "pass"
    state = _state(h, loop)
    assert state["mode"] == "code" and "hold" not in state and "repair" not in state
    assert h.store(loop).open_questions() == []


def test_a_failure_nobody_was_asked_about_reaches_the_owner_after_escalate_hours(h):
    loop = _job(h)
    (loop / "source").unlink()
    h.behave({"learn": learn(classification="world", reason="upstream is late")})
    h.run(loop)
    assert h.store(loop).open_questions() == []
    path = loop / "learnings" / "state.json"
    state = json.loads(path.read_text())
    state["failing_since"] = "2020-01-01T00:00:00Z"
    path.write_text(json.dumps(state))
    trace = h.run(loop)
    assert trace["cost"]["llm_calls"] == 0
    text = h.store(loop).open_questions()[0]["text"]
    assert "has not held since 2020-01-01T00:00:00Z" in text and "upstream is late" in text


def test_without_an_llm_a_failing_implementation_still_reaches_the_owner(h):
    loop = _job(h)
    (loop / "source").unlink()
    trace = h.run(loop, llm=False)
    assert trace["act"]["driver"] == "code" and trace["learn"]["classification"] == "unclassified"
    text = h.store(loop).open_questions()[0]["text"]
    assert "could not classify" in text and "No such file" in text


def test_learn_does_not_call_the_llm_once_the_budget_is_spent(h):
    loop = _job(h)
    (loop / "config").mkdir()
    (loop / "config" / "loop.toml").write_text("[budget]\nllm_calls_per_window = 1\n")
    (loop / "source").unlink()
    h.behave({"learn": learn(classification="world")})
    h.run(loop)
    (loop / "source").write_text("v1\n")
    h.run(loop)
    (loop / "source").unlink()
    trace = h.run(loop)                                             # a new failure, budget already spent
    assert trace["cost"]["llm_calls"] == 0 and h.calls() == ["learn"]
    assert trace["learn"]["llm_error"] == "LLM budget for the window is spent"

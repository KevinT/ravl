"""Questions a loop asks its parent: when one is recorded, and how it is carried.

A loop may ask whether or not its outcome holds. The question is kept in the loop; a
command the owner configures under `[ask]` carries it, and `ravl answer` records the reply.
"""

import json
import sys

from conftest import ACT_WRITE, PRODUCE, act, learn
from ravl import cli

CARRIER = r"""
import json, os, sys
out = sys.argv[1]
payload = json.load(sys.stdin)
if os.path.exists(out + ".down"):
    sys.stderr.write("the messaging service is not reachable\n")
    sys.exit(4)
payload["env"] = {k: os.environ.get(k) for k in ("RAVL_LOOP_DIR", "RAVL_QUESTION_ID")}
with open(out, "a") as f:
    f.write(json.dumps(payload) + "\n")
"""


def asking(question, **over):
    behaviour = act(["echo ready > out.txt"], ["out.txt"])
    behaviour["report"]["ask"] = question
    behaviour["report"].update(over)
    return behaviour


def carrier(h):
    """Add an ask command to the test's settings; returns the file it appends questions to."""
    program, out = h.tmp / "carrier.py", h.tmp / "carried.jsonl"
    program.write_text(CARRIER)
    h.user_config.write_text(h.user_config.read_text()
                             + f'\n[ask]\ncommand = ["{sys.executable}", "{program}", "{out}"]\n')
    return out


def carried(out):
    return [json.loads(line) for line in out.read_text().splitlines()] if out.exists() else []


def test_a_loop_whose_outcome_holds_can_ask_and_the_question_waits_until_answered(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": asking("Which bed are the roses in?"), "learn": learn()})
    first = h.run(loop)
    assert first["verify"]["status"] == "pass" and first["learn"]["asked"] == ["q-001"]
    (question,) = h.store(loop).open_questions()
    assert question["text"] == "Which bed are the roses in?" and question["condition"].startswith("asked:")

    second = h.run(loop)                          # passes again, asks the same thing again
    assert second["learn"]["asked"] == [] and second["learn"]["not_asked"] == 1
    assert [q["id"] for q in h.store(loop).open_questions()] == ["q-001"]   # still open, not doubled
    assert "# Questions already waiting for the owner (do not ask these again)\n- Which bed are the roses in?" \
        in h.prompt("act")

    assert cli.main(["answer", str(loop), "q-001", "The", "north", "bed"]) == 0
    h.behave({"act": ACT_WRITE, "learn": learn()})
    h.run(loop)
    prompt = h.prompt("act")
    assert "- Which bed are the roses in? -> The north bed" in prompt
    assert "do not ask these again)\n(none)" in prompt and h.store(loop).open_questions() == []


def test_learn_may_ask_about_a_run_that_passed(h):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": ACT_WRITE, "learn": learn(question="Is weekly often enough?")})
    trace = h.run(loop)
    assert trace["verify"]["status"] == "pass" and trace["learn"]["question"] is None
    assert [q["text"] for q in h.store(loop).open_questions()] == ["Is weekly often enough?"]
    assert "# Questions already waiting for the owner" in h.prompt("learn")


def test_no_more_than_the_limit_wait_at_once_and_a_failure_is_still_put(h):
    loop = h.loop("produce", PRODUCE)
    (loop / "config").mkdir()
    (loop / "config" / "loop.toml").write_text("[ask]\nmax_open = 2\n")
    for number in (1, 2, 3):
        h.behave({"act": asking(f"Question number {number}?"), "learn": learn()})
        trace = h.run(loop)
    assert trace["learn"]["asked"] == [] and trace["learn"]["not_asked"] == 1
    assert [q["text"] for q in h.store(loop).open_questions()] == ["Question number 1?", "Question number 2?"]

    # A failing condition is always put to the parent, whatever is already waiting.
    h.behave({"act": act([], [], needs_owner="Sign in to the service again."),
              "learn": learn(classification="world", hold=True)})
    failed = h.run(loop)
    assert failed["verify"]["status"] == "fail" and failed["learn"]["question"] == "q-003"
    assert len(h.store(loop).open_questions()) == 3


def test_the_ask_command_is_given_each_question_once(h):
    loop = h.loop("produce", PRODUCE)
    out = carrier(h)
    h.behave({"act": asking("Which bed are the roses in?"), "learn": learn()})
    trace = h.run(loop)
    assert trace["ask"] == [{"id": "q-001", "sent": True, "error": None}]
    (sent,) = carried(out)
    assert sent["text"] == "Which bed are the roses in?" and sent["title"] == "Produce a file"
    assert sent["loop"] == str(loop) and sent["id"] == "q-001" and sent["run"] == trace["run_id"]
    assert sent["answer_with"] == ["ravl", "answer", str(loop), "q-001"]
    assert sent["env"] == {"RAVL_LOOP_DIR": str(loop), "RAVL_QUESTION_ID": "q-001"}
    assert h.store(loop).open_questions()[0]["delivered"]

    again = h.run(loop)                           # the question still waits; it is not sent twice
    assert "ask" not in again and len(carried(out)) == 1


def test_a_question_that_could_not_be_sent_is_kept_and_tried_again(h, capsys):
    loop = h.loop("produce", PRODUCE)
    out = carrier(h)
    down = h.tmp / "carried.jsonl.down"
    down.write_text("")
    h.behave({"act": asking("Which bed are the roses in?"), "learn": learn()})
    trace = h.run(loop)
    assert trace["verify"]["status"] == "pass"    # a failed delivery does not change the run
    assert trace["ask"][0]["sent"] is False and "not reachable" in trace["ask"][0]["error"]
    question = h.store(loop).open_questions()[0]
    assert not question.get("delivered") and "exited 4" in question["delivery_error"]

    calls = len(h.calls())
    assert cli.main(["ask", str(loop.parent), "--user-config", str(h.user_config)]) == 1
    assert "not sent: the ask command exited 4" in capsys.readouterr().out
    down.unlink()
    assert cli.main(["ask", str(loop.parent), "--list", "--user-config", str(h.user_config)]) == 0
    assert "last attempt failed" in capsys.readouterr().out and carried(out) == []   # --list sends nothing
    assert cli.main(["ask", str(loop.parent), "--user-config", str(h.user_config)]) == 0
    assert "produce  q-001  sent now" in capsys.readouterr().out and len(carried(out)) == 1
    assert cli.main(["ask", str(loop.parent), "--user-config", str(h.user_config)]) == 0
    assert "produce  q-001  sent 2" in capsys.readouterr().out and len(carried(out)) == 1
    assert len(h.calls()) == calls                # carrying a question makes no LLM call


def test_with_no_ask_command_questions_wait_in_the_loop(h, capsys):
    loop = h.loop("produce", PRODUCE)
    h.behave({"act": asking("Which bed are the roses in?"), "learn": learn()})
    assert "ask" not in h.run(loop)
    assert cli.main(["ask", str(loop), "--user-config", str(h.user_config)]) == 0
    out = capsys.readouterr().out
    assert "q-001  waiting: no ask command is configured" in out and "[ask]" in out
    assert cli.main(["ask", str(loop), "--json", "--user-config", str(h.user_config)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["text"] == "Which bed are the roses in?"
    assert cli.main(["answer", str(loop), "q-001", "north"]) == 0
    capsys.readouterr()
    assert cli.main(["ask", str(loop), "--user-config", str(h.user_config)]) == 0
    assert "no open questions" in capsys.readouterr().out


def test_an_answer_makes_an_llm_driven_loop_act_once_even_though_every_check_passes(h):
    from conftest import MAINTAIN
    loop = h.loop("maintain", MAINTAIN)
    behaviour = act(["touch flag"], ["flag"])
    behaviour["report"]["ask"] = "What colour should the flag be?"
    h.behave({"act": behaviour, "learn": learn()})
    assert h.run(loop)["act"]["driver"] == "llm"
    quiet = h.run(loop)                           # the outcome holds and nothing is new
    assert quiet["act"]["driver"] == "none" and quiet["cost"]["llm_calls"] == 0

    h.store(loop).answer("q-001", "Red")
    h.behave({"act": act(["echo red > flag"], ["flag"]), "learn": learn()})
    acted = h.run(loop)
    assert acted["reflect"]["world"]["status"] == "pass" and acted["act"]["driver"] == "llm"
    assert acted["act"]["answers_read"] == ["q-001"] and acted["verify"]["status"] == "pass"
    assert "# Answers given since the last Act (new: bring the work into line with them)\n" \
           "- What colour should the flag be? -> Red" in h.prompt("act")
    assert (loop / "flag").read_text().strip() == "red"

    after = h.run(loop)                           # the answer has been read; the loop is quiet again
    assert after["act"]["driver"] == "none" and after["cost"]["llm_calls"] == 0

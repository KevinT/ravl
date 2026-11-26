"""A specification with no criteria: the verifier is assumed from the intent, once.

It is written to verifier.md, used as written on later runs, edited by the loop's
parent, and never changed by the loop it judges.
"""

import json

from conftest import act, learn
from ravl import spec as specmod

BARE = """\
# Greeting

## Intent

`out.txt` holds the word ready. Never write anywhere else.
"""

DERIVED = json.dumps({
    "understood": "A file out.txt containing the word ready.",
    "assumptions": ["out.txt is in the loop directory"],
    "criteria": [
        {"text": "`out.txt` exists and holds the word ready.", "check": "grep -qx ready out.txt"},
        {"text": "Nothing else was written.", "check": None},
    ],
})
WRITE = act(["echo ready > out.txt"], ["out.txt"])


def test_criteria_are_derived_before_act_and_written_where_they_can_be_edited(h):
    loop = h.loop("greeting", BARE)
    h.behave({"derive": DERIVED, "act": WRITE, "learn": learn()})
    trace = h.run(loop)
    assert h.calls() == ["derive", "act", "learn"]
    text = (loop / "verifier.md").read_text()
    assert text.startswith("# Verifier (assumed)") and trace["run_id"] in text
    assert "A file out.txt containing the word ready." in text
    assert "1. out.txt is in the loop directory" in text
    assert "- `out.txt` exists and holds the word ready.\n  ```check\n  grep -qx ready out.txt\n  ```" in text
    assert (loop / "ravl.md").read_text() == BARE                      # the specification is untouched
    assert trace["verifier"] == {"derived": True, "file": "verifier.md", "source": "file",
                                 "criteria": 2, "with_check": 1}
    assert trace["reflect"]["world"]["status"] == "fail"               # judged before Act, by the new criteria
    assert trace["verify"]["status"] == "pass" and len(trace["verify"]["unchecked"]) == 1
    assert "grep -qx ready out.txt" in h.prompt("act")                 # Act is shown what it is judged by
    assert "You have no tools" in h.prompt("derive") and "Never write anywhere else." in h.prompt("derive")


def test_the_assumed_verifier_is_held_and_not_derived_again(h):
    loop = h.loop("greeting", BARE)
    h.behave({"derive": DERIVED, "act": WRITE, "learn": learn()})
    h.run(loop)
    first = (loop / "verifier.md").read_bytes()
    (loop / "out.txt").unlink()
    other = json.dumps({"criteria": [{"text": "Something else entirely.", "check": "true"}]})
    h.behave({"derive": other, "act": WRITE, "learn": learn()})
    second = h.run(loop)
    assert h.calls().count("derive") == 1
    assert (loop / "verifier.md").read_bytes() == first
    assert second["verifier"] == {"source": "file", "criteria": 2, "with_check": 1}


def test_the_parent_edits_the_file_and_the_next_run_uses_the_edit(h):
    loop = h.loop("greeting", BARE)
    h.behave({"derive": DERIVED, "act": WRITE, "learn": learn()})
    assert h.run(loop)["verify"]["status"] == "pass"
    path = loop / "verifier.md"
    path.write_text(path.read_text() + "- `out.txt` ends with a newline.\n  ```check\n  test \"$(tail -c1 out.txt | wc -l)\" -eq 1\n  ```\n"
                    "- `log.txt` records the run.\n  ```check\n  test -s log.txt\n  ```\n")
    trace = h.run(loop)
    assert trace["verifier"]["criteria"] == 4 and trace["verifier"]["with_check"] == 3
    failing = [c["text"] for c in trace["reflect"]["world"]["checks"] if c["status"] == "fail"]
    assert failing == ["`log.txt` records the run."]
    assert h.calls().count("derive") == 1


def test_the_loop_cannot_change_the_criteria_it_is_judged_by(h):
    loop = h.loop("greeting", BARE)
    weaken = act(["sed -i 's/grep -qx ready out.txt/true/' verifier.md"], [])
    h.behave({"derive": DERIVED, "act": weaken, "learn": learn(classification="solution")})
    trace = h.run(loop)
    assert trace["act"]["restored"] == ["verifier.md"]
    assert "grep -qx ready out.txt" in (loop / "verifier.md").read_text()
    assert trace["verify"]["status"] == "fail"                         # still judged by the original
    proposed = (loop / "runs" / trace["run_id"] / "verifier-proposed.md").read_text()
    assert "true" in proposed and "grep -qx ready" not in proposed
    assert "changed verifier.md; the change was undone" in h.store(loop).open_questions()[0]["text"]


def test_criteria_written_in_the_specification_take_precedence(h):
    loop = h.loop("greeting", BARE + "\n## Verifier\n\n- `out.txt` exists.\n  ```check\n  test -f out.txt\n  ```\n")
    (loop / "verifier.md").write_text("- Never read.\n  ```check\n  false\n  ```\n")
    h.behave({"derive": DERIVED, "act": WRITE, "learn": learn()})
    trace = h.run(loop)
    assert "derive" not in h.calls()
    assert trace["verifier"] == {"source": "specification", "criteria": 1, "with_check": 1}
    assert trace["verify"]["status"] == "pass"


def test_when_criteria_cannot_be_derived_nothing_is_written(h):
    loop = h.loop("no-llm", BARE)
    trace = h.run(loop, llm=False)
    assert not (loop / "verifier.md").exists()
    assert trace["verifier"]["derived"] is False and trace["verify"]["status"] == "no-verifier"
    assert "could not be derived from the intent (no LLM command is configured)" in \
        h.store(loop).open_questions()[0]["text"]

    for name, reply in (("empty", json.dumps({"criteria": []})), ("prose", "I am not sure what you want.")):
        loop = h.loop(name, BARE)
        h.behave({"derive": reply, "act": WRITE, "learn": learn()})
        trace = h.run(loop)
        assert not (loop / "verifier.md").exists() and trace["verifier"]["derived"] is False


def test_only_criteria_are_read_from_the_file(h):
    text = specmod.render_verifier("r1", "An outcome\nover two lines.", ["first", "second"],
                                   [{"text": "One  thing\nholds.", "check": "  test -f a\n  test -f b"},
                                    {"text": "Another.", "check": None}])
    loop = h.loop("parse", BARE)
    (loop / "verifier.md").write_text(text)
    criteria = specmod.load(loop).criteria
    assert [(c.text, c.check) for c in criteria] == [("One thing holds.", "test -f a\ntest -f b"), ("Another.", None)]

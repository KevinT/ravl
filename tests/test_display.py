"""The terminal display: what a run reports as it proceeds, and how it is drawn.

The display is drawn on a recording console, so these tests read the text a person
would see, without colour.
"""

import io
import json

from rich.console import Console

from conftest import act, learn
from ravl import cli, ui

LOOP = """\
# Greeting

## Intent

`out.txt` holds the word ready.

## Verifier

- `out.txt` exists.
  ```check
  test -f out.txt || { echo "out.txt is missing"; exit 1; }
  ```
- Somebody likes it.
"""


def _console():
    return Console(file=io.StringIO(), force_terminal=True, width=110, record=True, highlight=False)


def test_a_run_reports_each_phase_in_order_and_an_observer_cannot_break_it(h):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act(["echo ready > out.txt"], ["out.txt"]), "learn": learn()})
    seen = []
    trace = cli.runner.run(loop, h.user_config, lambda event, phase, data: seen.append((event, phase)))
    assert seen == [("start", ""), ("begin", "reflect"), ("end", "reflect"), ("begin", "act"), ("end", "act"),
                    ("begin", "verify"), ("end", "verify"), ("begin", "learn"), ("end", "learn"), ("finish", "")]

    def broken(event, phase, data):
        data.clear()                      # it is handed copies
        raise RuntimeError("display fault")

    (loop / "out.txt").unlink()
    again = cli.runner.run(loop, h.user_config, broken)
    assert again["verify"]["status"] == trace["verify"]["status"] == "pass"
    assert again["act"]["driver"] == "llm"


def test_deriving_a_verifier_is_reported_as_its_own_step(h):
    loop = h.loop("bare", "# Bare\n\n## Intent\n\nA file.\n")
    h.behave({"derive": json.dumps({"criteria": [{"text": "A file exists.", "check": "test -f a"}]}),
              "act": act(["touch a"], ["a"]), "learn": learn()})
    seen = []
    cli.runner.run(loop, h.user_config, lambda event, phase, data: seen.append((event, phase, data)))
    assert [(e, p) for e, p, _ in seen[:3]] == [("start", ""), ("begin", "derive"), ("end", "derive")]
    assert seen[2][2]["derived"] is True and seen[2][2]["criteria"] == 1


def test_a_passing_run_is_drawn_with_its_phases_criteria_and_cost(h):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act(["echo ready > out.txt"], ["out.txt"]), "learn": learn(steer="Keep writing the file.")})
    out = _console()
    cli.runner.run(loop, h.user_config, ui.RunDisplay(out, live=False))
    text = out.export_text()
    assert "ravl  Greeting" in text
    for line in ("R  Reflect", "A  Act", "V  Verify", "L  Learn"):
        assert line in text
    assert "0 of 2 criteria hold before Act" in text and "out.txt is missing" not in text   # no check output at Reflect
    assert "by llm" in text and "✓ out.txt" in text
    assert " PASS   1 of 2 criteria hold" in text and "✓ `out.txt` exists." in text
    assert "– (no check) Somebody likes it." in text
    assert "steer for the next run  Keep writing the file." in text
    assert "2 LLM calls" in text and "fake-1" in text


def test_a_failing_run_shows_the_check_output_the_classification_and_the_question(h):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act([], []), "learn": learn(classification="world", reason="the disk is read-only",
                                                 question="Make the directory writable.")})
    out = _console()
    cli.runner.run(loop, h.user_config, ui.RunDisplay(out, live=False))
    text = out.export_text()
    assert " FAIL   0 of 2 criteria hold" in text and "✗ `out.txt` exists." in text
    assert "out.txt is missing" in text                                 # what the failing check printed
    assert "world failure" in text and "the disk is read-only" in text
    assert "question for the loop's parent · q-001" in text and "Make the directory writable." in text
    assert 'ravl answer' in text and 'q-001 "…"' in text


def test_the_line_shown_while_a_phase_runs_carries_the_time_so_far():
    moments = iter([100.0, 163.0])
    out = _console()
    out.print(ui._Working("act", lambda: next(moments)))
    text = out.export_text()
    assert "A  Act" in text and "working  1m 03s" in text


def test_a_finished_run_can_be_drawn_again_from_its_trace(h):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act(["echo ready > out.txt"], ["out.txt"]), "learn": learn()})
    trace = h.run(loop)
    out = _console()
    ui.replay(out, trace, "Greeting", "", [])
    text = out.export_text()
    assert f"run {trace['run_id']}" in text and " PASS " in text and "by llm" in text


def test_list_show_and_config_are_drawn(h, tmp_path):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act([], []), "learn": learn(classification="world", question="Fix it.")})
    h.run(loop)
    out = _console()
    ui.listing(out, [cli.summary(loop)], loop.parent)
    ui.show(out, cli.summary(loop))
    ui.config(out, tmp_path / "none.toml", {}, [
        {"name": "claude", "title": "Claude Code", "program": "/bin/claude", "signin": ["~/.x"],
         "signin_hint": "claude auth login", "confines_act": "nothing", "proven": True, "note": ""},
        {"name": "codex", "title": "Codex CLI", "program": None, "signin": None,
         "signin_hint": "codex login", "confines_act": "its own sandbox", "proven": False, "note": "unproven"}],
        "notice text")
    text = out.export_text()
    assert " FAIL " in text and "greeting" in text and "1 question(s)" in text
    assert "2 criteria, 1 with a check  ·  written in ravl.md" in text and "✗ `out.txt` exists." in text
    assert "not configured" in text and "✓ on PATH" in text and "✗ not on PATH" in text
    assert "no sign-in found, to sign in: codex login" in text and "notice text" in text


def test_output_that_is_not_a_terminal_stays_plain(h, capsys):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act(["echo ready > out.txt"], ["out.txt"]), "learn": learn()})
    assert cli.main(["run", str(loop), "--user-config", str(h.user_config)]) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("loop     ") and "verify   PASS" in printed and "\x1b[" not in printed


def test_a_claimed_effect_may_be_a_path_followed_by_a_note(h):
    loop = h.loop("greeting", LOOP)
    h.behave({"act": act(["mkdir -p out && echo ready > out/a.txt && echo ready > out.txt"],
                         ["out/ (1 file, out/a.txt)", "out.txt", "nowhere.txt (scratch)"]), "learn": learn()})
    effects = {e["claim"]: e["confirmed"] for e in h.run(loop)["act"]["effects"]}
    assert effects == {"out/ (1 file, out/a.txt)": True, "out.txt": True, "nowhere.txt (scratch)": False}

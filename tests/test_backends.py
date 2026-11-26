"""Backends shipped in the package, and `ravl config`.

The agent programs are stand-ins: small scripts placed on PATH that record how they
were started and reply in the real program's output format.
"""

import json
import os
import subprocess
import sys
import tomllib

import pytest

from ravl import backends, cli, config

CLAUDE = """#!/usr/bin/env python3
import json, sys
json.dump({"argv": sys.argv[1:], "stdin": sys.stdin.read()}, open("claude-call.json", "w"))
print(json.dumps({"result": "done", "total_cost_usd": 0.02, "is_error": False,
                  "modelUsage": {"m-1": {"inputTokens": 10, "cacheReadInputTokens": 5, "outputTokens": 3}}}))
"""

CODEX = """#!/usr/bin/env python3
import json, sys
argv = sys.argv[1:]
json.dump({"argv": argv, "stdin": sys.stdin.read()}, open("codex-call.json", "w"))
open(argv[argv.index("--output-last-message") + 1], "w").write("codex reply")
print(json.dumps({"type": "thread.started"}))
print("a log line that is not JSON")
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7, "output_tokens": 2}}))
"""


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A home directory and a PATH that hold only what a test puts there."""
    home, bin_dir, work = tmp_path / "home", tmp_path / "bin", tmp_path / "work"
    for directory in (home, bin_dir, work):
        directory.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(config, "USER_CONFIG", home / ".config" / "ravl" / "config.toml")
    monkeypatch.chdir(work)

    def install(name: str, script: str) -> None:
        path = bin_dir / name
        path.write_text(script.replace("#!/usr/bin/env python3", f"#!{sys.executable}"))
        path.chmod(0o755)

    return type("Machine", (), {"home": home, "work": work, "install": staticmethod(install)})


def _adapter(name, phase, *extra, prompt="the prompt"):
    return subprocess.run([sys.executable, "-m", "ravl.backends", name, *extra], input=prompt,
                          capture_output=True, text=True, env={**os.environ, "RAVL_PHASE": phase})


def test_a_backend_name_resolves_to_the_adapter_command_and_a_command_takes_precedence():
    run = [sys.executable, "-m", "ravl.backends"]
    assert config.llm_command({"llm": {"backend": "claude"}}, "act") == [*run, "claude"]
    cfg = {"llm": {"backend": "claude", "model": "big", "learn": {"model": "small"}, "derive": {"backend": "codex"}}}
    assert config.llm_command(cfg, "act") == [*run, "claude", "--model", "big"]
    assert config.llm_command(cfg, "learn") == [*run, "claude", "--model", "small"]
    assert config.llm_command(cfg, "derive") == [*run, "codex", "--model", "big"]
    assert config.llm_command({"llm": {"backend": "claude", "command": ["mine"]}}, "act") == ["mine"]
    assert config.llm_command({"llm": {}}, "act") is None


def test_looking_for_a_program_starts_nothing(machine):
    machine.install("claude", "#!/usr/bin/env python3\nopen('started', 'w')\n")
    seen = {row["name"]: row for row in backends.look_all()}
    assert seen["claude"]["program"].endswith("/bin/claude") and seen["claude"]["signin"] is None
    assert seen["codex"]["program"] is None
    assert not (machine.work / "started").exists()

    (machine.home / ".claude").mkdir()
    (machine.home / ".claude" / ".credentials.json").write_text("{}")
    os.environ["ANTHROPIC_API_KEY"] = "not-a-real-key"
    try:
        signin = backends.look(backends.BACKENDS["claude"])["signin"]
    finally:
        del os.environ["ANTHROPIC_API_KEY"]
    assert signin == ["~/.claude/.credentials.json", "$ANTHROPIC_API_KEY"]   # names only, never a value


def test_claude_gets_tools_only_in_act(machine):
    machine.install("claude", CLAUDE)
    done = _adapter("claude", "act", "--model", "big")
    assert done.returncode == 0
    envelope = json.loads(done.stdout)
    assert envelope["text"] == "done"
    assert envelope["usage"] == {"model": "m-1", "input_tokens": 15, "output_tokens": 3, "cost_usd": 0.02}
    call = json.loads((machine.work / "claude-call.json").read_text())
    assert call["stdin"] == "the prompt" and call["argv"][:1] == ["-p"]
    assert call["argv"][-4:] == ["--model", "big", "--permission-mode", "bypassPermissions"]

    _adapter("claude", "learn")
    argv = json.loads((machine.work / "claude-call.json").read_text())["argv"]
    assert argv[-2:] == ["--tools", ""] and "bypassPermissions" not in argv and "--model" not in argv


def test_codex_is_confined_to_the_loop_directory_in_act_and_read_only_otherwise(machine):
    machine.install("codex", CODEX)
    done = _adapter("codex", "act")
    assert done.returncode == 0
    envelope = json.loads(done.stdout)
    assert envelope["text"] == "codex reply"
    assert (envelope["usage"]["input_tokens"], envelope["usage"]["output_tokens"]) == (7, 2)
    call = json.loads((machine.work / "codex-call.json").read_text())
    assert call["stdin"] == "the prompt" and call["argv"][0] == "exec" and call["argv"][-1] == "-"
    assert call["argv"][call["argv"].index("--sandbox") + 1] == "workspace-write"

    _adapter("codex", "derive", "--model", "m")
    argv = json.loads((machine.work / "codex-call.json").read_text())["argv"]
    assert argv[argv.index("--sandbox") + 1] == "read-only" and argv[argv.index("--model") + 1] == "m"


def test_a_missing_program_and_an_unknown_name_are_reported(machine):
    missing = _adapter("claude", "act")
    assert missing.returncode == 127 and "was not found" in missing.stderr
    unknown = _adapter("nothing", "act")
    assert unknown.returncode == 2 and "known: claude, codex" in unknown.stderr


def test_a_program_that_fails_is_a_failed_call(machine):
    machine.install("codex", "#!/usr/bin/env python3\nimport json, sys\n"
                    "print(json.dumps({'type': 'error', 'message': '401 Unauthorized'}))\nsys.exit(1)\n")
    failed = _adapter("codex", "act")
    assert failed.returncode == 1 and "401 Unauthorized" in failed.stderr


def test_config_set_writes_the_choice_and_keeps_other_settings(machine, capsys):
    path = config.USER_CONFIG
    path.parent.mkdir(parents=True)
    path.write_text('[llm]\ncommand = ["old", "adapter"]\ntimeout_s = 300\n\n[llm.learn]\nmodel = "small"\n\n'
                    '[budget]\nllm_calls_per_window = 4\n')
    machine.install("claude", CLAUDE)
    assert cli.main(["config", "set", "claude", "--model", "big"]) == 0
    out = capsys.readouterr().out
    assert "backend claude, model big" in out and "no sign-in was found" in out and "does not confine a run yet" in out
    assert tomllib.loads(path.read_text()) == {
        "llm": {"backend": "claude", "model": "big", "timeout_s": 300, "learn": {"model": "small"}},
        "budget": {"llm_calls_per_window": 4}}

    assert cli.main(["config", "set", "codex"]) == 0                # no model: the earlier one is dropped
    out = capsys.readouterr().out
    assert "`codex` is not on PATH" in out and "not yet run against a signed-in Codex" in out
    assert tomllib.loads(path.read_text())["llm"] == {"backend": "codex", "timeout_s": 300, "learn": {"model": "small"}}
    assert cli.main(["config", "set", "nothing"]) == 2


def test_config_shows_what_is_set_and_what_was_found_and_chooses_nothing_itself(machine, capsys):
    machine.install("claude", CLAUDE)
    assert cli.main(["config"]) == 0                                # not a terminal: no question is asked
    out = capsys.readouterr().out
    assert "not written yet" in out and "not configured" in out
    assert "1. claude" in out and "on PATH" in out and "to sign in: claude auth login" in out
    assert "2. codex" in out and "not on PATH" in out
    assert not config.USER_CONFIG.exists()
    assert not (machine.work / "claude-call.json").exists()         # showing started no program


def test_a_loop_runs_through_a_backend_chosen_with_config(machine, h, capsys):
    machine.install("claude", CLAUDE)
    cli.main(["config", "set", "claude"])
    loop = h.loop("job", "# Job\n\n## Intent\n\nx\n\n## Verifier\n\n- A file exists.\n  ```check\n  test -f made\n  ```\n")
    trace = cli.runner.run(loop)                                     # the user file chosen above is read
    assert trace["act"]["driver"] == "llm" and trace["act"]["ok"] is True
    assert trace["cost"]["tokens"] == {"m-1": {"input": 30, "output": 6}}   # Act and Learn, 15 and 3 each
    assert (loop / "claude-call.json").exists()                      # the program ran in the loop directory


def test_an_unconfigured_run_says_how_to_configure(machine, h, capsys):
    loop = h.loop("bare", "# Bare\n\n## Intent\n\nx\n")
    assert cli.main(["run", str(loop)]) == 1
    assert "to configure one: ravl config" in capsys.readouterr().out


def test_config_set_with_a_folder_writes_that_folders_file_and_shows_what_is_in_effect(machine, capsys):
    machine.install("claude", CLAUDE)
    folder = machine.work / "loops"
    (folder / "deep" / "er").mkdir(parents=True)
    assert cli.main(["config", "set", "--model", "small", "--dir", str(folder)]) == 2   # no agent program yet
    assert "none is chosen yet" in capsys.readouterr().err and not (folder / "ravl.toml").exists()

    cli.main(["config", "set", "claude", "--model", "big"])
    capsys.readouterr()
    assert cli.main(["config", "set", "--model", "small", "--dir", str(folder)]) == 0
    out = capsys.readouterr().out
    assert f"wrote {folder / 'ravl.toml'}: model small" in out and "every phase  claude, model small" in out
    assert tomllib.loads((folder / "ravl.toml").read_text()) == {"llm": {"model": "small"}}
    assert tomllib.loads(config.USER_CONFIG.read_text())["llm"] == {"backend": "claude", "model": "big"}

    (folder / "ravl.toml").write_text('[llm]\nmodel = "small"\n\n[llm.act]\nmodel = "large"\n\n[read]\nradius = 2\n')
    assert cli.main(["config", "set", "--model", "tiny", "--dir", str(folder / "deep")]) == 0
    capsys.readouterr()
    assert tomllib.loads((folder / "ravl.toml").read_text())["read"] == {"radius": 2}   # the file above is untouched
    assert cli.main(["config", "--dir", str(folder / "deep" / "er")]) == 0
    out = capsys.readouterr().out
    assert f"folder   {folder / 'ravl.toml'}  model small; act: model large" in out
    assert f"folder   {folder / 'deep' / 'ravl.toml'}  model tiny" in out
    assert "derive       claude, model tiny" in out and "act          claude, model large" in out
    assert cli.main(["config", "set", "--dir", str(folder)]) == 2                       # nothing to set
    assert cli.main(["config", "set", "--model", "x", "--dir", str(folder / "absent")]) == 2


def test_a_model_alone_changes_the_machine_model_and_keeps_the_agent_program(machine, capsys):
    machine.install("claude", CLAUDE)
    assert cli.main(["config", "set", "--model", "small"]) == 2                         # no agent program yet
    cli.main(["config", "set", "claude"])
    assert "no model set: the program uses its own default" not in capsys.readouterr().out
    assert cli.main(["config"]) == 0
    assert "every phase  claude, no model set: the program uses its own default" in capsys.readouterr().out
    assert cli.main(["config", "set", "--model", "small"]) == 0
    assert tomllib.loads(config.USER_CONFIG.read_text())["llm"] == {"backend": "claude", "model": "small"}
    config.USER_CONFIG.write_text('[llm]\ncommand = ["mine"]\n')
    assert cli.main(["config", "set", "--model", "small"]) == 2
    assert "name a command instead" in capsys.readouterr().err


def test_asked_on_a_terminal_config_takes_the_program_and_the_model_together(machine, capsys, monkeypatch):
    machine.install("claude", CLAUDE)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)

    def answers(*replies):
        queue = list(replies)
        monkeypatch.setattr("builtins.input", lambda prompt="": queue.pop(0))

    answers("1", "")                                   # a program, then no model
    assert cli.main(["config"]) == 0
    out = capsys.readouterr().out
    assert "Model for Claude Code" in out and "the program's own default" in out
    assert "no model was chosen; nothing was changed" in out and not config.USER_CONFIG.exists()

    answers("1", "2")                                  # the second offered model
    assert cli.main(["config"]) == 0
    assert tomllib.loads(config.USER_CONFIG.read_text())["llm"] == {
        "backend": "claude", "model": backends.BACKENDS["claude"].models[1]}

    config.USER_CONFIG.unlink()
    answers("1", "d")                                  # the program's own default, chosen by name
    assert cli.main(["config"]) == 0
    assert tomllib.loads(config.USER_CONFIG.read_text())["llm"] == {"backend": "claude"}
    assert "the program's default model" in capsys.readouterr().out

    config.USER_CONFIG.unlink()
    answers("1", "some-other-model")
    assert cli.main(["config"]) == 0
    assert tomllib.loads(config.USER_CONFIG.read_text())["llm"]["model"] == "some-other-model"

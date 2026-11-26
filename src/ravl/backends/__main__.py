"""Run one backend: `python -m ravl.backends <name> [--model MODEL]`.

Reads the prompt on standard input and writes ravl's envelope on standard output:

    {"text": "...", "usage": {"model": ..., "input_tokens": ..., "output_tokens": ..., "cost_usd": ...}}

In the Act phase the agent program is started with tools and with its approval prompts
off, because nobody is present to answer them. In every other phase it produces text
and is given no tools, or a read-only sandbox.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import BACKENDS


def _emit(text: str, usage: dict) -> None:
    print(json.dumps({"text": text, "usage": usage}))


def claude(program: str, prompt: str, phase: str, model: str | None) -> int:
    command = [program, "-p", "--output-format", "json", "--no-session-persistence"]
    command += ["--model", model] if model else []
    command += ["--permission-mode", "bypassPermissions"] if phase == "act" else ["--tools", ""]
    proc = subprocess.run(command, input=prompt, capture_output=True, text=True)
    try:
        reply = json.loads(proc.stdout)
    except json.JSONDecodeError:
        sys.stderr.write((proc.stderr or proc.stdout)[-2000:])
        return proc.returncode or 1
    usage = {"model": "unknown", "input_tokens": 0, "output_tokens": 0,
             "cost_usd": reply.get("total_cost_usd", 0)}
    models = reply.get("modelUsage") or {}
    if models:
        usage["model"] = "+".join(sorted(models))
        for figures in models.values():
            usage["input_tokens"] += (figures.get("inputTokens", 0) + figures.get("cacheReadInputTokens", 0)
                                      + figures.get("cacheCreationInputTokens", 0))
            usage["output_tokens"] += figures.get("outputTokens", 0)
    _emit(reply.get("result") or "", usage)
    if reply.get("is_error") or proc.returncode != 0:
        sys.stderr.write(f"claude: {reply.get('subtype')} {reply.get('api_error_status') or ''}\n")
        return proc.returncode or 1
    return 0


def codex(program: str, prompt: str, phase: str, model: str | None) -> int:
    with tempfile.TemporaryDirectory() as scratch:
        last = Path(scratch) / "last-message.txt"
        command = [program, "exec", "--json", "--skip-git-repo-check", "--ephemeral",
                   "--color", "never", "--output-last-message", str(last)]
        command += ["--model", model] if model else []
        if phase == "act":
            # Codex's own sandbox: writes inside the working directory, network allowed.
            command += ["--sandbox", "workspace-write", "-c", "sandbox_workspace_write.network_access=true"]
        else:
            command += ["--sandbox", "read-only"]
        command.append("-")   # the prompt is read from standard input
        proc = subprocess.run(command, input=prompt, capture_output=True, text=True)
        text = last.read_text() if last.is_file() else ""
    usage = {"model": model or "codex default", "input_tokens": 0, "output_tokens": 0}
    error = ""
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "error":
            error = str(event.get("message") or "")
        figures = event.get("usage") if event.get("type") == "turn.completed" else None
        if isinstance(figures, dict):
            usage["input_tokens"] += int(figures.get("input_tokens") or 0)
            usage["output_tokens"] += int(figures.get("output_tokens") or 0)
    _emit(text, usage)
    if proc.returncode != 0 or not text.strip():
        sys.stderr.write(f"codex: {error or proc.stderr.strip()[-600:] or 'no reply'}\n")
        return proc.returncode or 1
    return 0


RUN = {"claude": claude, "codex": codex}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ravl.backends")
    parser.add_argument("name")
    parser.add_argument("--model")
    args = parser.parse_args(argv)
    backend = BACKENDS.get(args.name)
    if backend is None:
        sys.stderr.write(f"ravl: no backend named {args.name!r}; known: {', '.join(BACKENDS)}. "
                         "See `ravl config`.\n")
        return 2
    program = shutil.which(backend.program)
    if program is None:
        sys.stderr.write(f"ravl: backend {backend.name!r} needs the program `{backend.program}` "
                         "on PATH, and it was not found.\n")
        return 127
    return RUN[backend.name](program, sys.stdin.read(), os.environ.get("RAVL_PHASE", "act"), args.model)


if __name__ == "__main__":
    sys.exit(main())

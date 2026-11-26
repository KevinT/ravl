"""Call the LLM: a command that reads a prompt on stdin and writes a response on stdout.

The library has no knowledge of which model or agent runtime the command is. The
response is either plain text, or one JSON object (the envelope) with:

    {"text": "...", "usage": {"model": "...", "input_tokens": 0, "output_tokens": 0,
                              "cost_usd": 0.0}}

`usage` is optional and feeds the cost ledger. A command that performs Act is
expected to be an agent that can read and change files and run commands itself,
because Act is where the work is done.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LLMResult:
    ok: bool
    text: str = ""
    error: str | None = None
    usage: dict = field(default_factory=dict)
    wall_s: float = 0.0


def call(command: list[str], prompt: str, cwd: Path, env: dict, timeout_s: int) -> LLMResult:
    started = time.time()
    try:
        proc = subprocess.run(command, input=prompt, capture_output=True, text=True,
                              cwd=cwd, env={**os.environ, **env}, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return LLMResult(False, error=f"timed out after {timeout_s}s", wall_s=time.time() - started)
    except OSError as exc:
        return LLMResult(False, error=f"could not start {command[0]!r}: {exc}",
                         wall_s=time.time() - started)
    wall = time.time() - started
    out = proc.stdout.strip()
    text, usage = out, {}
    if out.startswith("{"):
        try:
            envelope = json.loads(out)
            if isinstance(envelope, dict) and isinstance(envelope.get("text"), str):
                text = envelope["text"]
                usage = envelope.get("usage") or {}
        except json.JSONDecodeError:
            pass
    if proc.returncode != 0:
        detail = (proc.stderr.strip() or out)[-600:]
        return LLMResult(False, text=text, error=f"exit {proc.returncode}: {detail}",
                         usage=usage, wall_s=wall)
    if not text:
        return LLMResult(False, error="empty response", usage=usage, wall_s=wall)
    return LLMResult(True, text=text, usage=usage, wall_s=wall)


def last_json(text: str) -> dict | None:
    """The last JSON object in a response: a fenced `json` block, else a bare object."""
    blocks = re.findall(r"```(?:json)?\s*\n(\{.*?\})\s*\n```", text, flags=re.S)
    candidates = list(reversed(blocks))
    stripped = text.strip()
    if stripped.startswith("{"):
        candidates.append(stripped)
    start = text.rfind("\n{")
    if start != -1:
        candidates.append(text[start + 1:].strip())
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None

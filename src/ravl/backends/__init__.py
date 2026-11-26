"""Backends: adapters between ravl's LLM contract and agent programs people already have.

The core does not import this package. A backend named in configuration is run as a
separate process, `python -m ravl.backends <name>`, with the prompt on standard input
and the phase in RAVL_PHASE. This file holds the registry, which is data, and the
lookup `ravl config` uses to show what is on the machine. That lookup starts no program
and reads no credential: it looks at PATH and at whether a sign-in file exists.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Backend:
    name: str            # the value of `[llm] backend`
    title: str
    program: str         # the executable looked for on PATH
    signin_files: tuple[str, ...]   # relative to the home directory; any one present counts
    signin_env: tuple[str, ...]     # environment variables the program accepts as a credential
    signin_hint: str     # what the owner runs to sign in
    confines_act: str    # a clause: what the program itself limits during Act
    proven: bool         # an end-to-end run with a signed-in program has been observed
    note: str = ""
    models: tuple[str, ...] = ()    # names the program accepts, offered by `ravl config`; not checked


BACKENDS: dict[str, Backend] = {b.name: b for b in (
    Backend(
        name="claude", title="Claude Code", program="claude",
        signin_files=(".claude/.credentials.json",), signin_env=("ANTHROPIC_API_KEY",),
        signin_hint="claude auth login",
        confines_act="the program confines nothing; Act can change whatever the user can",
        proven=True, models=("fable", "opus", "sonnet", "haiku")),
    Backend(
        name="codex", title="Codex CLI", program="codex",
        signin_files=(".codex/auth.json",), signin_env=(),
        signin_hint="codex login",
        confines_act="the program limits writes to the loop directory and the temporary directory",
        proven=False,
        note="written from the program's help text; not yet run against a signed-in Codex"),
)}


def look(backend: Backend) -> dict:
    """What can be seen of one backend without starting it."""
    home = Path.home()
    files = [name for name in backend.signin_files if (home / name).exists()]
    env = [name for name in backend.signin_env if os.environ.get(name)]
    return {"name": backend.name, "title": backend.title,
            "program": shutil.which(backend.program),
            "signin": ([f"~/{name}" for name in files] + [f"${name}" for name in env]) or None,
            "signin_hint": backend.signin_hint, "confines_act": backend.confines_act,
            "proven": backend.proven, "note": backend.note, "models": list(backend.models)}


def look_all() -> list[dict]:
    return [look(backend) for backend in BACKENDS.values()]

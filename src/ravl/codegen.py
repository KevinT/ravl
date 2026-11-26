"""Generated code for Act: validate it before it runs, then run it.

A generated program is a single Python file with PEP 723 inline metadata. Before
it is accepted it must parse, declare only whitelisted dependencies, and violate
no recorded execution constraint. A program that fails any of these is rejected
and never run; the rejection is a library result, not a model failure.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

OUTPUT_LIMIT = 4000

PEP723 = re.compile(r"(?m)^# /// script\s*$\n(?P<body>(?:^#.*$\n)*?)^# ///\s*$")


def extract_program(text: str) -> str | None:
    blocks = re.findall(r"```(?:python|py)\s*\n(.*?)\n```", text, flags=re.S)
    return blocks[-1].strip() + "\n" if blocks else None


def dependencies(program: str) -> list[str] | None:
    """Declared dependencies, or None when the PEP 723 block is absent or unreadable."""
    match = PEP723.search(program)
    if not match:
        return None
    body = "\n".join(line[2:] if line.startswith("# ") else line[1:]
                     for line in match.group("body").splitlines())
    try:
        meta = tomllib.loads(body)
    except tomllib.TOMLDecodeError:
        return None
    return [str(d) for d in meta.get("dependencies", [])]


def _name(requirement: str) -> str:
    return re.match(r"^[A-Za-z0-9._-]+", requirement.strip()).group(0).lower().replace("_", "-")


def validate(program: str, whitelist: list[str], constraints: list[dict]) -> list[str]:
    """Reasons the program is rejected. Empty means accepted."""
    problems = []
    try:
        ast.parse(program)
    except SyntaxError as exc:
        return [f"does not parse: {exc.msg} (line {exc.lineno})"]
    deps = dependencies(program)
    if deps is None:
        problems.append("no readable PEP 723 `# /// script` block")
    else:
        allowed = {_name(w) for w in whitelist}
        for dep in deps:
            if _name(dep) not in allowed:
                problems.append(f"dependency {dep!r} is not on the whitelist")
    for constraint in constraints:
        pattern = constraint.get("forbid")
        if not pattern:
            continue
        try:
            if re.search(pattern, program, flags=re.M):
                problems.append(f"violates execution constraint: {constraint.get('text', pattern)}")
        except re.error:
            continue
    return problems


def run_owner(script: str, loop_dir: Path, env: dict, timeout_s: int) -> dict:
    """Run the implementation the owner wrote in the specification's `act` block."""
    shell = shutil.which("bash") or "/bin/sh"
    started = time.time()
    try:
        proc = subprocess.run([shell, "-c", script], capture_output=True, text=True, cwd=loop_dir,
                              env={**os.environ, **env}, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        partial = ((exc.stdout or b"") + (exc.stderr or b""))
        partial = partial.decode("utf-8", "replace") if isinstance(partial, bytes) else str(partial)
        return {"ok": False, "exit": None, "error": f"timed out after {timeout_s}s",
                "output": partial[-OUTPUT_LIMIT:], "wall_s": round(time.time() - started, 2)}
    output = (proc.stdout + proc.stderr).strip()
    return {"ok": proc.returncode == 0, "exit": proc.returncode,
            "error": None if proc.returncode == 0 else f"exit {proc.returncode}",
            "output": output[-OUTPUT_LIMIT:], "wall_s": round(time.time() - started, 2)}


def run(program_path: Path, loop_dir: Path, env: dict, timeout_s: int) -> dict:
    """Run accepted code. The last stdout line may be a JSON report with `effects`."""
    deps = dependencies(program_path.read_text()) or []
    if deps:
        uv = shutil.which("uv")
        if not uv:
            return {"ok": False, "error": "generated code declares dependencies and `uv` is not on PATH"}
        command = [uv, "run", "--script", str(program_path)]
    else:
        command = [sys.executable, str(program_path)]
    started = time.time()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, cwd=loop_dir,
                              env={**os.environ, **env}, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {timeout_s}s"}
    report = {}
    lines = [line for line in proc.stdout.strip().splitlines() if line.strip()]
    if lines and lines[-1].lstrip().startswith("{"):
        try:
            report = json.loads(lines[-1])
        except json.JSONDecodeError:
            report = {}
    return {
        "ok": proc.returncode == 0,
        "exit": proc.returncode,
        "error": None if proc.returncode == 0 else (proc.stderr.strip() or proc.stdout.strip())[-800:],
        "claims": [str(e) for e in report.get("effects", [])] if isinstance(report, dict) else [],
        "summary": report.get("summary", "") if isinstance(report, dict) else "",
        "wall_s": round(time.time() - started, 2),
    }

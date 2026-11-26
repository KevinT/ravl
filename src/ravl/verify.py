"""The verification harness: run each criterion's check and report the result.

A check is a shell script run from the loop directory. Exit status 0 passes the
criterion; any other status, or a timeout, fails it. The check's output is kept as
evidence: it is what Act is shown when the criterion fails. No LLM is involved, so
the state of the outcome can be read when no LLM is reachable.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path

from .spec import Spec

OUTPUT_LIMIT = 2000


def _shell() -> list[str]:
    return [shutil.which("bash") or "/bin/sh", "-c"]


def run_checks(spec: Spec, loop_dir: Path, env: dict, timeout_s: int) -> list[dict]:
    results = []
    for criterion in spec.criteria:
        record = {"id": criterion.id, "text": criterion.text}
        if not criterion.check:
            results.append({**record, "status": "unchecked"})
            continue
        started = time.time()
        try:
            proc = subprocess.run([*_shell(), criterion.check], capture_output=True, text=True,
                                  cwd=loop_dir, env={**os.environ, **env}, timeout=timeout_s)
            status = "pass" if proc.returncode == 0 else "fail"
            output = (proc.stdout + proc.stderr).strip()
            record["exit"] = proc.returncode
        except subprocess.TimeoutExpired:
            status, output = "fail", f"check timed out after {timeout_s}s"
            record["exit"] = None
        results.append({**record, "status": status, "output": output[-OUTPUT_LIMIT:],
                        "wall_s": round(time.time() - started, 2)})
    return results


def summarize(results: list[dict]) -> dict:
    failing = [r["id"] for r in results if r["status"] == "fail"]
    unchecked = [r["id"] for r in results if r["status"] == "unchecked"]
    checked = [r for r in results if r["status"] in ("pass", "fail")]
    if not checked:
        status = "no-verifier"
    elif failing:
        status = "fail"
    else:
        status = "pass"
    return {"status": status, "failing": failing, "unchecked": unchecked,
            "fingerprint": fingerprint(failing)}


def fingerprint(failing: list[str]) -> str | None:
    """Identity of a failing condition: the set of failing criteria, not their output."""
    if not failing:
        return None
    return hashlib.sha1("|".join(sorted(failing)).encode()).hexdigest()[:10]

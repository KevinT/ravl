"""Configuration, resolved from three files, later overriding earlier.

1. User file (`~/.config/ravl/config.toml`): the LLM backend or command, set once per
   host, by hand or with `ravl config`.
2. `ravl.toml` at the root of a tree of loops: settings for the whole tree.
3. `config/` in the loop directory: the owner's settings for that loop.

No environment variable is read. The core names no environment: the LLM is a
command the owner supplies, and resources are entries the owner lists.
"""

from __future__ import annotations

import copy
import json
import sys
import tomllib
from pathlib import Path

from . import __version__

USER_CONFIG = Path.home() / ".config" / "ravl" / "config.toml"
TREE_FILE = "ravl.toml"
MODES = ("lock", "never-lock", "learned")

DEFAULTS: dict = {
    # `command` is the argv of a program that reads a prompt on stdin and writes the
    # response on stdout. `backend` names an adapter shipped with ravl, which is run the
    # same way; `model` is passed to it. A command takes precedence over a backend.
    # `llm.act`, `llm.learn`, `llm.codegen` and `llm.derive` may each override these.
    "llm": {"command": None, "backend": None, "model": None, "timeout_s": 900},
    "run": {"check_timeout_s": 120, "code_timeout_s": 600, "keep_runs": 200},
    "learn": {
        "promote_after": 3,      # consecutive LLM-driven passes before code is generated
        "hold_hours": 24,        # how long a hold written by Learn stays in force
        "never_lock_after": 3,   # declined code generations before proposing never-lock
        "max_repair_attempts": 2,  # failed LLM-driven attempts on one condition before the owner is asked
        "escalate_hours": 24,    # a failure with no question after this long is put to the owner
    },
    "budget": {"llm_calls_per_window": 12, "window_hours": 24},
    "read": {"radius": 1},
    "codegen": {"whitelist": []},
    "children": {"editable": True},
    "resources": {},
}


class ConfigError(Exception):
    pass


def _merge(base: dict, over: dict) -> dict:
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def _read(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def tree_root(loop_dir: Path) -> Path | None:
    """Nearest directory at or above the loop that holds `ravl.toml`."""
    for directory in [loop_dir, *loop_dir.parents]:
        if (directory / TREE_FILE).is_file():
            return directory
    return None


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split(".") if p.isdigit())


def load(loop_dir: Path, user_config: Path | None = None) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    user = user_config or USER_CONFIG
    if user.is_file():
        _merge(cfg, _read(user))
    root = tree_root(loop_dir)
    if root is not None:
        tree = _read(root / TREE_FILE)
        minimum = tree.pop("min_version", None)
        if minimum and _version_tuple(minimum) > _version_tuple(__version__):
            raise ConfigError(
                f"{root / TREE_FILE} requires ravl >= {minimum}; this is {__version__}. "
                "Upgrade with: uv tool upgrade ravl")
        _merge(cfg, tree)
    loop_file = loop_dir / "config" / "loop.toml"
    if loop_file.is_file():
        _merge(cfg, _read(loop_file))
    cfg["tree_root"] = str(root) if root else None
    cfg["mode"] = owner_mode(loop_dir)
    return cfg


def owner_mode(loop_dir: Path) -> str:
    path = loop_dir / "config" / "mode"
    value = path.read_text().strip() if path.is_file() else "learned"
    if value not in MODES:
        raise ConfigError(f"{path}: expected one of {', '.join(MODES)}, found {value!r}")
    return value


def set_owner_mode(loop_dir: Path, value: str) -> None:
    if value not in MODES:
        raise ConfigError(f"mode must be one of {', '.join(MODES)}")
    (loop_dir / "config").mkdir(exist_ok=True)
    (loop_dir / "config" / "mode").write_text(value + "\n")


def llm_command(cfg: dict, phase: str) -> list[str] | None:
    llm = cfg.get("llm", {})
    specific = llm.get(phase, {}) if isinstance(llm.get(phase), dict) else {}
    command = specific.get("command") or llm.get("command")
    if command:
        return list(command)
    backend = specific.get("backend") or llm.get("backend")
    if not backend:
        return None
    # The name is handed on unread: which agent programs exist is known to the
    # adapter process, not here.
    model = specific.get("model") or llm.get("model")
    return [sys.executable, "-m", "ravl.backends", str(backend)] + (["--model", str(model)] if model else [])


def _toml(data: dict, prefix: str = "") -> list[str]:
    """Enough TOML to write the settings this library reads: scalars, lists, tables."""
    lines, tables = [], []
    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        elif value is not None:
            rendered = ("true" if value else "false") if isinstance(value, bool) else json.dumps(value)
            lines.append(f"{key} = {rendered}")
    for key, value in tables:
        name = f"{prefix}{key}"
        lines += ["", f"[{name}]", *_toml(value, name + ".")]
    return lines


def choose_backend(name: str, model: str | None, path: Path | None = None) -> Path:
    """Record the owner's choice of backend in the user file. Other settings are kept.

    A `command` at the top of `[llm]` is removed, because it would take precedence.
    Comments in the file are not kept: it is rewritten from its values.
    """
    path = path or USER_CONFIG
    data = _read(path) if path.is_file() else {}
    llm = data.setdefault("llm", {})
    llm.pop("command", None)
    llm["backend"] = name
    if model:
        llm["model"] = model
    else:
        llm.pop("model", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_toml(data)).strip() + "\n")
    return path

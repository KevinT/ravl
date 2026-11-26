"""Configuration, resolved from three files, later overriding earlier.

1. User file (`~/.config/ravl/config.toml`): the LLM command, set once per host.
2. `ravl.toml` at the root of a tree of loops: settings for the whole tree.
3. `config/` in the loop directory: the owner's settings for that loop.

No environment variable is read. The core names no environment: the LLM is a
command the owner supplies, and resources are entries the owner lists.
"""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path

from . import __version__

USER_CONFIG = Path.home() / ".config" / "ravl" / "config.toml"
TREE_FILE = "ravl.toml"
MODES = ("lock", "never-lock", "learned")

DEFAULTS: dict = {
    # argv of a command that reads a prompt on stdin and writes the response on
    # stdout. `llm.act`, `llm.learn` and `llm.codegen` may each override it.
    "llm": {"command": None, "timeout_s": 900},
    "run": {"check_timeout_s": 120, "code_timeout_s": 600, "keep_runs": 200},
    "learn": {
        "promote_after": 3,      # consecutive LLM-driven passes before code is generated
        "hold_hours": 24,        # how long a hold written by Learn stays in force
        "never_lock_after": 3,   # declined code generations before proposing never-lock
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
    return list(command) if command else None

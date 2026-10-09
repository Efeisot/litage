"""Small sysfs helpers. Read-only funcs never raise; write funcs return bool."""
from __future__ import annotations

import os


def read_str(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return None


def read_int(path: str) -> int | None:
    s = read_str(path)
    if s is None:
        return None
    try:
        return int(s.split()[0])
    except ValueError:
        return None


def write_str(path: str, value: str) -> tuple[bool, str]:
    """Try to write; return (ok, message). Caller decides sudo/polkit."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
        return True, "ok"
    except PermissionError:
        return False, f"permission denied writing {path} (need root?)"
    except OSError as e:
        return False, f"cannot write {path}: {e}"


def first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def list_dir(path: str) -> list[str]:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []

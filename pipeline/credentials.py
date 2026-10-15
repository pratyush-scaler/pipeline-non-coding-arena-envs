"""Reloadable OpenAI credentials without changing request or spend budgets.

The CLI enables keys.env loading; explicit pool paths also opt in. An explicit
canonical environment override isolates the default pool from that file.
CLI-managed values follow file revisions instead of keeping stale aliases alive.
Rotation does not increase organization or project rate limits.
"""
from __future__ import annotations

import os
import re
import threading
from collections.abc import Mapping, MutableMapping
from pathlib import Path


KEYS_FILE = Path(__file__).resolve().parents[1] / "keys.env"
_KEY_NAME = re.compile(r"\A(OPENAI|OPEN_AI)_API_KEY(?:_?([1-9][0-9]{0,8}))?\Z")
_environment_lock = threading.Lock()
_managed_environment: dict[str, str] = {}
_enabled_keys_file: Path | None = None


def _key_order(name: str) -> tuple | None:
    match = _KEY_NAME.fullmatch(name)
    if not match:
        return None
    prefix, number = match.groups()
    if number is None:
        return (0 if prefix == "OPENAI" else 1, 0, name)
    return (2, int(number), 0 if prefix == "OPENAI" else 1, name)


def openai_keys(values: Mapping[str, str]) -> tuple[str, ...]:
    ordered = sorted(((_key_order(name), value.strip()) for name, value in values.items()
                      if _key_order(name) is not None and isinstance(value, str) and value.strip()),
                     key=lambda item: item[0])
    return tuple(dict.fromkeys(value for order, value in ordered))


def normalize_openai_aliases(values: Mapping[str, str]) -> dict[str, str]:
    normalized = dict(values)
    keys = openai_keys(values)
    if keys and not normalized.get("OPENAI_API_KEY", "").strip():
        normalized["OPENAI_API_KEY"] = keys[0]
    return normalized


def install_openai_environment(values: Mapping[str, str],
                               environment: MutableMapping[str, str] | None = None,
                               *, keys_file: Path | None = None) -> None:
    global _enabled_keys_file
    environment = os.environ if environment is None else environment
    with _environment_lock:
        _enabled_keys_file = Path(keys_file) if keys_file is not None else KEYS_FILE
        for name, value in normalize_openai_aliases(values).items():
            if _key_order(name) is not None and value.strip() and not environment.get(name, "").strip():
                environment[name] = value.strip()
                _managed_environment[name] = value.strip()
        if not environment.get("OPENAI_API_KEY", "").strip():
            keys = openai_keys(environment)
            if keys:
                environment["OPENAI_API_KEY"] = keys[0]
                _managed_environment["OPENAI_API_KEY"] = keys[0]


def read_key_file(path: Path) -> dict[str, str]:
    """keys.env exactly as written: every NAME=value line, comments skipped.

    No environment is consulted: a caller that must not inherit the shell's
    credentials (an inherited ANTHROPIC_AUTH_TOKEN once reached calibration
    campaigns) reads the file through this. `cli.load_keys` parses with it too.
    """
    values: dict[str, str] = {}
    path = Path(path)
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def _file_keys(filename: Path) -> dict[str, str]:
    try:
        text = filename.read_text()
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError):
        raise RuntimeError("OpenAI credential file could not be read") from None
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, separator, value = line.partition("=")
        if _key_order(name.strip()) is not None:
            values[name.strip()] = value.strip().strip('"').strip("'")
    return values


class OpenAICredentialPool:
    def __init__(self, keys_file: Path | None = None):
        self.keys_file = keys_file
        self._selected: str | None = None
        self._observed_keys: set[str] = set()
        self._lock = threading.Lock()

    def select(self, rotate_after: str | None = None) -> str:
        with self._lock:
            with _environment_lock:
                environment = dict(os.environ)
                managed = dict(_managed_environment)
                filename = self.keys_file if self.keys_file is not None else _enabled_keys_file
            canonical = environment.get("OPENAI_API_KEY", "").strip()
            if self.keys_file is None and canonical and managed.get("OPENAI_API_KEY") != canonical:
                filename = None
            values = _file_keys(filename) if filename is not None else {}
            for name, value in environment.items():
                if _key_order(name) is not None and value.strip() and managed.get(name) != value:
                    values[name] = value
            keys = openai_keys(values)
            if not keys:
                raise RuntimeError("No OpenAI credential configured; set OPENAI_API_KEY or numbered aliases in keys.env")
            self._observed_keys.update(keys)
            if rotate_after in keys:
                self._selected = keys[(keys.index(rotate_after) + 1) % len(keys)]
            elif self._selected not in keys:
                self._selected = keys[0]
            return self._selected

    def contains_secret(self, value: str) -> bool:
        with self._lock:
            return any(secret in value for secret in self._observed_keys)


OPENAI_POOL = OpenAICredentialPool()

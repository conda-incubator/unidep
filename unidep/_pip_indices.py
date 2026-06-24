"""Helpers for UniDep pip index URLs."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


_ENV_VAR_PATTERN = re.compile(
    r"\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<plain>[A-Za-z_][A-Za-z0-9_]*))",
)


class MissingPipIndexEnvironmentVariablesError(ValueError):
    """Raised when pip index URL environment variable placeholders are unset."""


def _validate_pip_indices_env_vars(pip_indices: Sequence[str]) -> tuple[str, ...]:
    """Validate that all env vars referenced by pip index URLs are set."""
    missing_names = sorted(
        {
            match.group("braced") or match.group("plain")
            for index in pip_indices
            for match in _ENV_VAR_PATTERN.finditer(index)
            if (match.group("braced") or match.group("plain")) not in os.environ
        },
    )
    if missing_names:
        names = ", ".join(missing_names)
        msg = (
            f"Unresolved environment variable(s) {names} in pip_indices."
            " Set the variable(s) before running UniDep or remove the placeholder(s)."
        )
        raise MissingPipIndexEnvironmentVariablesError(msg)
    return tuple(pip_indices)


def _expand_pip_indices_for_installer(pip_indices: Sequence[str]) -> tuple[str, ...]:
    """Expand pip index env vars for installer command arguments."""
    _validate_pip_indices_env_vars(pip_indices)
    return tuple(os.path.expandvars(index) for index in pip_indices)


def normalize_pip_indices(pip_indices: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize configured pip index URLs without expanding secrets."""
    if pip_indices is None:
        return ()
    if isinstance(pip_indices, str):
        return _validate_pip_indices_env_vars((pip_indices,))
    return _validate_pip_indices_env_vars(pip_indices)


def build_pip_index_arguments(pip_indices: Sequence[str]) -> list[str]:
    """Build pip/uv index arguments from pip_indices list."""
    args = []
    if pip_indices:
        expanded_indices = _expand_pip_indices_for_installer(pip_indices)
        args.extend(["--index-url", expanded_indices[0]])
        for index in expanded_indices[1:]:
            args.extend(["--extra-index-url", index])
    return args


def _redact_url_credentials(value: str) -> str:
    """Redact userinfo credentials from HTTP(S) URLs."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"} or "@" not in parsed.netloc:
        return value
    _userinfo, host = parsed.netloc.rsplit("@", 1)
    if not host:
        return value
    return urlunsplit(
        (parsed.scheme, f"***@{host}", parsed.path, parsed.query, parsed.fragment),
    )


def format_command_for_display(command: Sequence[str | Path]) -> str:
    """Format a command for logging without exposing URL credentials."""
    return " ".join(_redact_url_credentials(str(part)) for part in command)


def redact_command_for_exception(command: object) -> object:
    """Redact URL credentials from a subprocess exception command."""
    if isinstance(command, str):
        return _redact_url_credentials(command)
    if isinstance(command, list):
        return [_redact_url_credentials(str(part)) for part in command]
    if isinstance(command, tuple):
        return tuple(_redact_url_credentials(str(part)) for part in command)
    return command

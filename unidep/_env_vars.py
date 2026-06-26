"""Helpers for resolving environment variables from configured commands."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast

RefreshPolicy = Literal["missing", "always"]

_ENV_VAR_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class EnvVarCommandError(RuntimeError):
    """Raised when an env var command cannot produce a value."""


@dataclass(frozen=True)
class EnvVarCommand:
    """Command that can provide an environment variable value."""

    command: tuple[str, ...]
    refresh: RefreshPolicy = "missing"


def collect_env_vars(data: Mapping[str, Any]) -> dict[str, EnvVarCommand]:
    """Collect env var command definitions from the unidep config."""
    raw_env_vars = data.get("env_vars")
    if raw_env_vars is None:
        return {}
    if not isinstance(raw_env_vars, Mapping):
        msg = "`env_vars` must be a mapping."
        raise TypeError(msg)

    env_vars: dict[str, EnvVarCommand] = {}
    for name, raw_config in raw_env_vars.items():
        if not isinstance(name, str) or not _ENV_VAR_NAME.fullmatch(name):
            msg = "`env_vars` keys must be valid environment variable names."
            raise ValueError(msg)
        if not isinstance(raw_config, Mapping):
            msg = f"`env_vars.{name}` must be a mapping."
            raise TypeError(msg)
        raw_command = raw_config.get("command")
        if (
            isinstance(raw_command, str)
            or not isinstance(raw_command, Sequence)
            or not raw_command
            or any(not isinstance(part, str) or not part for part in raw_command)
        ):
            msg = f"`env_vars.{name}.command` must be a non-empty list of strings."
            raise TypeError(msg)
        raw_refresh = raw_config.get("refresh", "missing")
        if raw_refresh not in {"missing", "always"}:
            msg = f"`env_vars.{name}.refresh` must be 'missing' or 'always'."
            raise ValueError(msg)
        env_vars[name] = EnvVarCommand(
            command=tuple(raw_command),
            refresh=cast("RefreshPolicy", raw_refresh),
        )
    return env_vars


def resolve_env_var_commands(
    env_vars: Mapping[str, EnvVarCommand],
    *,
    no_env_commands: bool,
) -> dict[str, str]:
    """Run configured commands and return resolved environment variable values."""
    if no_env_commands:
        return {}
    to_resolve = {
        name: config
        for name, config in env_vars.items()
        if config.refresh == "always" or name not in os.environ
    }
    if not to_resolve:
        return {}
    return {
        name: _run_env_var_command(name, config) for name, config in to_resolve.items()
    }


def _run_env_var_command(name: str, config: EnvVarCommand) -> str:
    try:
        completed = subprocess.run(
            config.command,
            capture_output=True,
            check=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        msg = f"`env_vars.{name}.command` failed to resolve a value."
        raise EnvVarCommandError(msg) from error
    value = completed.stdout.strip()
    if not value:
        msg = f"`env_vars.{name}.command` produced no output."
        raise EnvVarCommandError(msg)
    return value

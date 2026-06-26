"""Tests for resolving installer environment variables from commands."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from unidep._cli import _install_command, main
from unidep._dependencies_parsing import parse_requirements
from unidep._env_vars import (
    EnvVarCommand,
    EnvVarCommandError,
    collect_env_vars,
    resolve_env_var_commands,
)
from unidep._pip_indices import MissingPipIndexEnvironmentVariablesError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def _write_private_index_project(
    tmp_path: Path,
    *,
    refresh: str | None = None,
) -> Path:
    refresh_config = "" if refresh is None else f"    refresh: {refresh}\n"
    req_file = tmp_path / "requirements.yaml"
    req_file.write_text(
        f"""\
name: test_project
env_vars:
  PRIVATE_REPO_TOKEN:
    command:
      - gcloud
      - auth
      - print-access-token
{refresh_config}pip_indices:
  - https://token:${{PRIVATE_REPO_TOKEN}}@private.example.com/simple/
dependencies:
  - pip: private-package
""",
    )
    return req_file


def test_install_resolves_missing_pip_index_env_var_from_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)

    def run(
        command: Sequence[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if tuple(command) == ("gcloud", "auth", "print-access-token"):
            return subprocess.CompletedProcess(command, 0, stdout="synthetic-token\n")
        raise AssertionError(command)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run", side_effect=run) as env_run,
        patch("unidep._cli._run_with_redacted_command") as pip_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
        )

    out = capsys.readouterr().out
    assert env_run.call_args[0][0] == ("gcloud", "auth", "print-access-token")
    assert "synthetic-token" not in out
    assert "https://***@private.example.com/simple/" in out
    assert (
        "https://token:synthetic-token@private.example.com/simple/"
        in pip_run.call_args[0][0]
    )


def test_install_no_env_commands_skips_command_and_reports_missing_var(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run") as env_run,
        pytest.raises(
            MissingPipIndexEnvironmentVariablesError,
            match="PRIVATE_REPO_TOKEN",
        ),
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
            no_env_commands=True,
        )

    env_run.assert_not_called()


def test_install_dry_run_does_not_run_env_var_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run") as env_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=True,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
        )

    out = capsys.readouterr().out
    env_run.assert_not_called()
    assert "https://***@private.example.com/simple/" in out
    assert "PRIVATE_REPO_TOKEN" not in os.environ


def test_install_no_dependencies_does_not_run_env_var_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run") as env_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=False,
            no_dependencies=True,
            no_uv=True,
            verbose=False,
        )

    env_run.assert_not_called()
    assert "PRIVATE_REPO_TOKEN" not in os.environ


def test_install_skip_pip_and_local_does_not_run_env_var_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run") as env_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=True,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
        )

    env_run.assert_not_called()
    assert "PRIVATE_REPO_TOKEN" not in os.environ


def test_install_keeps_existing_env_var_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "existing-token")
    req_file = _write_private_index_project(tmp_path)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run") as env_run,
        patch("unidep._cli._run_with_redacted_command") as pip_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
        )

    env_run.assert_not_called()
    assert (
        "https://token:existing-token@private.example.com/simple/"
        in pip_run.call_args[0][0]
    )


def test_install_refresh_always_replaces_existing_env_var(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "stale-token")
    req_file = _write_private_index_project(tmp_path, refresh="always")

    def run(
        command: Sequence[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if tuple(command) == ("gcloud", "auth", "print-access-token"):
            return subprocess.CompletedProcess(command, 0, stdout="fresh-token\n")
        raise AssertionError(command)

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch("unidep._env_vars.subprocess.run", side_effect=run),
        patch("unidep._cli._run_with_redacted_command") as pip_run,
    ):
        _install_command(
            req_file,
            conda_executable=None,
            conda_env_name=None,
            conda_env_prefix=None,
            conda_lock_file=None,
            dry_run=False,
            editable=False,
            skip_local=True,
            skip_pip=False,
            skip_conda=True,
            no_dependencies=False,
            no_uv=True,
            verbose=False,
        )

    assert (
        "https://token:fresh-token@private.example.com/simple/"
        in pip_run.call_args[0][0]
    )


def test_parse_env_vars_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """\
[tool.unidep]
dependencies = [{ pip = "private-package" }]
pip_indices = ["https://token:${PRIVATE_REPO_TOKEN}@private.example.com/simple/"]

[tool.unidep.env_vars.PRIVATE_REPO_TOKEN]
command = ["gcloud", "auth", "print-access-token"]
refresh = "always"
""",
    )

    parsed = parse_requirements(pyproject)

    assert parsed.env_vars == {
        "PRIVATE_REPO_TOKEN": EnvVarCommand(
            command=("gcloud", "auth", "print-access-token"),
            refresh="always",
        ),
    }


@pytest.mark.parametrize(
    ("config", "error_type", "match"),
    [
        ({"env_vars": []}, TypeError, "`env_vars` must be a mapping."),
        (
            {"env_vars": {"1BAD": {"command": ["echo"]}}},
            ValueError,
            "`env_vars` keys must be valid environment variable names.",
        ),
        (
            {"env_vars": {"TOKEN": "echo token"}},
            TypeError,
            "`env_vars.TOKEN` must be a mapping.",
        ),
        (
            {"env_vars": {"TOKEN": {"command": "echo token"}}},
            TypeError,
            "`env_vars.TOKEN.command` must be a non-empty list of strings.",
        ),
        (
            {"env_vars": {"TOKEN": {"command": ["echo"], "refresh": "never"}}},
            ValueError,
            "`env_vars.TOKEN.refresh` must be 'missing' or 'always'.",
        ),
    ],
)
def test_collect_env_vars_rejects_invalid_config(
    config: dict[str, Any],
    error_type: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error_type, match=match):
        collect_env_vars(config)


def test_parse_requirements_rejects_conflicting_env_var_definitions(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text(
        """\
env_vars:
  TOKEN:
    command: ["echo", "first"]
dependencies:
  - pip: private-package
""",
    )
    second.write_text(
        """\
env_vars:
  TOKEN:
    command: ["echo", "second"]
dependencies:
  - pip: other-private-package
""",
    )

    with pytest.raises(ValueError, match="Conflicting `env_vars` definitions"):
        parse_requirements(first, second)


def test_resolve_env_var_command_reports_failed_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TOKEN", raising=False)

    with (
        patch(
            "unidep._env_vars.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ("cmd",)),
        ),
        pytest.raises(EnvVarCommandError, match="failed to resolve a value"),
    ):
        resolve_env_var_commands(
            {"TOKEN": EnvVarCommand(command=("cmd",))},
            no_env_commands=False,
        )


def test_resolve_env_var_command_reports_empty_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TOKEN", raising=False)

    with (
        patch(
            "unidep._env_vars.subprocess.run",
            return_value=subprocess.CompletedProcess(("cmd",), 0, stdout="\n"),
        ),
        pytest.raises(EnvVarCommandError, match="produced no output"),
    ):
        resolve_env_var_commands(
            {"TOKEN": EnvVarCommand(command=("cmd",))},
            no_env_commands=False,
        )


def test_install_cli_no_env_commands_reports_missing_var(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("PRIVATE_REPO_TOKEN", raising=False)
    req_file = _write_private_index_project(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "unidep",
            "install",
            str(req_file),
            "--skip-conda",
            "--skip-local",
            "--conda-env-name",
            "test-env",
            "--no-env-commands",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    captured = capsys.readouterr()
    assert excinfo.value.code == 1
    assert "Unresolved environment variable(s) PRIVATE_REPO_TOKEN" in captured.err
    assert "Traceback" not in captured.err

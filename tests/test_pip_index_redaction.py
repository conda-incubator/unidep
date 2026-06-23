"""Tests for redacting pip index credentials in displayed commands."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from unidep._cli import _install_command, _pip_install_local
from unidep._pip_indices import (
    format_command_for_display,
    redact_command_for_exception,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_pip_install_local_print_redacts_index_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "synthetic-token")

    with patch("unidep._cli.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        _pip_install_local(
            "test_package",
            editable=False,
            dry_run=False,
            python_executable="/usr/bin/python",
            conda_run=[],
            no_uv=True,
            pip_indices=[
                "https://token:${PRIVATE_REPO_TOKEN}@private.example.com/simple/",
            ],
            flags=None,
        )

    out = capsys.readouterr().out
    assert "synthetic-token" not in out
    assert "https://***@private.example.com/simple/" in out
    assert (
        "https://token:synthetic-token@private.example.com/simple/"
        in run.call_args[0][0]
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://[not-valid/simple/", "https://[not-valid/simple/"),
        ("https://token@", "https://token@"),
    ],
)
def test_format_command_for_display_keeps_unparseable_urls(
    url: str,
    expected: str,
) -> None:
    assert format_command_for_display(["pip", "install", url]) == (
        f"pip install {expected}"
    )


def test_redact_command_for_exception_handles_non_list_commands() -> None:
    tuple_command = (
        "pip",
        "install",
        "https://token:synthetic-token@private.example.com/simple/",
    )

    assert (
        redact_command_for_exception(
            "https://token:synthetic-token@private.example.com/simple/",
        )
        == "https://***@private.example.com/simple/"
    )
    assert redact_command_for_exception(tuple_command) == (
        "pip",
        "install",
        "https://***@private.example.com/simple/",
    )

    sentinel = object()
    assert redact_command_for_exception(sentinel) is sentinel


def test_pip_install_local_error_redacts_index_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "synthetic-token")
    index_url = "https://token:synthetic-token@private.example.com/simple/"

    with (
        patch(
            "unidep._cli.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1,
                ["/usr/bin/python", "-m", "pip", "install", "--index-url", index_url],
            ),
        ),
        pytest.raises(subprocess.CalledProcessError) as exc_info,
    ):
        _pip_install_local(
            "test_package",
            editable=False,
            dry_run=False,
            python_executable="/usr/bin/python",
            conda_run=[],
            no_uv=True,
            pip_indices=[
                "https://token:${PRIVATE_REPO_TOKEN}@private.example.com/simple/",
            ],
            flags=None,
        )

    assert "synthetic-token" not in str(exc_info.value)
    assert "https://***@private.example.com/simple/" in str(exc_info.value)


def test_install_command_print_redacts_index_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "synthetic-token")
    req_file = tmp_path / "requirements.yaml"
    req_file.write_text(
        """\
name: test_project
pip_indices:
  - https://token:${PRIVATE_REPO_TOKEN}@private.example.com/simple/
dependencies:
  - pip: private-package
""",
    )

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch(
            "unidep._cli.subprocess.run",
        ) as run,
    ):
        run.return_value = MagicMock(returncode=0)
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
    assert "synthetic-token" not in out
    assert "https://***@private.example.com/simple/" in out
    assert (
        "https://token:synthetic-token@private.example.com/simple/"
        in run.call_args[0][0]
    )


def test_install_command_error_redacts_index_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PRIVATE_REPO_TOKEN", "synthetic-token")
    index_url = "https://token:synthetic-token@private.example.com/simple/"
    req_file = tmp_path / "requirements.yaml"
    req_file.write_text(
        """\
name: test_project
pip_indices:
  - https://token:${PRIVATE_REPO_TOKEN}@private.example.com/simple/
dependencies:
  - pip: private-package
""",
    )

    with (
        patch("unidep._cli._maybe_conda_executable", return_value=None),
        patch(
            "unidep._cli.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1,
                ["/usr/bin/python", "-m", "pip", "install", "--index-url", index_url],
            ),
        ),
        pytest.raises(subprocess.CalledProcessError) as exc_info,
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

    assert "synthetic-token" not in str(exc_info.value)
    assert "https://***@private.example.com/simple/" in str(exc_info.value)

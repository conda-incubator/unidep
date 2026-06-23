"""Tests for the supported Python version policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]


def _load_pyproject() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)


def _load_workflow(path: str) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    with (ROOT / path).open() as f:
        return yaml.load(f)


def test_project_metadata_requires_python_39_or_newer() -> None:
    pyproject = _load_pyproject()

    assert pyproject["project"]["requires-python"] == ">=3.9"
    assert pyproject["tool"]["ruff"]["target-version"] == "py39"
    assert pyproject["tool"]["mypy"]["python_version"] == "3.9"
    assert not any(
        dependency.startswith("typing_extensions")
        for dependency in pyproject["project"]["dependencies"]
    )


def test_ci_matrices_start_at_python_39() -> None:
    pytest_workflow = _load_workflow(".github/workflows/pytest.yml")
    install_workflow = _load_workflow(".github/workflows/install-example-projects.yml")

    assert (
        pytest_workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        == SUPPORTED_PYTHON_VERSIONS
    )
    assert (
        install_workflow["jobs"]["pip-install"]["strategy"]["matrix"][
            "python-version"
        ]
        == SUPPORTED_PYTHON_VERSIONS
    )
    assert (
        install_workflow["jobs"]["micromamba-install"]["strategy"]["matrix"][
            "python-version"
        ]
        == SUPPORTED_PYTHON_VERSIONS
    )
    assert (
        install_workflow["jobs"]["miniconda-install"]["strategy"]["matrix"][
            "python-version"
        ]
        == ["3.9", "3.12"]
    )

"""Tests for `unidep docs` README loading fallbacks."""

from __future__ import annotations

import pytest

import unidep._cli as cli


def test_read_docs_uses_legacy_importlib_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def read_text(package: str, resource: str, *, encoding: str) -> str:
        assert package == "unidep"
        assert resource == "README.md"
        assert encoding == "utf-8"
        return "legacy packaged README"

    monkeypatch.setattr(cli.importlib_resources, "files", None)
    monkeypatch.setattr(cli.importlib_resources, "read_text", read_text)

    assert cli._read_docs() == "legacy packaged README"


def test_read_docs_raises_when_readme_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingReadme:
        def __init__(self, *_args: object) -> None:
            pass

        @property
        def parent(self) -> MissingReadme:
            return self

        def __truediv__(self, _resource: str) -> MissingReadme:
            return self

        def resolve(self) -> MissingReadme:
            return self

        def is_file(self) -> bool:
            return False

    def missing_package_files(_package: str) -> MissingReadme:
        raise FileNotFoundError

    monkeypatch.setattr(cli.importlib_resources, "files", missing_package_files)
    monkeypatch.setattr(cli, "Path", MissingReadme)

    with pytest.raises(FileNotFoundError, match="Could not find README.md"):
        cli._read_docs()

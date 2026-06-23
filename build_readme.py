"""Build helpers for packaging documentation assets."""

from __future__ import annotations

from pathlib import Path

from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):  # noqa: N801
    """Copy README.md into the package build directory."""

    def run(self) -> None:
        """Run build_py and copy README.md into the built package."""
        super().run()

        source = Path(__file__).resolve().parent / "README.md"
        destination = Path(self.build_lib) / "unidep" / "README.md"
        self.mkpath(str(destination.parent))
        self.copy_file(str(source), str(destination))

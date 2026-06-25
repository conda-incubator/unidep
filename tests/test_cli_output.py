"""Tests for CLI output rendering helpers."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pytest

from unidep import _cli_output
from unidep._cli_output import print_command, print_phase


def test_install_output_plain_keeps_backtick_command_format(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_cli_output, "_rich_console", lambda: None)

    print_command(
        "Installing conda dependencies",
        "micromamba install numpy",
    )

    captured = capsys.readouterr()
    assert (
        "📦 Installing conda dependencies with `micromamba install numpy`"
        in captured.out
    )


def test_rich_class_returns_none_when_rich_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_find_spec = importlib.util.find_spec

    def find_spec(name: str) -> object | None:
        if name.startswith("rich"):
            return None
        return original_find_spec(name)

    monkeypatch.setattr(_cli_output.importlib.util, "find_spec", find_spec)

    assert _cli_output.rich_class("rich.text", "Text") is None


def test_rich_class_returns_none_when_rich_parent_package_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def find_spec(name: str) -> object | None:
        if name == "rich.console":
            msg = "No module named 'rich'"
            raise ModuleNotFoundError(msg)
        return object()

    monkeypatch.setattr(_cli_output.importlib.util, "find_spec", find_spec)

    assert _cli_output.rich_class("rich.console", "Console") is None


def test_install_output_auto_console_is_disabled_when_stdout_is_not_tty(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_cli_output.sys.stdout, "isatty", lambda: False)

    print_phase("Installing pip dependencies")

    captured = capsys.readouterr()
    assert "◆ Installing pip dependencies..." in captured.out


def test_install_output_auto_console_returns_none_when_rich_console_is_unavailable(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_cli_output.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(_cli_output, "rich_class", lambda *_args: None)

    print_phase("Installing pip dependencies")

    captured = capsys.readouterr()
    assert "◆ Installing pip dependencies..." in captured.out


def test_install_output_auto_console_uses_rich_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered_items: list[tuple[Any, dict[str, Any]]] = []

    class Console:
        def print(self, rendered: Any, **kwargs: Any) -> None:
            rendered_items.append((rendered, kwargs))

    class Text:
        def __init__(self, plain: str = "") -> None:
            self.plain = plain

        def append(self, text: str, **_kwargs: Any) -> None:
            self.plain += text

    def rich_class(module_name: str, _class_name: str) -> type[Console | Text]:
        if module_name == "rich.console":
            return Console
        return Text

    monkeypatch.setattr(_cli_output.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(_cli_output, "rich_class", rich_class)

    print_phase("Installing pip dependencies")

    assert rendered_items
    rendered, kwargs = rendered_items[0]
    assert rendered.plain == "◆ Installing pip dependencies..."
    assert kwargs == {"soft_wrap": True}


def test_install_output_falls_back_to_plain_command_without_rich_text(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Console:
        pass

    monkeypatch.setattr(_cli_output, "_rich_console", Console)
    monkeypatch.setattr(_cli_output, "rich_class", lambda *_args: None)

    print_command(
        "Installing pip dependencies",
        "uv pip install pydantic",
    )

    captured = capsys.readouterr()
    assert (
        "📦 Installing pip dependencies with `uv pip install pydantic`" in captured.out
    )


def test_install_output_rich_styles_exact_command_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Console:
        def __init__(self) -> None:
            self.rendered: Any | None = None
            self.print_kwargs: dict[str, Any] = {}

        def print(self, rendered: Any | None = None, **kwargs: Any) -> None:
            if rendered is not None:
                self.rendered = rendered
                self.print_kwargs = kwargs

    command = (
        "micromamba install --yes --override-channels --channel conda-forge "
        'fastapi httpx numpy"<3" pip pydantic python"=3.12.*" sqlalchemy'
    )
    console = Console()

    monkeypatch.setattr(_cli_output, "_rich_console", lambda: console)

    print_command("Installing conda dependencies", command)

    assert console.rendered is not None
    assert console.rendered.plain == f"📦 Installing conda dependencies with {command}"
    command_start = len("📦 Installing conda dependencies with ")
    assert [
        (span.start, span.end, str(span.style)) for span in console.rendered.spans
    ] == [(command_start, command_start + len(command), "bold cyan")]
    assert console.print_kwargs == {"soft_wrap": True}


def test_install_output_print_phase_prints_colored_line_without_spinner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Console:
        def __init__(self) -> None:
            self.status_calls: list[tuple[str, str]] = []
            self.rendered: list[Any] = []
            self.print_kwargs: list[dict[str, Any]] = []

        def print(self, rendered: Any | None = None, **kwargs: Any) -> None:
            if rendered is not None:
                self.rendered.append(rendered)
                self.print_kwargs.append(kwargs)

        def status(self, label: str, *, spinner: str) -> None:
            self.status_calls.append((label, spinner))

    console = Console()
    monkeypatch.setattr(_cli_output, "_rich_console", lambda: console)

    print_phase("Installing pip dependencies")

    assert console.status_calls == []
    assert len(console.rendered) == 1
    rendered = console.rendered[0]
    assert rendered.plain == "◆ Installing pip dependencies..."
    assert [(span.start, span.end, str(span.style)) for span in rendered.spans] == [
        (0, len("◆"), "bold green"),
        (1, len("◆ Installing pip dependencies..."), "bold yellow"),
    ]
    assert console.print_kwargs == [{"soft_wrap": True}]


def test_install_output_print_phase_plain_prints_symbol(
    capsys: pytest.CaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_cli_output, "_rich_console", lambda: None)

    print_phase("Installing pip dependencies")

    captured = capsys.readouterr()
    assert "◆ Installing pip dependencies..." in captured.out


def test_install_output_print_phase_falls_back_without_rich_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Console:
        def __init__(self) -> None:
            self.rendered: list[str] = []

        def print(self, rendered: str) -> None:
            self.rendered.append(rendered)

    console = Console()
    monkeypatch.setattr(_cli_output, "_rich_console", lambda: console)
    monkeypatch.setattr(_cli_output, "rich_class", lambda *_args: None)

    print_phase("Installing conda dependencies")

    assert console.rendered == ["◆ Installing conda dependencies..."]

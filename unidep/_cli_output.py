"""CLI output helpers with optional Rich styling."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from typing import Any


def rich_class(module_name: str, class_name: str) -> Any | None:
    """Return a Rich class if Rich is installed."""
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError:
        return None
    if spec is None:
        return None
    module = importlib.import_module(module_name)
    return getattr(module, class_name, None)


def _rich_console() -> Any | None:
    """Return a Rich console for interactive install output, if available."""
    if not sys.stdout.isatty():
        return None
    console_cls = rich_class("rich.console", "Console")
    if console_cls is None:
        return None

    return console_cls()


def print_command(
    label: str,
    command: str,
    *,
    emoji: str = "📦",
    blank_after: bool = True,
) -> None:
    """Print an install command, styling the command when Rich is available."""
    console = _rich_console()
    if console is None:
        suffix = "\n" if blank_after else ""
        print(f"{emoji} {label} with `{command}`{suffix}")
        return

    text_cls = rich_class("rich.text", "Text")
    if text_cls is None:
        suffix = "\n" if blank_after else ""
        print(f"{emoji} {label} with `{command}`{suffix}")
        return

    prefix = f"{emoji} {label} with "
    rendered = text_cls(prefix)
    rendered.append(command, style="bold cyan")
    console.print(rendered, soft_wrap=True)
    if blank_after:
        console.print()


def print_phase(label: str) -> None:
    """Print a phase line before child installers own terminal output."""
    console = _rich_console()
    symbol = "◆"
    message = f"{symbol} {label}..."
    if console is None:
        print(message)
        return

    text_cls = rich_class("rich.text", "Text")
    if text_cls is None:
        console.print(message)
        return
    rendered = text_cls()
    rendered.append(symbol, style="bold green")
    rendered.append(f" {label}...", style="bold yellow")
    console.print(rendered, soft_wrap=True)

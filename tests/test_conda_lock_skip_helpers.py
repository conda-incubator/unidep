"""Tests for conda-lock skip helper edge cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unidep._conda_lock import _discard_skipped_missing_keys

if TYPE_CHECKING:
    from unidep.platform_definitions import CondaPip, Platform


def test_discard_skipped_missing_keys_removes_matching_names() -> None:
    missing_keys: set[tuple[CondaPip, Platform, str]] = {
        ("pip", "linux-64", "private-config[extra]"),
        ("pip", "linux-64", "public-helper"),
    }

    _discard_skipped_missing_keys(missing_keys, ["private_config"])

    assert missing_keys == {("pip", "linux-64", "public-helper")}

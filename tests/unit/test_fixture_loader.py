"""Synthetic fixture loader."""

from __future__ import annotations

import pytest

from tests.fixtures.loader import load


def test_load_returns_html() -> None:
    html = load("post_options_menu")
    assert "<!DOCTYPE html>" in html
    assert "option-delete" in html


def test_load_missing_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load("nonexistent_fixture")

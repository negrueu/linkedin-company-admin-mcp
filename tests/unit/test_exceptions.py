"""Exception construction and formatting."""

from __future__ import annotations

from linkedin_company_admin_mcp.core.exceptions import SelectorError


def test_selector_error_formats_metadata() -> None:
    err = SelectorError(
        "could not find delete option",
        selector_name="POST_OPTIONS_DELETE",
        last_verified="2026-04-17",
        url="https://www.linkedin.com/feed/update/urn:li:activity:123/",
    )
    msg = str(err)
    assert "could not find delete option" in msg
    assert "POST_OPTIONS_DELETE" in msg
    assert "2026-04-17" in msg
    assert "urn:li:activity:123" in msg
    assert "--debug-snapshot" in msg  # hint to user


def test_selector_error_works_without_metadata() -> None:
    err = SelectorError("raw message")
    assert str(err) == "raw message"

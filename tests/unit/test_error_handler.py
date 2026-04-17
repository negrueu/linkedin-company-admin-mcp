"""Error handler wrapping and logging."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkedin_company_admin_mcp.core.exceptions import (
    AuthenticationError,
    LinkedInMCPError,
    SelectorError,
    ToolExecutionError,
)
from linkedin_company_admin_mcp.error_handler import (
    raise_tool_error,
    raise_tool_error_with_snapshot,
)


def test_mcp_error_passes_through() -> None:
    original = AuthenticationError("not logged in")
    with pytest.raises(AuthenticationError) as exc_info:
        raise_tool_error(original, "my_tool")
    assert exc_info.value is original


def test_generic_exception_gets_wrapped() -> None:
    with pytest.raises(ToolExecutionError) as exc_info:
        raise_tool_error(ValueError("boom"), "my_tool")
    assert exc_info.value.tool_name == "my_tool"
    assert isinstance(exc_info.value.cause, ValueError)
    assert "my_tool" in str(exc_info.value)


def test_subclass_of_mcp_error_preserves_type() -> None:
    class Custom(LinkedInMCPError):
        pass

    original = Custom("whatever")
    with pytest.raises(Custom):
        raise_tool_error(original, "tool")


async def test_raise_tool_error_triggers_snapshot_when_enabled(tmp_path: Path) -> None:
    page = MagicMock()
    page.url = "https://x/"
    page.content = AsyncMock(return_value="<html/>")
    page.screenshot = AsyncMock()

    with pytest.raises(SelectorError):
        await raise_tool_error_with_snapshot(
            SelectorError("no match", selector_name="X"),
            tool_name="demo",
            page=page,
            snapshot_dir=tmp_path,
            enabled=True,
        )
    assert any(p.suffix == ".html" for p in tmp_path.iterdir())


async def test_raise_tool_error_no_snapshot_when_disabled(tmp_path: Path) -> None:
    page = MagicMock()
    page.url = "https://x/"
    page.content = AsyncMock(return_value="<html/>")
    page.screenshot = AsyncMock()

    with pytest.raises(SelectorError):
        await raise_tool_error_with_snapshot(
            SelectorError("no match"),
            tool_name="demo",
            page=page,
            snapshot_dir=tmp_path,
            enabled=False,
        )
    assert list(tmp_path.iterdir()) == []

"""Error handler wrapping and logging."""

from __future__ import annotations

import pytest

from linkedin_company_admin_mcp.core.exceptions import (
    AuthenticationError,
    LinkedInMCPError,
    ToolExecutionError,
)
from linkedin_company_admin_mcp.error_handler import raise_tool_error


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

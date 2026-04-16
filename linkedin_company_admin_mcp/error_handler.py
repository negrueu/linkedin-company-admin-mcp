"""Centralised tool error routing.

Every MCP tool should wrap its body in ``try/except Exception`` and call
``raise_tool_error`` on failure. That keeps the user-visible surface
consistent and removes ad-hoc error formatting from each tool.
"""

from __future__ import annotations

import logging
from typing import NoReturn

from linkedin_company_admin_mcp.core.exceptions import (
    LinkedInMCPError,
    ToolExecutionError,
)

_log = logging.getLogger(__name__)


def raise_tool_error(exc: BaseException, tool_name: str) -> NoReturn:
    """Log the failure and re-raise a well-typed error.

    If ``exc`` is already a ``LinkedInMCPError``, re-raise as-is so callers
    see the specific subclass. Unknown exceptions get wrapped in
    ``ToolExecutionError`` so the tool boundary is always typed.
    """
    if isinstance(exc, LinkedInMCPError):
        _log.error("tool '%s' failed: %s", tool_name, exc)
        raise exc
    _log.exception("tool '%s' failed with unexpected error", tool_name)
    raise ToolExecutionError(tool_name, exc) from exc

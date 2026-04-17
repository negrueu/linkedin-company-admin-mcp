"""Centralised tool error routing.

Every MCP tool should wrap its body in ``try/except Exception`` and call
``raise_tool_error`` on failure. That keeps the user-visible surface
consistent and removes ad-hoc error formatting from each tool.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from linkedin_company_admin_mcp.core.debug_snapshot import capture_snapshot
from linkedin_company_admin_mcp.core.exceptions import (
    LinkedInMCPError,
    ToolExecutionError,
)

if TYPE_CHECKING:  # pragma: no cover
    from patchright.async_api import Page

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


async def raise_tool_error_with_snapshot(
    exc: BaseException,
    *,
    tool_name: str,
    page: "Page | None",
    snapshot_dir: Path,
    enabled: bool,
) -> NoReturn:
    """Same as ``raise_tool_error`` but additionally captures a snapshot.

    Called from provider code inside except blocks so we have a live
    ``page`` available. ``enabled`` comes from
    ``BrowserConfig.debug_snapshot`` and defaults to ``False``.
    """
    if enabled and page is not None:
        try:
            await capture_snapshot(page, snapshot_dir=snapshot_dir, label=tool_name)
        except Exception:  # noqa: BLE001
            _log.exception("snapshot capture itself failed; continuing with original error")
    raise_tool_error(exc, tool_name)

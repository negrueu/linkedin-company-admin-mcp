"""Exception taxonomy.

Every tool surface exception MUST be one of these types. Unknown exceptions
get wrapped by ``error_handler.raise_tool_error`` into ``ToolExecutionError``.
"""

from __future__ import annotations


class LinkedInMCPError(Exception):
    """Base class for all errors raised by this package."""


class ConfigurationError(LinkedInMCPError):
    """The environment or arguments are invalid."""


class AuthenticationError(LinkedInMCPError):
    """Session is missing, expired, or LinkedIn is showing an authwall."""


class SelectorError(LinkedInMCPError):
    """A DOM selector returned no match, meaning LinkedIn likely drifted.

    When raised by provider code pass ``selector_name`` (constant name in
    ``selectors/__init__.py``), ``last_verified`` (the date comment), and
    the offending ``url``. The user-visible message then includes the hint
    to re-run with ``--debug-snapshot`` and the exact selector to update.
    """

    def __init__(
        self,
        message: str,
        *,
        selector_name: str | None = None,
        last_verified: str | None = None,
        url: str | None = None,
    ) -> None:
        parts = [message]
        if selector_name:
            parts.append(f"selector={selector_name}")
        if last_verified:
            parts.append(f"last_verified={last_verified}")
        if url:
            parts.append(f"url={url}")
        if any([selector_name, last_verified, url]):
            parts.append("hint: run with --debug-snapshot to capture HTML+PNG")
        super().__init__(" | ".join(parts))
        self.selector_name = selector_name
        self.last_verified = last_verified
        self.url = url


class RateLimitError(LinkedInMCPError):
    """The per-tool rate limit was hit. Operation was not executed."""


class ToolExecutionError(LinkedInMCPError):
    """Fallback wrapper for unexpected errors during tool execution."""

    def __init__(self, tool_name: str, cause: BaseException) -> None:
        super().__init__(f"tool '{tool_name}' failed: {cause}")
        self.tool_name = tool_name
        self.cause = cause

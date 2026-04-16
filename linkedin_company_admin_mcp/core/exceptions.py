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
    """A DOM selector returned no match, meaning LinkedIn likely drifted."""


class RateLimitError(LinkedInMCPError):
    """The per-tool rate limit was hit. Operation was not executed."""


class ToolExecutionError(LinkedInMCPError):
    """Fallback wrapper for unexpected errors during tool execution."""

    def __init__(self, tool_name: str, cause: BaseException) -> None:
        super().__init__(f"tool '{tool_name}' failed: {cause}")
        self.tool_name = tool_name
        self.cause = cause

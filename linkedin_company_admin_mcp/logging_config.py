"""Logging setup. Called once from ``cli.main`` before anything else."""

from __future__ import annotations

import logging
import sys

from linkedin_company_admin_mcp.config.schema import LogLevel

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: LogLevel = "INFO") -> None:
    """Install a root handler writing to stderr.

    We write to stderr (not stdout) because the stdio transport uses stdout
    for MCP protocol traffic and any log line there corrupts the stream.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(getattr(logging, level))

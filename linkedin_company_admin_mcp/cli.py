"""Command-line entry point.

This is a stub for Faza 0 (bootstrap). Real implementation lands in Faza 1.
"""

from __future__ import annotations

import argparse
import sys

from linkedin_company_admin_mcp import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="linkedin-company-admin-mcp",
        description="MCP server for LinkedIn Company Page administration.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open a visible browser window for manual LinkedIn login. "
        "Persists session to the browser profile directory.",
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="Wipe the persistent browser profile (forces re-login on next run).",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=None,
        help="MCP transport. Default: stdio (for Claude Desktop).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.login or args.logout or args.transport:
        print(
            "Server runtime is not implemented yet (Faza 1). "
            "Flags received: "
            f"login={args.login}, logout={args.logout}, transport={args.transport}",
            file=sys.stderr,
        )
        return 1

    print(
        "linkedin-company-admin-mcp: bootstrap only. Run `--help` for options.",
        file=sys.stderr,
    )
    return 0

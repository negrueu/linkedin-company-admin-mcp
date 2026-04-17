"""Command-line entry point."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from linkedin_company_admin_mcp import __version__
from linkedin_company_admin_mcp.config.loaders import load_config
from linkedin_company_admin_mcp.core.auth import SessionInfo, run_login, run_logout
from linkedin_company_admin_mcp.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
)
from linkedin_company_admin_mcp.logging_config import configure_logging
from linkedin_company_admin_mcp.selectors.staleness import (
    SelectorEntry,
    find_stale,
    parse_selectors_file,
)

_log = logging.getLogger(__name__)

_SELECTORS_PATH = Path(__file__).parent / "selectors" / "__init__.py"


def _collect_selector_entries() -> list[SelectorEntry]:
    return parse_selectors_file(_SELECTORS_PATH)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="linkedin-company-admin-mcp",
        description="MCP server for LinkedIn Company Page administration.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
        help="MCP transport. Default (from env or 'stdio') used for Claude Desktop.",
    )
    parser.add_argument(
        "--debug-snapshot",
        action="store_true",
        help="On any tool error, save HTML + PNG snapshot next to the profile "
        "directory so failures can be reported with reproducible evidence.",
    )
    parser.add_argument(
        "--check-selectors",
        action="store_true",
        help="Report any selector whose last-verified date is older than "
        "--max-age-days and exit with code 3. CI-friendly, no browser required.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=60,
        help="Threshold for --check-selectors (default: 60).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.check_selectors:
        entries = _collect_selector_entries()
        stale = find_stale(entries, max_age_days=args.max_age_days, today=date.today())
        if not stale:
            print(
                f"all selectors fresh (threshold {args.max_age_days} days, "
                f"{len(entries)} entries)"
            )
            return 0
        print(f"stale selectors (threshold {args.max_age_days} days):")
        for e in stale:
            age = (date.today() - e.last_verified).days
            print(
                f"  {e.name}: last verified {e.last_verified.isoformat()} "
                f"({age} days ago)"
            )
        return 3

    try:
        config = load_config(args=args)
    except ConfigurationError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2

    if args.debug_snapshot:
        config.browser.debug_snapshot = True

    configure_logging(config.server.log_level)

    if args.logout:
        info = run_logout(config.browser)
        print(_format_session(info))
        return 0

    if args.login:
        try:
            info = asyncio.run(run_login(config.browser))
        except AuthenticationError as e:
            print(f"login failed: {e}", file=sys.stderr)
            return 1
        print(_format_session(info))
        return 0 if info.logged_in else 1

    from linkedin_company_admin_mcp.server import create_mcp_server

    server = create_mcp_server(config)
    transport = config.server.transport
    _log.info("starting MCP server on transport=%s", transport)

    if transport == "stdio":
        server.run(transport="stdio", show_banner=False)
    else:
        server.run(
            transport="streamable-http",
            host=config.server.host,
            port=config.server.port,
            path=config.server.http_path,
            show_banner=False,
        )
    return 0


def _format_session(info: SessionInfo) -> str:
    import json

    return json.dumps(asdict(info), indent=2)

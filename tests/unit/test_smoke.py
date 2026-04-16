"""Smoke test ensuring package imports and exposes a version string."""

from linkedin_company_admin_mcp import __version__
from linkedin_company_admin_mcp.cli import build_parser


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__.count(".") == 2


def test_cli_parser_has_login_flag() -> None:
    parser = build_parser()
    ns = parser.parse_args(["--login"])
    assert ns.login is True


def test_cli_parser_default_no_flags() -> None:
    parser = build_parser()
    ns = parser.parse_args([])
    assert ns.login is False
    assert ns.logout is False
    assert ns.transport is None

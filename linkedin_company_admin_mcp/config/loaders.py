"""Load configuration from environment variables (+ optional argparse).

Precedence (highest wins):
    1. Explicit kwargs passed to ``load_config``
    2. CLI arguments (parsed by ``cli.build_parser``)
    3. Environment variables (optionally from ``.env`` via python-dotenv)
    4. Defaults from ``schema.AppConfig``
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import cast, get_args

from dotenv import load_dotenv

from linkedin_company_admin_mcp.config.schema import (
    AppConfig,
    BrowserConfig,
    LogLevel,
    ServerConfig,
    Transport,
)
from linkedin_company_admin_mcp.config.schema import (
    EnvironmentKeys as E,
)
from linkedin_company_admin_mcp.core.exceptions import ConfigurationError


def _parse_bool(value: str) -> bool:
    """Interpret common truthy/falsy strings."""
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigurationError(f"cannot parse boolean: {value!r}")


def _parse_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except ValueError as e:
        raise ConfigurationError(f"{field_name} must be an integer, got {value!r}") from e


def _validate_choice(value: str, choices: tuple[str, ...], field_name: str) -> str:
    if value not in choices:
        raise ConfigurationError(f"{field_name} must be one of {choices}, got {value!r}")
    return value


def load_config(
    args: argparse.Namespace | None = None,
    env: dict[str, str] | None = None,
) -> AppConfig:
    """Build ``AppConfig`` from env + CLI args + defaults."""
    load_dotenv()
    source = env if env is not None else dict(os.environ)

    browser = BrowserConfig()
    server = ServerConfig()

    if raw := source.get(E.HEADLESS):
        browser.headless = _parse_bool(raw)
    if raw := source.get(E.USER_DATA_DIR):
        browser.user_data_dir = Path(raw).expanduser().resolve()

    if raw := source.get(E.TRANSPORT):
        _validate_choice(raw, get_args(Transport), E.TRANSPORT)
        server.transport = cast(Transport, raw)
    if raw := source.get(E.HOST):
        server.host = raw
    if raw := source.get(E.PORT):
        server.port = _parse_int(raw, E.PORT)
    if raw := source.get(E.HTTP_PATH):
        server.http_path = raw
    if raw := source.get(E.LOG_LEVEL):
        _validate_choice(raw, get_args(LogLevel), E.LOG_LEVEL)
        server.log_level = cast(LogLevel, raw)
    if raw := source.get(E.TOOL_TIMEOUT):
        server.tool_timeout_seconds = _parse_int(raw, E.TOOL_TIMEOUT)

    if args is not None and (transport := getattr(args, "transport", None)):
        server.transport = cast(Transport, transport)

    config = AppConfig(browser=browser, server=server)
    config.validate()
    return config

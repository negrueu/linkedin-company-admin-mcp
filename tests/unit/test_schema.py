"""Config dataclass validation."""

from __future__ import annotations

import pytest

from linkedin_company_admin_mcp.config.schema import (
    AppConfig,
    BrowserConfig,
    ServerConfig,
)
from linkedin_company_admin_mcp.core.exceptions import ConfigurationError


def test_default_app_config_validates() -> None:
    cfg = AppConfig()
    cfg.validate()


def test_invalid_browser_viewport_raises() -> None:
    bad = BrowserConfig(viewport_width=100, viewport_height=100)
    with pytest.raises(ConfigurationError, match="viewport too small"):
        bad.validate()


def test_invalid_server_port_raises() -> None:
    with pytest.raises(ConfigurationError, match="invalid port"):
        ServerConfig(port=0).validate()
    with pytest.raises(ConfigurationError, match="invalid port"):
        ServerConfig(port=70000).validate()


def test_invalid_tool_timeout_raises() -> None:
    with pytest.raises(ConfigurationError, match="tool_timeout_seconds"):
        ServerConfig(tool_timeout_seconds=0).validate()

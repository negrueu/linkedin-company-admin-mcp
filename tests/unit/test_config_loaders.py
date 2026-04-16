"""Config loading from environment variables."""

from __future__ import annotations

import pytest

from linkedin_company_admin_mcp.config.loaders import load_config
from linkedin_company_admin_mcp.core.exceptions import ConfigurationError


def test_defaults() -> None:
    cfg = load_config(env={})
    assert cfg.server.transport == "stdio"
    assert cfg.server.port == 8765
    assert cfg.server.log_level == "INFO"
    assert cfg.browser.headless is True


def test_env_override_transport() -> None:
    cfg = load_config(env={"LINKEDIN_TRANSPORT": "streamable-http"})
    assert cfg.server.transport == "streamable-http"


def test_env_override_headless_false() -> None:
    cfg = load_config(env={"LINKEDIN_HEADLESS": "0"})
    assert cfg.browser.headless is False


def test_env_override_port() -> None:
    cfg = load_config(env={"LINKEDIN_PORT": "9000"})
    assert cfg.server.port == 9000


def test_invalid_transport_raises() -> None:
    with pytest.raises(ConfigurationError, match="LINKEDIN_TRANSPORT"):
        load_config(env={"LINKEDIN_TRANSPORT": "websocket"})


def test_invalid_port_raises() -> None:
    with pytest.raises(ConfigurationError, match="must be an integer"):
        load_config(env={"LINKEDIN_PORT": "not-a-number"})


def test_port_out_of_range_raises() -> None:
    with pytest.raises(ConfigurationError, match="invalid port"):
        load_config(env={"LINKEDIN_PORT": "99999"})


def test_invalid_log_level_raises() -> None:
    with pytest.raises(ConfigurationError, match="LINKEDIN_LOG_LEVEL"):
        load_config(env={"LINKEDIN_LOG_LEVEL": "TRACE"})


def test_unparseable_bool_raises() -> None:
    with pytest.raises(ConfigurationError, match="cannot parse boolean"):
        load_config(env={"LINKEDIN_HEADLESS": "maybe"})

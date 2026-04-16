"""Configuration data classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from linkedin_company_admin_mcp.constants import DEFAULT_TOOL_TIMEOUT_SECONDS
from linkedin_company_admin_mcp.core.exceptions import ConfigurationError

Transport = Literal["stdio", "streamable-http"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


@dataclass(slots=True)
class BrowserConfig:
    """Browser/Patchright runtime configuration."""

    headless: bool = True
    user_data_dir: Path = field(
        default_factory=lambda: Path.home() / ".linkedin-company-admin" / "profile"
    )
    viewport_width: int = 1280
    viewport_height: int = 720
    slow_mo_ms: int = 0

    def validate(self) -> None:
        if self.viewport_width < 320 or self.viewport_height < 240:
            raise ConfigurationError(
                f"viewport too small: {self.viewport_width}x{self.viewport_height}"
            )


@dataclass(slots=True)
class ServerConfig:
    """MCP server runtime configuration."""

    transport: Transport = "stdio"
    host: str = "127.0.0.1"
    port: int = 8765
    http_path: str = "/mcp"
    log_level: LogLevel = "INFO"
    tool_timeout_seconds: int = DEFAULT_TOOL_TIMEOUT_SECONDS

    def validate(self) -> None:
        if not (1 <= self.port <= 65535):
            raise ConfigurationError(f"invalid port: {self.port}")
        if self.tool_timeout_seconds < 1:
            raise ConfigurationError(
                f"tool_timeout_seconds must be >= 1, got {self.tool_timeout_seconds}"
            )


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration."""

    browser: BrowserConfig = field(default_factory=BrowserConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    def validate(self) -> None:
        self.browser.validate()
        self.server.validate()


class EnvironmentKeys:
    """Centralised environment-variable names so they can be discovered."""

    TRANSPORT = "LINKEDIN_TRANSPORT"
    HOST = "LINKEDIN_HOST"
    PORT = "LINKEDIN_PORT"
    HTTP_PATH = "LINKEDIN_HTTP_PATH"
    HEADLESS = "LINKEDIN_HEADLESS"
    USER_DATA_DIR = "LINKEDIN_USER_DATA_DIR"
    LOG_LEVEL = "LINKEDIN_LOG_LEVEL"
    TOOL_TIMEOUT = "LINKEDIN_TOOL_TIMEOUT"

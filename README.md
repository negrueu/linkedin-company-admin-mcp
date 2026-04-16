# linkedin-company-admin-mcp

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**MCP server for LinkedIn Company Page administration.** Read analytics, manage posts, edit page details, grow followers, and bridge to your personal profile for employee advocacy workflows.

> **Complementary to [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server).** Stickerdaniel's project covers personal LinkedIn use cases (feed, messaging, search). This project fills the gap nobody else fills: **full administrative control of your LinkedIn Company Page**.

## Features

24 MCP tools across 5 categories:

| Category | Tools | Status |
|---|---|---|
| Company Read | 6 | Planned |
| Company Admin | 3 | Planned |
| Company Content | 6 | Planned |
| Company Growth | 2 | Planned |
| Personal -> Company Bridge | 4 | Planned |
| Infrastructure | 3 | Planned |

Full list in [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md).

## Installation

### Option 1: uvx (recommended)

```bash
uvx linkedin-company-admin-mcp@latest
```

Then add to your Claude Desktop config (`~/.config/Claude/claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "linkedin-company-admin": {
      "command": "uvx",
      "args": ["linkedin-company-admin-mcp@latest"]
    }
  }
}
```

### Option 2: Local development

```bash
git clone https://github.com/negrueu/linkedin-company-admin-mcp.git
cd linkedin-company-admin-mcp
uv sync
uv run linkedin-company-admin-mcp --login
```

## First-time login

**Credentials are never stored in this server.** Login is interactive:

```bash
uvx linkedin-company-admin-mcp --login
```

A visible Chromium window opens. Sign in to LinkedIn as you normally would (including 2FA). The persistent browser profile is saved to `~/.linkedin-company-admin/profile` (chmod 0o700 on Unix). All subsequent MCP calls reuse this session automatically.

To log out: `uvx linkedin-company-admin-mcp --logout` (wipes the profile directory).

## Security model

- No email/password handling. Your credentials never touch this code.
- Session state lives in a persistent browser profile, isolated per user, outside the repo.
- `.env` contains only configuration (log level, transport, etc). No secrets.
- The browser profile directory is chmod'd to `0o700` on first login.

## Status

This project is under active development. See [CHANGELOG.md](CHANGELOG.md) for version history and [issues](https://github.com/negrueu/linkedin-company-admin-mcp/issues) for the roadmap.

## Contributing

Contributions welcome. See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

[MIT](LICENSE)

# linkedin-company-admin-mcp

> **Language:** English - [Romana](docs/README.ro.md)

[![PyPI](https://img.shields.io/pypi/v/linkedin-company-admin-mcp.svg)](https://pypi.org/project/linkedin-company-admin-mcp/)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/negrueu/linkedin-company-admin-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/negrueu/linkedin-company-admin-mcp/actions/workflows/ci.yml)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

**MCP server for LinkedIn Company Page administration.** Read analytics, manage posts, edit page details, grow followers, and bridge your personal profile for employee advocacy workflows.

> **Complementary to [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server).** Stickerdaniel's project covers personal LinkedIn use cases (feed, messaging, search). This project fills the gap nobody else fills: **full administrative control of your LinkedIn Company Page**, plus a small set of personal-profile bridge tools used exclusively for employee-advocacy flows.

> ⚠️ **Terms of Service & account risk.** LinkedIn's [User Agreement](https://www.linkedin.com/legal/user-agreement) prohibits automated access to the platform. This server drives a real browser session on your behalf and LinkedIn may detect, rate-limit, or permanently restrict accounts that use it - including loss of access to the Company Page itself. **Use at your own risk.** Do not use this on a personal or business account you cannot afford to lose. There is no way for the authors to recover a restricted account for you. Prefer LinkedIn's [Community Management API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/) if you qualify for it.

> 🔐 **Security note - session dir equals credentials.** "No credentials stored" means this server never asks for your password and never puts one in a config file. It does **not** mean the profile directory is safe to share. After login, `~/.linkedin-company-admin/profile` contains LinkedIn session cookies that are functionally equivalent to your password + 2FA combined. Anyone who reads that directory gets full admin access to your account and Company Page. In particular: **do not sync this directory to OneDrive / iCloud / Dropbox / any cloud backup.** Keep it on local disk only, on a machine you trust.

## Why this project

LinkedIn's official Community Management API is invite-only. Scraping personal profiles is already well covered. What was missing: a stable, browser-first MCP that lets a page admin (or their assistant LLM) read analytics, draft posts, edit the about section, invite followers, and tag the page from a personal post - without any of it touching a stored password.

## Features at a glance

- **24 MCP tools** across 6 categories - see [Tool reference](#tool-reference) below.
- **Zero credentials** on disk. Interactive login via a visible Chromium window; session lives in a persistent profile directory (chmod 0o700 on Unix).
- **Stealth Chromium** via [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) (anti-detection fork of Playwright).
- **Provider abstraction** (`AdminProvider`, `PostsProvider`) so a future Community Management API backend can slot in without rewriting tools.
- **Rate limiting** actually applied (not just imported) - every write tool has a conservative hourly cap.
- **aria-label / role / innerText selectors only** - no obfuscated CSS class hashes. When LinkedIn ships a new UI, only `selectors/__init__.py` changes.
- **No god-files** (cap ~300 LOC per file), type-checked with mypy, linted with ruff.

## Installation

### Option 1: uvx (recommended)

Published on PyPI as [`linkedin-company-admin-mcp`](https://pypi.org/project/linkedin-company-admin-mcp/).

```bash
uvx linkedin-company-admin-mcp@latest --login
```

Then add to your Claude Desktop config (`~/.config/Claude/claude_desktop_config.json` or platform equivalent):

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

### Option 3: Docker

```bash
docker build -t linkedin-company-admin-mcp .
docker run --rm -it \
  -v linkedin_profile:/home/mcp/.linkedin-company-admin \
  linkedin-company-admin-mcp --login
```

## First-time login

**Credentials are never stored in this server.** Login is interactive:

```bash
uvx linkedin-company-admin-mcp --login
```

A visible Chromium window opens. Sign in to LinkedIn normally (including 2FA). The persistent browser profile is saved to `~/.linkedin-company-admin/profile` (chmod 0o700 on Unix). All subsequent MCP calls reuse this session automatically.

To log out: `uvx linkedin-company-admin-mcp --logout` (wipes the profile directory).

## Tool reference

Full argument lists and examples live in [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md). Summary:

### Session (3)

| Tool | Purpose |
|---|---|
| `session_status` | Is the persistent profile live and logged in? |
| `session_warmup` | Pre-open the browser + `/feed/` to reduce first-call latency. |
| `session_logout` | Close the browser and wipe the profile directory. |

### Company read (6)

| Tool | Purpose |
|---|---|
| `company_read_page` | Name, tagline, followers, about, industry, website. |
| `company_list_posts` | Recent posts with URN, text, reactions, comments. |
| `company_list_followers` | Followers list (admin-only; paginated). |
| `company_list_mentions` | Posts that mentioned the page (admin notifications). |
| `company_manage_admins` | List admins and their roles. |
| `company_analytics` | Followers / posts metrics for a 7d / 28d / 90d window. |

### Company admin write (3)

| Tool | Purpose |
|---|---|
| `company_edit_about` | Update the About section (with tagline fallback). |
| `company_edit_logo` | Upload a new logo (and optional banner). |
| `company_update_details` | Website, industry, size, specialties. |

### Company content (6)

| Tool | Purpose |
|---|---|
| `company_create_post` | Publish a text post (optional link / image). |
| `company_edit_post` | Replace the body of an existing post. |
| `company_delete_post` | Permanent delete - see [docs/RCA_DELETE_POST.md](docs/RCA_DELETE_POST.md). |
| `company_schedule_post` | Publish at a future ISO-8601 datetime. |
| `company_reply_comment` | Reply as the page to a comment on one of your posts. |
| `company_reshare_post` | Reshare another post on the page, optional commentary. |

### Company growth (2)

| Tool | Purpose |
|---|---|
| `company_invite_to_follow` | Send follow invitations to 1st-degree connections (LinkedIn caps 250/month). |
| `company_list_scheduled` | List posts queued for future publication. |

### Personal -> Company bridge (4)

| Tool | Purpose |
|---|---|
| `personal_tag_company` | Publish a personal post that @-mentions the page. |
| `personal_reshare_company_post` | Reshare a page post on your personal profile. |
| `personal_comment_as_admin` | Comment on a page post as the page (or as you). |
| `personal_read_company_mentions` | Scan your recent activity for posts that tag the page. |

## Security model

- **No email/password handling.** Credentials never touch this code.
- **Session state** lives in a persistent browser profile directory, isolated per OS user, outside the repo.
- **`.env`** contains only configuration (log level, transport, tool timeout). No secrets.
- The profile directory is chmod'd to `0o700` on first login (Unix).
- **Rate limiting** is enforced per-tool; the caps are conservative by design, tuned to what LinkedIn tolerates rather than what it allows.

## Supported workflows

- Draft, review, and publish a post on your company page from Claude.
- Tag the page from a personal post and track how the community responds.
- Audit who has posted about your page this week (admin mentions).
- Invite a batch of 1st-degree connections to follow the page, stopping at LinkedIn's monthly quota.
- Run a full CRUD pass on scheduled posts before a launch.

See [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md) for end-to-end examples.

## Troubleshooting

Selector drift, captcha, rate limits, cookie expiry and Chromium launch issues are all covered in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Contributing

Contributions welcome. See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for local setup, test layout, and the workflow for adding a new tool.

## Status

Under active development. See [CHANGELOG.md](CHANGELOG.md) for version history and [issues](https://github.com/negrueu/linkedin-company-admin-mcp/issues) for the roadmap.

## License

[MIT](LICENSE)

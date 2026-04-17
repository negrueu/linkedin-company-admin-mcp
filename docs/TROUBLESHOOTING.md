# Troubleshooting

Symptoms you are likely to hit, in roughly decreasing order of frequency.

## Session / login

### `session_status` says `active: false` after I logged in

The session is considered active only once the persistent profile contains LinkedIn cookies and `/feed/` loads without a redirect back to `/login`. If you logged in but closed the browser before reaching the feed, LinkedIn never wrote the final set of cookies.

Fix: run `--login` again and wait on the feed page for a few seconds before closing.

### "Browser manager not initialised"

You called a tool before `create_mcp_server()` finished setting up the singleton. In normal MCP usage this should not happen; if you see it, you are probably invoking internals directly. Use the `linkedin-company-admin-mcp` CLI or the FastMCP client, not `tools/*.py` functions directly.

### Login window opens but LinkedIn immediately shows the security challenge every time

LinkedIn uses Patchright's Chromium behaviour plus your IP reputation to decide when to challenge. Two things help:

- Do the challenge once and give LinkedIn a few minutes of continuous browsing (feed, profile, one DM) before closing - it builds "trust" for the device fingerprint.
- Avoid running `--login` from a datacenter IP (GitHub Actions, a Docker VPS). Use your normal workstation.

### The visible login window closes after 5 minutes with "login timeout"

By design. `core/auth.py::run_login()` caps the wait at 300 s. If you need more time (e.g. phone 2FA delay), run `--login` again; the session state from the first attempt is still there.

## Chromium / Patchright

### `patchright install chromium` failed on Linux

Run `patchright install chromium --with-deps` (requires sudo) to pull OS-level dependencies alongside the browser. On Debian/Ubuntu, the Dockerfile in this repo lists the minimal set of apt packages needed.

### Headless runs throw `net::ERR_HTTP2_PROTOCOL_ERROR` or similar transient errors

Almost always a Chromium-vs-Cloudflare dance. Retry once after a 5-second delay. If it persists across three retries, your IP is temporarily flagged - switch networks or wait 15-30 minutes.

### Browser launches but every page is blank

The profile directory is probably corrupt. Close any stray Chromium processes (`pkill -f patchright` on Unix), delete `~/.linkedin-company-admin/profile`, and run `--login` again.

## Selectors / parsing

### A read tool returns empty strings or missing fields

LinkedIn shipped a UI change. Because all selectors are centralised in `linkedin_company_admin_mcp/selectors/__init__.py` (and every entry carries a `# last verified YYYY-MM-DD` comment), the fix is usually a single-file update:

1. Open LinkedIn in the browser and inspect the changed element.
2. Prefer `aria-label` / `role` / visible text. Never use obfuscated class names (anything matching `_[0-9a-f]{8}`).
3. Update the selector constant and bump the `last verified` date.
4. Add a regression test with a captured HTML fixture under `tests/integration/fixtures/sample_html/`.

### Post body text includes "… see more" instead of the full content

By design in `company_list_posts` - we read what LinkedIn renders in the truncated card. To get the full body, fetch the post directly via its URN (planned as `company_read_post`).

### "Start a post" button not found (personal composer)

LinkedIn A/B-tests the feed composer. The helper in `tools/bridge_personal.py` first tries the literal text "Start a post"; if the match fails, inspect the feed DOM and add your variant to `providers/shared.py::js_click_by_text` call sites.

## Rate limits and LinkedIn quotas

### `RateLimitError: too many calls for key 'company_create_post'`

Hit our internal cap (defaults in each tool module). Inspect `core/rate_limit.py::RateLimiter` - the caps are sliding windows keyed on tool name. Wait; do not edit the cap to "make it work" without understanding why we chose it.

### Invites appear to go out but LinkedIn shows "you've reached the monthly limit"

`company_invite_to_follow` stops gracefully on this banner, but you may still see the message in the browser. LinkedIn's cap is 250 per page per calendar month. There is no known way to lift this (even with CMA).

### Post publishes but shows 0 reach after several hours

Most often a LinkedIn shadow-rate-limit on pages that post many auto-generated items in a row. Cooldown for 24-48 hours, then reduce cadence.

## Cookies / profile

### "Session expired" after weeks of use

LinkedIn rotates `li_at` on a schedule. Running `--login` reuses the existing profile and only refreshes cookies - you will not need to re-accept 2FA unless LinkedIn demands it.

### Multiple accounts

Use a separate profile directory per account:

```bash
LINKEDIN_USER_DATA_DIR=$HOME/.linkedin-company-admin/account-a linkedin-company-admin-mcp --login
LINKEDIN_USER_DATA_DIR=$HOME/.linkedin-company-admin/account-b linkedin-company-admin-mcp --login
```

Then pass the same env var when running the MCP server itself. Claude Desktop config:

```json
{
  "mcpServers": {
    "linkedin-company-admin-a": {
      "command": "uvx",
      "args": ["linkedin-company-admin-mcp@latest"],
      "env": { "LINKEDIN_USER_DATA_DIR": "/home/me/.linkedin-company-admin/account-a" }
    }
  }
}
```

## Other

### `company_delete_post` hangs or errors with "element not actionable"

This was the v1 blocker; the root cause and fix are documented in [RCA_DELETE_POST.md](RCA_DELETE_POST.md). If you see it again, LinkedIn has reshuffled the three-dot menu; re-apply the same `page.evaluate` strategy after updating the data-test-id / aria-label selectors.

### Claude Desktop shows no tools after I added the server

1. Restart Claude Desktop completely (not just close the window).
2. Run the CLI once manually to confirm it starts without error: `uvx linkedin-company-admin-mcp`.
3. Check Claude Desktop's log file (on macOS: `~/Library/Logs/Claude/mcp.log`) for launch errors.
4. If `uvx` is not on your `PATH` in Claude Desktop's environment, use the absolute path in the `command` field.

### I need to reset everything

```bash
linkedin-company-admin-mcp --logout   # wipes profile
rm -rf ~/.linkedin-company-admin      # belt and suspenders
linkedin-company-admin-mcp --login    # start over
```

If a bug remains after a clean reset, open an [issue](https://github.com/negrueu/linkedin-company-admin-mcp/issues) with the exact CLI command you ran, the tool call, and the error (with email / company names redacted).

## Debug snapshots

When a tool fails with `SelectorError` the message now contains the exact selector name, the date it was last verified and the page URL. Example:

```
SelectorError: could not find delete option on post page |
selector=OPTION_DELETE_LI |
last_verified=2026-04-17 |
url=https://www.linkedin.com/feed/update/urn:li:activity:123/ |
hint: run with --debug-snapshot to capture HTML+PNG
```

Re-run the server or CLI with `--debug-snapshot` (or set `LINKEDIN_DEBUG_SNAPSHOT=1` in your environment). On the next failure the package writes `<tool>_<timestamp>.html` and `.png` next to your profile directory:

```
~/.linkedin-company-admin/debug-snapshots/company_delete_post_20260417_153012.html
~/.linkedin-company-admin/debug-snapshots/company_delete_post_20260417_153012.png
```

Attach both files when opening a selector-drift issue.

## Selector staleness check

The package now tracks a `# last verified YYYY-MM-DD` comment next to every selector constant. To audit freshness without running a browser:

```bash
linkedin-company-admin-mcp --check-selectors --max-age-days 60
```

Exit code `3` means at least one selector is older than the threshold. The server itself also logs a warning at startup when stale entries are found.

## Persistent rate limiting

The default rate limiter is in-process. For users running the MCP from multiple clients or restarting Claude Desktop often, enable persistent state:

```bash
LINKEDIN_RATE_LIMIT_PERSIST=1 linkedin-company-admin-mcp
```

A sqlite file appears at `~/.linkedin-company-admin/rate-limits.db`. The limits defined by `@rate_limited` now survive restarts.

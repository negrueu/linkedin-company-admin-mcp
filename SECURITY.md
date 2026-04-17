# Security Policy

## Supported versions

Only the latest `0.x` release on [PyPI](https://pypi.org/project/linkedin-company-admin-mcp/) receives security fixes. `0.x` is pre-1.0 - breaking changes are possible between minor versions.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| < 0.1   | ❌        |

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.** Report privately to:

- **Email:** `office@ketu.ai`
- **Subject line:** `[SECURITY] linkedin-company-admin-mcp - <short summary>`
- **GitHub private advisory:** you may also use GitHub's [private vulnerability reporting](https://github.com/negrueu/linkedin-company-admin-mcp/security/advisories/new)

Please include:

1. A clear description of the issue and the impact you believe it has.
2. Steps to reproduce (code, config, commands).
3. Affected version(s) and environment (OS, Python version, Patchright version).
4. Whether the issue is already public, and if so where.

### Response expectations

- **Acknowledgement:** within 72 hours.
- **Initial assessment:** within 7 days.
- **Fix or mitigation:** depends on severity; critical issues are prioritized immediately.

We will credit reporters in the CHANGELOG unless they request otherwise.

## In scope

- Credential or session-token leakage from the server, its logs, or its error messages.
- Path traversal, arbitrary file write/read, or command injection via tool arguments.
- Rate-limit bypass that materially increases account-restriction risk for users.
- Vulnerabilities in how the server handles the persistent browser profile directory (permissions, cleanup, logging).
- Dependency vulnerabilities with a concrete exploit path through this codebase.

## Out of scope

- **LinkedIn's own security.** Report those to LinkedIn directly.
- **Session cookies leaving the user's machine.** The profile directory (`~/.linkedin-company-admin/profile`) is functionally equivalent to a password + 2FA combined. Users are responsible for keeping it on trusted local disk and **not** syncing it to cloud backups (OneDrive, iCloud, Dropbox, etc.). This is documented in the README.
- **Account restriction by LinkedIn.** Using this server violates LinkedIn's Terms of Service. Account loss is an accepted, documented risk. See the README warning.
- **Missing hardening** that is explicitly called out as a non-goal (e.g. multi-user isolation - the server is designed for single-user local use).

## Operational security notes for users

- Keep the profile directory on local disk with restrictive permissions. On Unix the server sets `0o700` automatically; on Windows rely on your user account ACLs.
- Rotate your LinkedIn session periodically by running `--logout` followed by `--login`.
- Never commit the profile directory, session cookies, or captured HTML/HAR snapshots to any git repository. `.gitignore` in this repo is wired to block this by default.
- If you suspect a session token was exposed, sign out of all LinkedIn sessions from [linkedin.com/psettings/sessions](https://www.linkedin.com/psettings/sessions) and re-authenticate.

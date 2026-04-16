# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project bootstrap: `pyproject.toml`, ruff, mypy, pytest, GitHub Actions CI.
- Core infrastructure: `BrowserManager` (persistent Patchright context with 0o700 profile),
  interactive `--login` / `--logout` flow, `SessionInfo`, sliding-window rate limiter,
  URN utilities, configuration loader, CLI entry point.
- Session tools: `session_status`, `session_warmup`, `session_logout`.
- Company read tools: `company_read_page`, `company_list_posts`, `company_list_followers`,
  `company_list_mentions`, `company_manage_admins`, `company_analytics`.
- Admin write tools: `company_edit_about`, `company_edit_logo`, `company_update_details`,
  backed by an `AdminProvider` abstraction.
- Content tools: `company_create_post`, `company_edit_post`, `company_delete_post`,
  `company_schedule_post`, `company_reply_comment`, `company_reshare_post`, backed
  by a `PostsProvider` abstraction. Root-cause analysis for the `artdeco-modal-outlet`
  overlay documented in `docs/RCA_DELETE_POST.md`.
- Growth tools: `company_invite_to_follow` (hard-capped, aware of LinkedIn's
  250/month quota), `company_list_scheduled`.
- Personal -> Company bridge tools: `personal_tag_company`, `personal_reshare_company_post`,
  `personal_comment_as_admin`, `personal_read_company_mentions`.
- Docs: `README.md` with full tool table, `docs/TOOL_REFERENCE.md` (arguments, returns,
  end-to-end examples), `docs/TROUBLESHOOTING.md`, `docs/CONTRIBUTING.md`,
  `docs/RCA_DELETE_POST.md`.
- Packaging: MIT `LICENSE`, `manifest.json` for Claude Desktop MCPB bundle, multi-stage
  `Dockerfile` with non-root `mcp` user and Patchright Chromium, `.dockerignore`.

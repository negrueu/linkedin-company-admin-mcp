# Tool reference

Full argument lists, return shapes, and end-to-end examples for every tool exposed by `linkedin-company-admin-mcp`.

Every write tool is wrapped in a sliding-window rate limiter (see `core/rate_limit.py`). The `max_per_hour` column is the hard cap applied by this server - LinkedIn's own quotas sit on top.

Legend for the **Rate** column:
- `-` means read-only; not rate-limited.
- `N/h` means up to N successful invocations per hour.

All tools accept `ctx: Context` as an implicit MCP-SDK parameter; it is not listed in the argument tables below.

Identity arguments:
- `company_id`: accepts either a numeric page ID (e.g. `"106949933"`) or a full URL (`"https://www.linkedin.com/company/ketu-ai/"`). The server normalises to the numeric ID.
- `post_urn` / `source_post_urn`: canonical LinkedIn URN such as `"urn:li:activity:7123456789012345678"`. The server also accepts `urn:li:ugcPost:` and `urn:li:share:` and resolves them where possible.

---

## Session

### `session_status`

| Arg | Type | Required | Description |
|---|---|---|---|
| - | - | - | - |

Returns `{ "active": bool, "user_data_dir": str, "detail": str }`. Runs without launching the browser when the profile folder alone can answer the question; otherwise performs a quick headless probe.

### `session_warmup`

| Arg | Type | Required | Description |
|---|---|---|---|
| - | - | - | - |

Opens the browser and visits `/feed/` to warm the session so the first real tool call is fast. Rate: `-` (idempotent).

### `session_logout`

| Arg | Type | Required | Description |
|---|---|---|---|
| - | - | - | - |

Closes the browser and deletes the persistent profile directory. Irreversible - you will need `--login` again afterwards. Rate: `-`.

---

## Company read

### `company_read_page`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |

Returns `{ name, tagline, followers, about, industry, website, company_id }`. Rate: `-`.

### `company_list_posts`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `max_posts` | `int` | no (default 20) | Cap on returned posts. |

Returns `{ company_id, count, posts: [{ urn, text, reactions, comments, published_at }] }`. Rate: `-`.

### `company_list_followers`

Admin-only. Returns the first page of followers with display name, headline and profile URL.

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `max_results` | `int` | no (default 50) | Hard cap. |

Returns `{ count, followers: [{ name, headline, profile_url }] }`. Rate: `-`.

### `company_list_mentions`

Admin notifications tab - posts that tagged the page.

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `max_results` | `int` | no (default 20) | Hard cap. |

Returns `{ count, mentions: [{ urn, author, text, timestamp }] }`. Rate: `-`.

### `company_manage_admins`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |

Returns `{ admins: [{ name, role, profile_url }] }`. Read-only in v1 - management operations are planned for v2 when the CMA provider lands. Rate: `-`.

### `company_analytics`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `timeframe` | `"7d" \| "28d" \| "90d"` | no (default `"28d"`) | Reporting window. |

Returns `{ timeframe, followers_delta, post_impressions, post_engagements, updated_at }`. Rate: `-`.

---

## Company admin write

### `company_edit_about`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `new_about` | `str` | yes | Full replacement text for the About field. |

Falls back to updating the tagline on older pages where the About field is missing. Rate: `5/h`.

### `company_edit_logo`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `logo_path` | `str` | yes | Absolute path to a local PNG/JPG. |
| `banner_path` | `str` | no | Absolute path to a local banner image. |

Rate: `3/h`.

### `company_update_details`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `website` | `str` | no | Homepage URL. |
| `industry` | `str` | no | Industry name from the LinkedIn picklist. |
| `size` | `str` | no | Size bucket (`"1-10"`, `"11-50"`, ...). |
| `specialties` | `list[str]` | no | Up to 20 specialty tags. |

Rate: `5/h`.

---

## Company content

### `company_create_post`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `text` | `str` | yes | Post body (hashtags and plain-text mentions auto-link on submit). |
| `link_url` | `str` | no | LinkedIn auto-renders a preview card. |
| `image_path` | `str` | no | Absolute path to a local image. |

Returns `{ ok, detail, extra: { has_link, has_image } }`. Rate: `10/h`.

### `company_edit_post`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `post_urn` | `str` | yes | URN from `company_list_posts`. |
| `new_text` | `str` | yes | Replacement body. |

Rate: `20/h`.

### `company_delete_post`

**Irreversible.** LinkedIn does not provide a trash for company posts. See [RCA_DELETE_POST.md](RCA_DELETE_POST.md) for the implementation quirks.

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `post_urn` | `str` | yes | URN of the post to delete. |

Rate: `15/h`.

### `company_schedule_post`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `text` | `str` | yes | Post body. |
| `scheduled_at_iso` | `str` | yes | ISO 8601 datetime with offset, e.g. `"2026-05-01T09:00:00+03:00"`. |

LinkedIn requires the time to be at least 10 minutes in the future and no more than 3 months out. Rate: `10/h`.

### `company_reply_comment`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `post_urn` | `str` | yes | URN of the post whose comment you reply to. |
| `comment_author_name` | `str` | yes | Case-insensitive substring match; the first matching comment wins. |
| `reply_text` | `str` | yes | Reply body. |

Rate: `30/h`.

### `company_reshare_post`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `source_post_urn` | `str` | yes | URN of the post being reshared. |
| `thoughts_text` | `str` | no | Leading commentary. |

Rate: `10/h`.

---

## Company growth

### `company_invite_to_follow`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |
| `max_invites` | `int` | no (default 50) | Hard cap for this invocation, 1-250. |

LinkedIn caps these at **250/month per page**. Default 50 so casual runs do not burn the allowance. Rate: `3/h`.

### `company_list_scheduled`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL. |

Returns `{ company_id, count, posts: [{ urn, text, scheduled_at }] }`. Rate: `-`.

---

## Personal -> Company bridge

These four tools exist purely to support employee-advocacy workflows (you posting about your own company). Anything further on personal profiles is out of scope - use [stickerdaniel/linkedin-mcp-server](https://github.com/stickerdaniel/linkedin-mcp-server).

### `personal_tag_company`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_name` | `str` | yes | Display name matching the @-typeahead suggestion. |
| `lead_text` | `str` | yes | Text inserted before the mention. May be empty. |
| `trailing_text` | `str` | yes | Text inserted after the mention. May be empty. |

Final post is assembled as `<lead_text> @<company>[first match] <trailing_text>`. Rate: `20/h`.

### `personal_reshare_company_post`

| Arg | Type | Required | Description |
|---|---|---|---|
| `source_post_urn` | `str` | yes | URN of the company post (from `company_list_posts`). |
| `thoughts_text` | `str` | no | Commentary added above the reshared post. |

Rate: `15/h`.

### `personal_comment_as_admin`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_id` | `str` | yes | Numeric ID or URL (used to locate the identity selector). |
| `source_post_urn` | `str` | yes | URN of the target post. |
| `comment_text` | `str` | yes | Comment body. |
| `comment_as_company` | `bool` | no (default `True`) | Flip the identity selector to the page before submitting. |

Rate: `30/h`.

### `personal_read_company_mentions`

| Arg | Type | Required | Description |
|---|---|---|---|
| `company_name` | `str` | yes | Matched case-insensitively inside your post bodies. |
| `max_results` | `int` | no (default 20) | Hard cap. |

Returns `{ company_name, count, posts: [{ urn, text, time }] }`. Rate: `-`.

---

## End-to-end examples

### Draft, publish, and verify a page post

```python
# 1) Create
result = await mcp.call_tool("company_create_post", {
    "company_id": "106949933",
    "text": "Launching our spring playbook today. Full details in comments.",
})

# 2) Verify it shows up at the top of the feed
posts = await mcp.call_tool("company_list_posts", {
    "company_id": "106949933",
    "max_posts": 1,
})
urn = posts["posts"][0]["urn"]

# 3) Fix a typo without reposting
await mcp.call_tool("company_edit_post", {
    "company_id": "106949933",
    "post_urn": urn,
    "new_text": "Launching our spring playbook today. Details in comments.",
})
```

### Employee-advocacy chain

```python
# 1) Tag the company in a personal post
await mcp.call_tool("personal_tag_company", {
    "company_name": "KETU AI",
    "lead_text": "Proud of the team shipping this:",
    "trailing_text": "- worth a read.",
})

# 2) Later, audit which personal posts mention the page
mentions = await mcp.call_tool("personal_read_company_mentions", {
    "company_name": "KETU AI",
    "max_results": 10,
})
```

### Weekly growth ping

```python
# Send up to 25 invites to 1st-degree connections
await mcp.call_tool("company_invite_to_follow", {
    "company_id": "106949933",
    "max_invites": 25,
})

# Check the scheduled queue before a launch
await mcp.call_tool("company_list_scheduled", {
    "company_id": "106949933",
})
```

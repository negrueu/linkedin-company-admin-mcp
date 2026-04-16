"""Centralised selector registry.

LinkedIn ships hashed CSS classes that drift weekly. To stay stable we
rely on ``aria-label``, ``role``, ``id`` and DOM structure. Every entry
below carries a ``# last verified`` comment. When something breaks, this
file is the single place that changes.
"""

from __future__ import annotations

# ---------- URL templates --------------------------------------------------

COMPANY_BASE = "https://www.linkedin.com/company/{company_id}"
COMPANY_ADMIN_DASHBOARD = f"{COMPANY_BASE}/admin/dashboard/"
COMPANY_ADMIN_PAGE_POSTS = f"{COMPANY_BASE}/admin/page-posts/published/"
COMPANY_ADMIN_ANALYTICS_UPDATES = f"{COMPANY_BASE}/admin/analytics/updates/"
COMPANY_ADMIN_ANALYTICS_FOLLOWERS = f"{COMPANY_BASE}/admin/analytics/followers/"
COMPANY_ADMIN_FOLLOWERS = f"{COMPANY_BASE}/admin/analytics/followers/"
COMPANY_ADMIN_NOTIFICATIONS = f"{COMPANY_BASE}/admin/notifications/all/"
COMPANY_ADMIN_MANAGE_ADMINS = f"{COMPANY_BASE}/admin/settings/manage-admins/"

# ---------- Company dashboard & header ------------------------------------

# last verified 2026-04-16
DASHBOARD_PAGE_NAME = "h1"
DASHBOARD_FOLLOWERS_LINK = 'a[href*="/followers/"]'
DASHBOARD_TAGLINE_CANDIDATES = (
    "p.org-top-card-summary__tagline",
    ".org-top-card-summary__tagline",
    '[data-test-id="org-tagline"]',
)


# ---------- Published posts -----------------------------------------------

# Posts on the admin published list are identified by the data-urn attribute.
# A standard entity lockup wraps the author, time and body.
#
# last verified 2026-04-16
PUBLISHED_POST_CONTAINER = '[data-urn^="urn:li:activity"]'
PUBLISHED_POST_TEXT = 'div[dir="ltr"]'
PUBLISHED_POST_TIMESTAMP = "time"
PUBLISHED_POST_REACTIONS_BTN = 'button[aria-label*="reaction"], span[aria-label*="like"]'
PUBLISHED_POST_COMMENT_BTN = 'button[aria-label*="comment"]'


# ---------- Followers list ------------------------------------------------

# last verified 2026-04-16
FOLLOWER_LIST_ITEM = ".org-view-page-followers-module__follower-list-item"
FOLLOWER_NAME = ".artdeco-entity-lockup__title"
FOLLOWER_HEADLINE = ".artdeco-entity-lockup__subtitle, .artdeco-entity-lockup__caption"
FOLLOWER_PROFILE_LINK = 'a[href*="/in/"]'


# ---------- Notifications / mentions --------------------------------------

# last verified 2026-04-16
MENTION_CARD = '[data-urn*="notification"], li.nt-card'
MENTION_EMPTY_STATE = '.nt-empty-state, [aria-label*="No notifications"]'
MENTION_TEXT = 'span[dir="ltr"], p[dir="ltr"]'
MENTION_LINK = "a[href]"


# ---------- Admin list (manage-admins page) -------------------------------

# last verified 2026-04-16
ADMIN_TABLE_ROW = ".org-admin-roles-module__table-wrapper tbody tr"
ADMIN_ROW_NAME = 'a[href*="/in/"]'
ADMIN_ROW_ROLE = ".org-admin-roles-module__role"
ADMIN_ROW_HEADLINE = ".entity-headline"


# ---------- Generic ------------------------------------------------------

EMPTY_STATE_MARKERS = (
    "No posts yet",
    "No notifications",
    "No followers yet",
)

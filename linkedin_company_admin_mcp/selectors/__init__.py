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
COMPANY_ADMIN_EDIT_MODAL = f"{COMPANY_BASE}/admin/dashboard/?editPage=true"
COMPANY_ADMIN_PAGE_POSTS = f"{COMPANY_BASE}/admin/page-posts/published/"
COMPANY_ADMIN_ANALYTICS_UPDATES = f"{COMPANY_BASE}/admin/analytics/updates/"
COMPANY_ADMIN_ANALYTICS_FOLLOWERS = f"{COMPANY_BASE}/admin/analytics/followers/"
COMPANY_ADMIN_FOLLOWERS = f"{COMPANY_BASE}/admin/analytics/followers/"
COMPANY_ADMIN_NOTIFICATIONS = f"{COMPANY_BASE}/admin/notifications/all/"
COMPANY_ADMIN_MANAGE_ADMINS = f"{COMPANY_BASE}/admin/settings/manage-admins/"

# The scheduled-posts list for a company is not a standalone URL; it renders
# as a dialog on top of /admin/page-posts/published/ when the query string
# ?share=true&view=management&actorCompanyId=<id> is supplied.
# last verified 2026-04-17
COMPANY_ADMIN_SCHEDULED_LIST = (
    f"{COMPANY_BASE}/admin?share=true&view=management&actorCompanyId={{company_id}}"
)

# ---------- Company dashboard & header ------------------------------------

# last verified 2026-04-17
DASHBOARD_PAGE_NAME = "h1.org-organizational-page-admin-navigation__title, h1"
DASHBOARD_FOLLOWER_COUNT = "a.org-organizational-page-admin-navigation__follower-count"
DASHBOARD_SLUG_LINK = 'a[href*="/company/"][href*="/posts"]'

# Edit Page modal (opened via ?editPage=true) - every field is an input/textarea/select
# with a stable #id. Nothing here relies on hashed classes.
#
# last verified 2026-04-17
EDIT_MODAL_DIALOG = '[role="dialog"]'
EDIT_FIELD_NAME = "#organization-name-field"
EDIT_FIELD_PUBLIC_URL = "#organization-public-url-field"
EDIT_FIELD_TAGLINE = "#organization-tagline-field"
EDIT_FIELD_DESCRIPTION = "#organization-description-field"
EDIT_FIELD_WEBSITE = "#organization-website-field"
EDIT_FIELD_INDUSTRY = "#organization-industry-typeahead"
EDIT_FIELD_SIZE = "#organization-size-select"
EDIT_FIELD_TYPE = "#organization-type-select"
EDIT_FIELD_PHONE = "#organization-phone-field"
EDIT_FIELD_FOUNDED = "#organization-founded-on-input"

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

# Each admin renders as a tr with class org-admin-roles-module__row.
# Name + headline are inside an artdeco-entity-lockup. Role is p.label-20dp.
#
# last verified 2026-04-17
ADMIN_TABLE_ROW = "tr.org-admin-roles-module__row, .org-admin-roles-module__row"
ADMIN_ROW_NAME = ".artdeco-entity-lockup__title"
ADMIN_ROW_HEADLINE = ".artdeco-entity-lockup__subtitle"
ADMIN_ROW_PROFILE_LINK = 'a[href^="/in/"], a[href*="/in/"]'
ADMIN_ROW_ROLE = "p.label-20dp, .org-admin-roles-module__role"


# ---------- Analytics metric cards ----------------------------------------

# last verified 2026-04-17
ANALYTICS_CARD = (
    ".member-analytics-addon-card__base-card, .artdeco-card.member-analytics-addon-card__base-card"
)
ANALYTICS_CAROUSEL_ITEM = ".member-analytics-addon-metrics-carousel-item"
ANALYTICS_DATE_RANGE_BUTTON = 'button[aria-label^="Date range"]'


# ---------- Generic ------------------------------------------------------

EMPTY_STATE_MARKERS = (
    "No posts yet",
    "No notifications",
    "No followers yet",
)

"""Backwards-compatible re-exports.

Prefer importing from ``linkedin_company_admin_mcp.providers.admin`` or
``linkedin_company_admin_mcp.providers.posts`` directly.
"""

from __future__ import annotations

from linkedin_company_admin_mcp.providers.admin import BrowserAdminProvider
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider
from linkedin_company_admin_mcp.providers.shared import (
    dirty_state_trigger,
    js_click_by_text,
    quill_insert_text,
    remove_blocking_modal_outlet,
)

__all__ = [
    "BrowserAdminProvider",
    "BrowserPostsProvider",
    "dirty_state_trigger",
    "js_click_by_text",
    "quill_insert_text",
    "remove_blocking_modal_outlet",
]

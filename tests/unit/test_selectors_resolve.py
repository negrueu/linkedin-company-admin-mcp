"""Selector constants vs synthetic fixtures.

We do NOT exercise Patchright here. We parse the fixtures with cheap
regex-based checks to confirm the constants in ``selectors/__init__.py``
still map onto the DOM we last captured.
"""

from __future__ import annotations

import re

import pytest

from tests.fixtures.loader import load


@pytest.fixture
def post_menu_html() -> str:
    return load("post_options_menu")


def _has_css_class(html: str, cls: str) -> bool:
    return re.search(rf'class="[^"]*\b{re.escape(cls)}\b', html) is not None


def test_option_delete_selector_matches_fixture(post_menu_html: str) -> None:
    # The delete_post flow clicks `li.option-delete > [role="button"]`.
    assert _has_css_class(post_menu_html, "option-delete")
    assert 'role="button"' in post_menu_html


def test_option_edit_selector_matches_fixture(post_menu_html: str) -> None:
    # Edit uses option-edit-share (not option-edit!) per RCA_DELETE_POST.
    assert _has_css_class(post_menu_html, "option-edit-share")


def test_confirm_dialog_matches(post_menu_html: str) -> None:
    assert 'role="dialog"' in post_menu_html
    assert 'aria-label="Delete post"' in post_menu_html


def test_schedule_dialog_has_date_time_inputs() -> None:
    html = load("schedule_dialog")
    assert 'id="schedule-date-input"' in html
    assert 'id="schedule-time-input"' in html
    assert "<button>Next</button>" in html
    assert 'aria-label="Schedule"' in html


def test_reshare_switcher_present() -> None:
    html = load("reshare_actor_switch")
    assert "share-unified-settings-entry-button" in html
    assert 'name="actor"' in html
    assert 'value="company"' in html
    assert "share-box-v2__modal" in html
    assert 'role="textbox"' in html


def test_edit_about_fields_have_stable_ids() -> None:
    html = load("edit_about_tab")
    for sel in [
        "organization-name-field",
        "organization-description-field",
        "organization-website-field",
        "organization-public-url-field",
        "organization-tagline-field",
    ]:
        assert f'id="{sel}"' in html


def test_edit_about_has_details_tab_selected() -> None:
    html = load("edit_about_tab")
    assert 'aria-selected="true"' in html
    assert ">Details<" in html

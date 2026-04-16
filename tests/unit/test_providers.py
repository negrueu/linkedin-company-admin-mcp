"""Provider abstraction surface."""

from __future__ import annotations

import inspect

import pytest

from linkedin_company_admin_mcp.providers.base import (
    AdminProvider,
    CreatePostRequest,
    DeletePostRequest,
    EditAboutRequest,
    EditLogoRequest,
    EditPostRequest,
    PostsProvider,
    ProviderResult,
    ReplyCommentRequest,
    ResharePostRequest,
    SchedulePostRequest,
    UpdateDetailsRequest,
)
from linkedin_company_admin_mcp.providers.browser_provider import (
    BrowserAdminProvider,
    BrowserPostsProvider,
)


def test_admin_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        AdminProvider()  # type: ignore[abstract]


def test_posts_provider_is_abstract() -> None:
    with pytest.raises(TypeError):
        PostsProvider()  # type: ignore[abstract]


class TestProviderResult:
    def test_success_with_extra(self) -> None:
        r = ProviderResult(ok=True, detail="ok", extra={"id": 1})
        assert r.ok
        assert r.extra == {"id": 1}

    def test_failure(self) -> None:
        r = ProviderResult(ok=False, detail="nope")
        assert not r.ok
        assert r.extra is None


class TestRequestDataclasses:
    """Each request dataclass keeps a stable field contract."""

    def test_edit_about_requires_text(self) -> None:
        req = EditAboutRequest(company_id="123", about_text="new")
        assert req.about_text == "new"

    def test_edit_logo_allows_single_path(self) -> None:
        req = EditLogoRequest(company_id="123", logo_path="/tmp/logo.png")
        assert req.banner_path is None

    def test_update_details_all_optional(self) -> None:
        req = UpdateDetailsRequest(company_id="123")
        assert req.website is None
        assert req.specialties is None

    def test_create_post_requires_text(self) -> None:
        assert CreatePostRequest(company_id="1", text="hi").text == "hi"

    def test_edit_post_urn_required(self) -> None:
        assert (
            EditPostRequest(company_id="1", post_urn="urn:li:activity:1", new_text="t").new_text
            == "t"
        )

    def test_delete_post_urn(self) -> None:
        assert DeletePostRequest(company_id="1", post_urn="urn:li:share:2").post_urn.startswith(
            "urn:"
        )

    def test_schedule_post_iso(self) -> None:
        req = SchedulePostRequest(
            company_id="1", text="t", scheduled_at_iso="2026-04-20T09:00:00+03:00"
        )
        assert "T" in req.scheduled_at_iso

    def test_reply_comment(self) -> None:
        req = ReplyCommentRequest(
            company_id="1", post_urn="urn:li:activity:1", comment_author_name="X", reply_text="Y"
        )
        assert req.reply_text == "Y"

    def test_reshare(self) -> None:
        assert (
            ResharePostRequest(company_id="1", source_post_urn="urn:li:activity:1").thoughts_text
            is None
        )


class TestBrowserPostsProviderValidation:
    """Pre-browser validation happens early enough to unit test."""

    async def test_edit_post_rejects_invalid_urn(self) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        bad = EditPostRequest(company_id="1", post_urn="not-a-urn", new_text="x")
        with pytest.raises(ValueError, match="Invalid post URN"):
            await provider.edit_post(bad)

    async def test_delete_post_rejects_invalid_urn(self) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        bad = DeletePostRequest(company_id="1", post_urn="garbage")
        with pytest.raises(ValueError, match="Invalid post URN"):
            await provider.delete_post(bad)

    async def test_schedule_post_requires_iso_with_time(self) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        bad = SchedulePostRequest(company_id="1", text="t", scheduled_at_iso="2026-04-20")
        with pytest.raises(ValueError, match="ISO 8601"):
            await provider.schedule_post(bad)

    async def test_reply_rejects_invalid_urn(self) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        bad = ReplyCommentRequest(
            company_id="1",
            post_urn="bad",
            comment_author_name="x",
            reply_text="y",
        )
        with pytest.raises(ValueError, match="Invalid post URN"):
            await provider.reply_to_comment(bad)

    async def test_reshare_rejects_invalid_urn(self) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        bad = ResharePostRequest(company_id="1", source_post_urn="nope")
        with pytest.raises(ValueError, match="Invalid source URN"):
            await provider.reshare_post(bad)


def test_browser_posts_provider_implements_all_methods() -> None:
    from linkedin_company_admin_mcp.providers.base import PostsProvider

    assert issubclass(BrowserPostsProvider, PostsProvider)
    for m in (
        "create_post",
        "edit_post",
        "delete_post",
        "schedule_post",
        "reply_to_comment",
        "reshare_post",
    ):
        assert inspect.iscoroutinefunction(getattr(BrowserPostsProvider, m))


def test_browser_admin_provider_signatures() -> None:
    """Admin provider has the exact 3 abstract methods implemented."""
    assert issubclass(BrowserAdminProvider, AdminProvider)
    methods = {"edit_about", "edit_logo", "update_details"}
    for m in methods:
        assert inspect.iscoroutinefunction(getattr(BrowserAdminProvider, m))

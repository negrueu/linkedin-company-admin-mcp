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


class TestBrowserPostsProviderStubs:
    """All 6 methods raise NotImplementedError until Faza 4."""

    @pytest.mark.parametrize(
        ("method_name", "request_obj"),
        [
            ("create_post", CreatePostRequest(company_id="1", text="t")),
            (
                "edit_post",
                EditPostRequest(company_id="1", post_urn="urn:li:activity:1", new_text="t"),
            ),
            ("delete_post", DeletePostRequest(company_id="1", post_urn="urn:li:activity:1")),
            (
                "schedule_post",
                SchedulePostRequest(
                    company_id="1", text="t", scheduled_at_iso="2026-04-20T09:00:00Z"
                ),
            ),
            (
                "reply_to_comment",
                ReplyCommentRequest(
                    company_id="1",
                    post_urn="urn:li:activity:1",
                    comment_author_name="x",
                    reply_text="y",
                ),
            ),
            (
                "reshare_post",
                ResharePostRequest(company_id="1", source_post_urn="urn:li:activity:1"),
            ),
        ],
    )
    async def test_stub_raises(self, method_name: str, request_obj: object) -> None:
        provider = BrowserPostsProvider(browser=None)  # type: ignore[arg-type]
        method = getattr(provider, method_name)
        assert inspect.iscoroutinefunction(method)
        with pytest.raises(NotImplementedError):
            await method(request_obj)


def test_browser_admin_provider_signatures() -> None:
    """Admin provider has the exact 3 abstract methods implemented."""
    assert issubclass(BrowserAdminProvider, AdminProvider)
    methods = {"edit_about", "edit_logo", "update_details"}
    for m in methods:
        assert inspect.iscoroutinefunction(getattr(BrowserAdminProvider, m))

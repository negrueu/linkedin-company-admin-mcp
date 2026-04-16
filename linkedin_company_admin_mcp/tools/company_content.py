"""Company Page content tools: create / edit / delete / schedule / reply / reshare."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.rate_limit import rate_limited
from linkedin_company_admin_mcp.error_handler import raise_tool_error
from linkedin_company_admin_mcp.providers.base import (
    CreatePostRequest,
    DeletePostRequest,
    EditPostRequest,
    ReplyCommentRequest,
    ResharePostRequest,
    SchedulePostRequest,
)
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider

GetBrowser = Callable[[], BrowserManager]


def register_company_content_tools(mcp: FastMCP[None], *, get_browser: GetBrowser) -> None:
    """Attach the 6 content-management tools."""

    @mcp.tool(
        title="Create company post",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "content"},
    )
    @rate_limited(key="company_create_post", max_per_hour=10)
    async def company_create_post(
        company_id: str,
        text: str,
        ctx: Context,
        link_url: str | None = None,
        image_path: str | None = None,
    ) -> dict[str, object]:
        """Publish a text post to the company page.

        Args:
            company_id: Numeric page ID or URL.
            text: Post body. Supports hashtags (``#AI``) and mentions
                inserted by hand as plain text - LinkedIn auto-links
                them on submission.
            link_url: Optional URL; LinkedIn auto-generates a preview card.
            image_path: Optional absolute path to a local image file.

        Returns:
            ``{ok: True, detail: str, extra: {has_link, has_image}}``.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.create_post(
                CreatePostRequest(
                    company_id=company_id,
                    text=text,
                    link_url=link_url,
                    image_path=image_path,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_create_post")

    @mcp.tool(
        title="Edit company post",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "content"},
    )
    @rate_limited(key="company_edit_post", max_per_hour=20)
    async def company_edit_post(
        company_id: str,
        post_urn: str,
        new_text: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Replace the body of an existing company post.

        Args:
            company_id: Numeric page ID or URL.
            post_urn: URN from ``company_list_posts``, e.g.
                ``"urn:li:activity:7123456789012345678"``.
            new_text: The replacement body.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.edit_post(
                EditPostRequest(company_id=company_id, post_urn=post_urn, new_text=new_text)
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_edit_post")

    @mcp.tool(
        title="Delete company post",
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": True,
        },
        tags={"company", "write", "content"},
    )
    @rate_limited(key="company_delete_post", max_per_hour=15)
    async def company_delete_post(
        company_id: str,
        post_urn: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Permanently delete a company post.

        This operation is irreversible. LinkedIn does not provide a trash
        or restore mechanism for company posts.

        Implementation note: the click sequence runs entirely through
        ``page.evaluate`` to bypass Playwright's actionability checks.
        See ``providers/shared.remove_blocking_modal_outlet`` for the
        root cause (phantom ``#artdeco-modal-outlet`` overlays).

        Args:
            company_id: Numeric page ID or URL.
            post_urn: URN of the post to delete (from ``company_list_posts``).
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.delete_post(
                DeletePostRequest(company_id=company_id, post_urn=post_urn)
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_delete_post")

    @mcp.tool(
        title="Schedule company post",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "content", "schedule"},
    )
    @rate_limited(key="company_schedule_post", max_per_hour=10)
    async def company_schedule_post(
        company_id: str,
        text: str,
        scheduled_at_iso: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Publish a post at a future date/time.

        Args:
            company_id: Numeric page ID or URL.
            text: Post body.
            scheduled_at_iso: ISO 8601 datetime with timezone, e.g.
                ``"2026-04-20T09:00:00+03:00"``. LinkedIn requires the time
                to be at least 10 minutes in the future and no further out
                than 3 months.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.schedule_post(
                SchedulePostRequest(
                    company_id=company_id,
                    text=text,
                    scheduled_at_iso=scheduled_at_iso,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_schedule_post")

    @mcp.tool(
        title="Reply to comment as company",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "content"},
    )
    @rate_limited(key="company_reply_comment", max_per_hour=30)
    async def company_reply_comment(
        company_id: str,
        post_urn: str,
        comment_author_name: str,
        reply_text: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Reply as the company to a comment on one of its posts.

        Args:
            company_id: Numeric page ID or URL.
            post_urn: URN of the post whose comment you are replying to.
            comment_author_name: Case-insensitive substring of the comment
                author's display name; the first matching comment is used.
            reply_text: The reply body.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.reply_to_comment(
                ReplyCommentRequest(
                    company_id=company_id,
                    post_urn=post_urn,
                    comment_author_name=comment_author_name,
                    reply_text=reply_text,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_reply_comment")

    @mcp.tool(
        title="Reshare post to company page",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "content"},
    )
    @rate_limited(key="company_reshare_post", max_per_hour=10)
    async def company_reshare_post(
        company_id: str,
        source_post_urn: str,
        ctx: Context,
        thoughts_text: str | None = None,
    ) -> dict[str, object]:
        """Reshare another post on the company page, optionally with commentary.

        Args:
            company_id: Numeric page ID or URL. Required even though the
                page posts the reshare; used to validate admin context.
            source_post_urn: URN of the post being reshared.
            thoughts_text: Optional leading commentary.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserPostsProvider(browser)
            result = await provider.reshare_post(
                ResharePostRequest(
                    company_id=company_id,
                    source_post_urn=source_post_urn,
                    thoughts_text=thoughts_text,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_reshare_post")


__all__ = ["register_company_content_tools"]

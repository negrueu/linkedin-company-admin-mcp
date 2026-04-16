"""Provider abstract base classes.

The write path goes through a provider so we can add a LinkedIn
Community Management API implementation later without rewriting the
tools. Current concrete implementation is ``BrowserProvider`` (Patchright).

A provider receives a ``BrowserManager`` at construction time and never
calls ``raise_tool_error`` directly - it raises typed exceptions from
``core.exceptions``. The tool layer wraps into MCP errors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class EditAboutRequest:
    company_id: str
    about_text: str


@dataclass(slots=True)
class EditLogoRequest:
    company_id: str
    logo_path: str | None = None
    banner_path: str | None = None


@dataclass(slots=True)
class UpdateDetailsRequest:
    company_id: str
    website: str | None = None
    industry: str | None = None
    size_range: str | None = None
    specialties: list[str] | None = None


@dataclass(slots=True)
class ProviderResult:
    """Uniform success response."""

    ok: bool
    detail: str
    extra: dict[str, object] | None = None


class AdminProvider(ABC):
    """Write operations on the company page details."""

    @abstractmethod
    async def edit_about(self, request: EditAboutRequest) -> ProviderResult: ...

    @abstractmethod
    async def edit_logo(self, request: EditLogoRequest) -> ProviderResult: ...

    @abstractmethod
    async def update_details(self, request: UpdateDetailsRequest) -> ProviderResult: ...


@dataclass(slots=True)
class CreatePostRequest:
    company_id: str
    text: str
    link_url: str | None = None
    image_path: str | None = None


@dataclass(slots=True)
class EditPostRequest:
    company_id: str
    post_urn: str
    new_text: str


@dataclass(slots=True)
class DeletePostRequest:
    company_id: str
    post_urn: str


@dataclass(slots=True)
class SchedulePostRequest:
    company_id: str
    text: str
    scheduled_at_iso: str  # ISO 8601 with timezone


@dataclass(slots=True)
class ReplyCommentRequest:
    company_id: str
    post_urn: str
    comment_author_name: str
    reply_text: str


@dataclass(slots=True)
class ResharePostRequest:
    company_id: str
    source_post_urn: str
    thoughts_text: str | None = None


class PostsProvider(ABC):
    """Write operations on company posts."""

    @abstractmethod
    async def create_post(self, request: CreatePostRequest) -> ProviderResult: ...

    @abstractmethod
    async def edit_post(self, request: EditPostRequest) -> ProviderResult: ...

    @abstractmethod
    async def delete_post(self, request: DeletePostRequest) -> ProviderResult: ...

    @abstractmethod
    async def schedule_post(self, request: SchedulePostRequest) -> ProviderResult: ...

    @abstractmethod
    async def reply_to_comment(self, request: ReplyCommentRequest) -> ProviderResult: ...

    @abstractmethod
    async def reshare_post(self, request: ResharePostRequest) -> ProviderResult: ...

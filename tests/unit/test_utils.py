"""URN parsing and misc helpers."""

from __future__ import annotations

from linkedin_company_admin_mcp.core.utils import (
    extract_activity_urn,
    is_valid_urn,
    normalise_company_id,
)


class TestIsValidUrn:
    def test_activity(self) -> None:
        assert is_valid_urn("urn:li:activity:1234567890")

    def test_ugc_post(self) -> None:
        assert is_valid_urn("urn:li:ugcPost:abcDEF123")

    def test_share(self) -> None:
        assert is_valid_urn("urn:li:share:1234")

    def test_organization(self) -> None:
        assert is_valid_urn("urn:li:organization:106949933")

    def test_rejects_unknown_type(self) -> None:
        assert not is_valid_urn("urn:li:mystery:123")

    def test_rejects_garbage(self) -> None:
        assert not is_valid_urn("not a urn")

    def test_rejects_empty(self) -> None:
        assert not is_valid_urn("")


class TestExtractActivityUrn:
    def test_from_bare_urn(self) -> None:
        assert extract_activity_urn("urn:li:activity:7123") == "urn:li:activity:7123"

    def test_from_data_urn_attribute(self) -> None:
        html = '<div data-urn="urn:li:activity:998877">body</div>'
        assert extract_activity_urn(html) == "urn:li:activity:998877"

    def test_from_ugc_post(self) -> None:
        assert extract_activity_urn("url?urn=urn:li:ugcPost:42") == "urn:li:ugcPost:42"

    def test_returns_none_when_missing(self) -> None:
        assert extract_activity_urn("no urn in this string") is None


class TestNormaliseCompanyId:
    def test_numeric(self) -> None:
        assert normalise_company_id("106949933") == "106949933"

    def test_full_admin_url(self) -> None:
        assert (
            normalise_company_id("https://www.linkedin.com/company/106949933/admin/dashboard/")
            == "106949933"
        )

    def test_slug_url(self) -> None:
        assert normalise_company_id("https://www.linkedin.com/company/ketu-ai/") == "ketu-ai"

    def test_unknown_passthrough(self) -> None:
        assert normalise_company_id("ketu-ai") == "ketu-ai"

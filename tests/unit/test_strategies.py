"""Parsing strategies."""

from __future__ import annotations

from linkedin_company_admin_mcp.selectors.strategies import (
    extract_followers_count,
    is_empty_state,
    parse_abbreviated_count,
    parse_after_marker,
)


class TestParseAbbreviatedCount:
    def test_plain_integer(self) -> None:
        assert parse_abbreviated_count("1234") == 1234

    def test_comma_separated(self) -> None:
        assert parse_abbreviated_count("1,234") == 1234

    def test_k_suffix(self) -> None:
        assert parse_abbreviated_count("5.4K") == 5400

    def test_m_suffix(self) -> None:
        assert parse_abbreviated_count("2M followers") == 2_000_000

    def test_b_suffix(self) -> None:
        assert parse_abbreviated_count("1.5B") == 1_500_000_000

    def test_no_match(self) -> None:
        assert parse_abbreviated_count("no number here") is None

    def test_lowercase_suffix(self) -> None:
        assert parse_abbreviated_count("3.2k") == 3200


class TestExtractFollowersCount:
    def test_small_number(self) -> None:
        assert extract_followers_count("KETU AI SRL 1 follower") == 1

    def test_large_abbreviated(self) -> None:
        assert extract_followers_count("Acme 1.2K followers - 10 employees") == 1200

    def test_no_followers_phrase(self) -> None:
        assert extract_followers_count("no relevant text") is None


class TestParseAfterMarker:
    def test_marker_found(self) -> None:
        text = "Author Name\nHeadline here\nFollow\nBody of post"
        assert parse_after_marker(text, "Follow") == "Body of post"

    def test_marker_missing(self) -> None:
        assert parse_after_marker("no marker", "Follow") is None

    def test_skips_empty_lines(self) -> None:
        text = "A\nB\nFollow\n\n   \nReal body"
        assert parse_after_marker(text, "Follow") == "Real body"

    def test_min_length_filter(self) -> None:
        text = "A\nFollow\n1\nReal content"
        assert parse_after_marker(text, "Follow", min_length=3) == "Real content"


class TestIsEmptyState:
    def test_matches_marker(self) -> None:
        assert is_empty_state("Sorry, no posts yet.", ("No posts yet",))

    def test_case_insensitive(self) -> None:
        assert is_empty_state("NO NOTIFICATIONS", ("No notifications",))

    def test_does_not_match(self) -> None:
        assert not is_empty_state("Has 5 posts", ("No posts yet",))

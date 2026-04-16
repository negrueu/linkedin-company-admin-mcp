"""Server factory wires tools correctly."""

from __future__ import annotations

from linkedin_company_admin_mcp.config.schema import AppConfig
from linkedin_company_admin_mcp.server import create_mcp_server


async def test_server_registers_all_tools() -> None:
    """The MCP server must expose the expected tool set for Faza 2."""
    mcp = create_mcp_server(AppConfig())
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    expected = {
        # session
        "session_status",
        "session_warmup",
        "session_logout",
        # company read
        "company_read_page",
        "company_list_posts",
        "company_list_followers",
        "company_list_mentions",
        "company_manage_admins",
        "company_analytics",
        # company admin write
        "company_edit_about",
        "company_edit_logo",
        "company_update_details",
        # company content
        "company_create_post",
        "company_edit_post",
        "company_delete_post",
        "company_schedule_post",
        "company_reply_comment",
        "company_reshare_post",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"


async def test_server_has_expected_name_and_version() -> None:
    mcp = create_mcp_server(AppConfig())
    assert mcp.name == "linkedin-company-admin-mcp"

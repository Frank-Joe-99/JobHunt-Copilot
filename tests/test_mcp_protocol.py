"""
MCP 协议标准与安全性测试 (Protocol & Safety Tests)
涵盖：stdio 握手、工具发现、输入 Schema 约束、注解验证、资源脱敏与越权防御。
"""
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_mcp_initialize_and_tools_count(mcp_server_params):
    """测试 stdio 握手及 13 个业务工具注册"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.server_info.name == "jobhunt-copilot"

            tools_res = await session.list_tools()
            tools_map = {t.name: t for t in tools_res.tools}

            assert len(tools_res.tools) == 13

            # 验证涵盖的核心工具
            expected_tools = [
                "tool_generate_resume",
                "tool_analyze_jd",
                "tool_recommend_projects",
                "tool_one_click_tailor",
                "tool_track_application",
                "tool_get_upcoming_schedules",
                "tool_get_funnel_analytics",
                "tool_diagnose_ats",
                "tool_polish_experiences",
                "tool_scan_jds",
                "tool_interview_start",
                "tool_interview_answer",
                "tool_interview_finish",
            ]
            for name in expected_tools:
                assert name in tools_map, f"缺少预期工具: {name}"


@pytest.mark.asyncio
async def test_mcp_tool_schema_and_annotations(mcp_server_params):
    """测试状态枚举 Schema 与 ToolAnnotations"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_res = await session.list_tools()
            tools_map = {t.name: t for t in tools_res.tools}

            # 1. 验证 tool_track_application 的 status 为枚举
            track_tool = tools_map["tool_track_application"]
            status_schema = track_tool.input_schema.get("properties", {}).get("status", {})
            assert "enum" in status_schema
            assert set(status_schema["enum"]) == {
                "wishlist", "applied", "assessment",
                "interview_1", "interview_2", "hr_stage",
                "offer", "rejected", "closed"
            }

            # 2. 验证 tool_one_click_tailor 的默认值
            tailor_tool = tools_map["tool_one_click_tailor"]
            tailor_props = tailor_tool.input_schema.get("properties", {})
            assert tailor_props.get("auto_track", {}).get("default") is False
            assert tailor_props.get("enable_github", {}).get("default") is True

            # 3. 验证工具注解
            assert tools_map["tool_get_funnel_analytics"].annotations.read_only_hint is True
            assert tools_map["tool_get_upcoming_schedules"].annotations.read_only_hint is True
            assert tools_map["tool_analyze_jd"].annotations.open_world_hint is True
            assert tools_map["tool_generate_resume"].annotations.read_only_hint is False


@pytest.mark.asyncio
async def test_mcp_resource_sanitization(mcp_server_params):
    """测试 profile://summary 资源暴露及隐私脱敏"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            resources = await session.list_resources()
            uris = [str(r.uri) for r in resources.resources]
            assert "profile://summary" in uris

            res = await session.read_resource("profile://summary")
            content_json = json.loads(res.contents[0].text)

            # 严格脱敏断言：手机、邮箱、身份证绝对不能暴露
            basics = content_json.get("basics", {})
            assert "phone" not in basics
            assert "email" not in basics
            assert "id_card" not in basics
            assert "address" not in basics


@pytest.mark.asyncio
async def test_mcp_security_path_traversal(mcp_server_params):
    """测试 tool_scan_jds 针对越权路径的强制安全拦截"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 越权访问项目外目录
            res = await session.call_tool("tool_scan_jds", {"directory": "../../../windows/system32"})
            assert res.is_error is True
            assert "安全违规" in res.content[0].text or "Error executing tool" in res.content[0].text


@pytest.mark.asyncio
async def test_mcp_error_propagation_is_error(mcp_server_params):
    """测试错误在 MCP 层被正确标记为 is_error=True"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 传入不存在的 record_id
            res = await session.call_tool("tool_track_application", {
                "company": "Test",
                "role": "QA",
                "record_id": 99999999,
            })
            assert res.is_error is True

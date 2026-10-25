"""
MCP 业务工具执行与离线能力测试 (Tools Execution Tests)
"""
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_tool_funnel_and_schedules(mcp_server_params):
    """测试漏斗统计与日程查询工具"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            res_funnel = await session.call_tool("tool_get_funnel_analytics", {})
            assert res_funnel.is_error is False
            funnel_data = json.loads(res_funnel.content[0].text)
            assert "total_count" in funnel_data
            assert "status_distribution" in funnel_data

            res_sched = await session.call_tool("tool_get_upcoming_schedules", {"days_ahead": 14})
            assert res_sched.is_error is False
            sched_data = json.loads(res_sched.content[0].text)
            assert isinstance(sched_data, list)


@pytest.mark.asyncio
async def test_tool_track_application_lifecycle(mcp_server_params):
    """测试投递看板增删改查生命周期"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. 登记新投递
            res_add = await session.call_tool("tool_track_application", {
                "company": "Pytest测试企业",
                "role": "Python后端开发",
                "status": "applied",
                "salary_range": "20-25K",
                "location": "北京",
                "note": "自动化测试记录",
            })
            assert res_add.is_error is False
            record = json.loads(res_add.content[0].text)
            rec_id = record["id"]
            assert record["company"] == "Pytest测试企业"
            assert record["status"] == "applied"

            # 2. 推进状态为 interview_1 并预约时间
            res_update = await session.call_tool("tool_track_application", {
                "company": "Pytest测试企业",
                "role": "Python后端开发",
                "record_id": rec_id,
                "status": "interview_1",
                "next_schedule_time": "2026-10-25 15:00",
                "next_schedule_notes": "技术一面",
            })
            assert res_update.is_error is False
            updated = json.loads(res_update.content[0].text)
            assert updated["id"] == rec_id
            assert updated["status"] == "interview_1"
            assert updated["next_schedule_notes"] == "技术一面"


@pytest.mark.asyncio
async def test_tool_generate_resume_pure_local(mcp_server_params):
    """测试本地双格式简历排版（验证协议完全无 stdout 坏行污染）"""
    async with stdio_client(mcp_server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            res = await session.call_tool("tool_generate_resume", {
                "template": "modern",
                "output_name": "pytest_test_resume",
            })
            assert res.is_error is False
            data = json.loads(res.content[0].text)
            assert data["status"] == "success"
            assert Path(data["pdf_path"]).exists()
            assert Path(data["docx_path"]).exists()

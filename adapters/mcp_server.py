"""
JobHunt-Copilot Model Context Protocol (MCP) 服务端
基于 Anthropic MCP 协议标准搭建，赋予系统与 Claude Desktop、Cursor、VS Code 等主流宿主环境的无缝互操作能力。
外部 AI 助手可通过调用本服务端暴露的 Tools，直接执行简历生成、JD深度比对、开源推荐、一键定向投递与日程看板管理。
"""

import json
import sys
from pathlib import Path

# 确保在任何外部调用环境下均能正确引入项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from mcp.server.mcpserver import MCPServer
    mcp_app = MCPServer(
        name="jobhunt-copilot",
        description="JobHunt-Copilot 智能求职赋能套件：简历排版、JD穿透匹配、开源实战项目推荐、一键定向全套交付与投递日程看板。",
    )
except ImportError:
    from mcp.server.fastmcp import FastMCP
    mcp_app = FastMCP(
        name="jobhunt-copilot",
        description="JobHunt-Copilot 智能求职赋能套件",
    )


@mcp_app.tool()
def tool_generate_resume(
    template: str = "modern",
    output_name: str = "resume_default",
) -> str:
    """
    根据本地求职者主档案 (config/profile.yaml)，排版并编译输出高质量 PDF 与 Word (docx) 双格式简历。

    Args:
        template: 简历视觉主题模板，支持 'modern'（现代专业风）或 'minimal'（极简学术风）
        output_name: 输出文件基本名称（无需后缀）
    """
    try:
        from skills.resume_generator import generate_resume
        paths = generate_resume(template=template, output_name=output_name)
        return json.dumps(
            {
                "status": "success",
                "message": "双格式简历编译成功！",
                "pdf_path": str(paths["pdf"].resolve()),
                "docx_path": str(paths["docx"].resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_analyze_jd(
    jd_text: str,
    provider: str | None = None,
) -> str:
    """
    深度穿透解析目标企业招聘 JD，与求职者画像进行全维度技术契合度打分，列出技能匹配点、短板缺口及量身定制的自荐信草稿。

    Args:
        jd_text: 目标岗位的招聘 JD 纯文本或包含岗位要求的描述
        provider: 可选的大模型供应商 (如 deepseek/aliyun/custom)
    """
    try:
        from skills.jd_matcher import parse_jd, match_profile_with_jd
        from core.config import load_user_profile

        profile = load_user_profile()
        parsed_jd = parse_jd(jd_text, provider=provider)
        match_result = match_profile_with_jd(profile, parsed_jd, provider=provider)

        return json.dumps(
            {
                "status": "success",
                "target_company": parsed_jd.company,
                "target_role": parsed_jd.role,
                "match_score": match_result.score,
                "matched_skills": [m.model_dump() for m in match_result.matched_skills],
                "missing_skills": [g.model_dump() for g in match_result.missing_skills],
                "tuning_advice": match_result.resume_tuning_advice,
                "cover_letter_draft": match_result.cover_letter_draft,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_recommend_projects(
    skills: list[str],
    language: str = "python",
    provider: str | None = None,
) -> str:
    """
    针对技能短板（如 Kafka, K8s, Redis, 分布式存储等），检索 GitHub 高价值开源实战项目，并由大模型提供极简速成学习路线与简历 STAR 范文。

    Args:
        skills: 待攻坚的技能关键词列表，例如 ["Kafka", "Redis"]
        language: 偏好的主语言（默认 python）
        provider: 可选的大模型供应商
    """
    try:
        from skills.project_recommender import recommend_projects_report
        from core.state import SkillGap

        gaps = [SkillGap(skill=s, status="missing", suggestion="需要补充工业级实战经验") for s in skills]
        report = recommend_projects_report(skills_gaps=gaps, language=language, provider=provider)
        return report.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_one_click_tailor(
    jd_text: str,
    auto_track: bool = True,
    provider: str | None = None,
) -> str:
    """
    【一键岗位定向全套交付流】输入目标岗位招聘 JD，端到端自动完成：
    JD深度比对 ➔ 开源项目补强 ➔ 重点经历 STAR 强化 ➔ 编译专属双格式简历 ➔ 生成投递战报 ➔ 自动登记入库跟踪（防腐零污染）。

    Args:
        jd_text: 目标岗位的招聘 JD 纯文本或文件路径
        auto_track: 是否在生成定制简历后自动将其登记到投递看板（默认 True）
        provider: 可选的大模型供应商
    """
    try:
        from core.workflow import tailor_application_flow

        package = tailor_application_flow(
            jd_input=jd_text,
            auto_track=auto_track,
            provider=provider,
        )
        return json.dumps(
            {
                "status": "success",
                "target_company": package.target_company,
                "target_role": package.target_role,
                "match_score": package.match_result.score,
                "pdf_resume": package.resume_files.get("pdf", ""),
                "docx_resume": package.resume_files.get("docx", ""),
                "package_report_path": package.package_report_path,
                "cover_letter_draft": package.match_result.cover_letter_draft,
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_track_application(
    company: str,
    role: str,
    status: str = "applied",
    record_id: int | None = None,
    next_schedule_time: str | None = None,
    next_schedule_notes: str | None = None,
    salary_range: str | None = None,
    location: str | None = None,
    note: str | None = None,
) -> str:
    """
    求职投递看板管理：登记新投递记录，或根据 record_id 推进已有求职流程阶段（如更新为一面/预约面试时间/录入复盘笔记）。

    Args:
        company: 企业名称（如：字节跳动）
        role: 岗位名称（如：后端开发工程师）
        status: 投递状态 (wishlist / applied / assessment / interview_1 / interview_2 / hr_stage / offer / rejected / closed)
        record_id: 若提供已有记录 ID 则执行状态更新与日程录入；若不传则创建新投递
        next_schedule_time: 下一次面试或笔试时间（如 "2026-09-28 14:00"）
        next_schedule_notes: 日程备忘（如 "飞书会议号 123-456-789"）
        salary_range: 薪资预期或待遇范围
        location: 工作城市
        note: 本次状态变更或面试复盘备忘流水
    """
    try:
        from skills.application_tracker import add_application, update_status
        from core.state import ApplicationStatus

        if record_id:
            updated = update_status(
                record_id=record_id,
                status=status,
                next_schedule_time=next_schedule_time,
                next_schedule_notes=next_schedule_notes,
                salary_range=salary_range,
                location=location,
                note=note,
            )
            if not updated:
                return json.dumps({"status": "error", "error": f"未找到 ID 为 {record_id} 的投递记录"}, ensure_ascii=False)
            return updated.model_dump_json(indent=2)
        else:
            created = add_application(
                company=company,
                role=role,
                status=status,
                salary_range=salary_range,
                location=location,
                next_schedule_time=next_schedule_time,
                next_schedule_notes=next_schedule_notes,
                note=note,
            )
            return created.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_get_upcoming_schedules(days_ahead: int = 7) -> str:
    """
    查询未来若干天内（默认 7 天）以及近 3 天未关闭的笔试与面试待办日程提醒及倒计时。

    Args:
        days_ahead: 检索未来多少天内的日程（默认 7 天）
    """
    try:
        from skills.application_tracker import get_upcoming_schedules

        events = get_upcoming_schedules(days_ahead=days_ahead)
        return json.dumps([e.model_dump() for e in events], ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


@mcp_app.tool()
def tool_get_funnel_analytics() -> str:
    """
    获取当前个人求职全流程转化漏斗统计（投递总量、正式投递量、笔试数、进面数、Offer数、进面率%、Offer转化率%及各阶段分布）。
    """
    try:
        from skills.application_tracker import get_funnel_analytics

        stats = get_funnel_analytics()
        return stats.model_dump_json(indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def main():
    """以标准 stdio 协议启动 MCP 服务端"""
    mcp_app.run(transport="stdio")


if __name__ == "__main__":
    main()

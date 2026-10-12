"""
JobHunt-Copilot Model Context Protocol (MCP) 服务端
基于 Anthropic MCP 协议标准搭建，赋予系统与 Claude Desktop、Cursor、VS Code 等主流宿主环境的无缝互操作能力。
外部 AI 助手可通过调用本服务端暴露的 Tools，直接执行简历生成、JD深度比对、开源推荐、一键定向投递、日程看板管理、ATS诊断、STAR润色、批量岗位雷达与模拟面试。
"""

import contextlib
import functools
import inspect
import json
import logging
import sys
from pathlib import Path
from typing import Literal

# 确保在任何外部调用环境下均能正确引入项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import anyio
from mcp.server.mcpserver import MCPServer, Context
from mcp.types import ToolAnnotations

APPLICATION_STATUS_VALUES = Literal[
    "wishlist", "applied", "assessment",
    "interview_1", "interview_2", "hr_stage",
    "offer", "rejected", "closed"
]

INTERVIEW_ROLE_VALUES = Literal[
    "strict_architect", "practical_lead", "hrbp"
]

logger = logging.getLogger(__name__)

mcp_app = MCPServer(
    name="jobhunt-copilot",
    description="JobHunt-Copilot 智能求职赋能套件：简历排版、JD穿透匹配、开源实战项目推荐、一键定向全套交付、投递日程看板、ATS体检、STAR润色与模拟面试。",
)

# 内存会话管理：模拟面试多轮状态机缓存
_interview_sessions: dict[str, object] = {}


def _mcp_tool_safe(func):
    """Decorator: redirect stdout→stderr during tool execution to protect JSON-RPC stdio.
    支持同步与异步协程函数。
    """
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with contextlib.redirect_stdout(sys.stderr):
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with contextlib.redirect_stdout(sys.stderr):
                return func(*args, **kwargs)
        return sync_wrapper


# ==========================================
# 核心求职物料生成与匹配工具 (P0-P2)
# ==========================================

@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, open_world_hint=False))
@_mcp_tool_safe
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


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
@_mcp_tool_safe
def tool_analyze_jd(
    jd_text: str,
    provider: str | None = None,
) -> str:
    """
    深度穿透解析目标企业招聘 JD，与求职者画像进行全维度技术契合度打分，列出技能匹配点、短板缺口及量身定制的自荐信草稿。

    Args:
        jd_text: 目标岗位的招聘 JD 纯文本或包含岗位要求的描述
        provider: 可选的大模型供应商 (如 deepseek/aliyun/custom)

    ⚠️ 隐私提示：本工具会将 JD 文本与求职者档案摘要发送至外部大模型服务进行分析。
    """
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


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
@_mcp_tool_safe
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

    ⚠️ 隐私提示：本工具会调用 GitHub API 检索仓库，并将技能信息发送至外部大模型进行评估。
    """
    from skills.project_recommender import recommend_projects_report
    from core.state import SkillGap

    gaps = [SkillGap(skill=s, status="missing", suggestion="需要补充工业级实战经验") for s in skills]
    report = recommend_projects_report(skills_gaps=gaps, language=language, provider=provider)
    return report.model_dump_json(indent=2)


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True))
@_mcp_tool_safe
async def tool_one_click_tailor(
    jd_text: str,
    auto_track: bool = False,
    enable_github: bool = True,
    provider: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    【一键岗位定向全套交付流】输入目标岗位招聘 JD，端到端自动完成：
    JD深度比对 ➔ 开源项目补强 ➔ 重点经历 STAR 强化 ➔ 编译专属双格式简历 ➔ 生成投递战报 ➔ 自动登记入库跟踪（防腐零污染）。
    本工具为非阻塞长任务，支持实时向宿主上报 5 个阶段的执行进度。

    Args:
        jd_text: 目标岗位的招聘 JD 纯文本或文件路径
        auto_track: 是否在生成定制简历后自动将其登记到投递看板（默认 False，不自动写入看板）
        enable_github: 是否针对技能短板检索 GitHub 开源实战项目（默认 True）
        provider: 可选的大模型供应商

    ⚠️ 隐私提示：本工具会将 JD 与求职者档案发送至外部大模型服务，并可能调用 GitHub API。
    """
    from core.workflow import tailor_application_flow

    def _sync_flow():
        def _on_progress(step: int, total: int, msg: str):
            if ctx:
                try:
                    anyio.from_thread.run(ctx.report_progress, float(step), float(total), msg)
                except Exception:
                    pass

        return tailor_application_flow(
            jd_input=jd_text,
            auto_track=auto_track,
            enable_github_search=enable_github,
            provider=provider,
            progress_callback=_on_progress,
        )

    package = await anyio.to_thread.run_sync(_sync_flow)

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


# ==========================================
# 投递看板与日程工具 (P0-P1)
# ==========================================

@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False))
@_mcp_tool_safe
def tool_track_application(
    company: str,
    role: str,
    status: APPLICATION_STATUS_VALUES = "applied",
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
            raise ValueError(f"未找到 ID 为 {record_id} 的投递记录")
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


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
@_mcp_tool_safe
def tool_get_upcoming_schedules(days_ahead: int = 7) -> str:
    """
    查询未来若干天内（默认 7 天）以及近 3 天未关闭的笔试与面试待办日程提醒及倒计时。

    Args:
        days_ahead: 检索未来多少天内的日程（默认 7 天）
    """
    from skills.application_tracker import get_upcoming_schedules

    events = get_upcoming_schedules(days_ahead=days_ahead)
    return json.dumps([e.model_dump() for e in events], ensure_ascii=False, indent=2)


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
@_mcp_tool_safe
def tool_get_funnel_analytics() -> str:
    """
    获取当前个人求职全流程转化漏斗统计（投递总量、正式投递量、笔试数、进面数、Offer数、进面率%、Offer转化率%及各阶段分布）。
    """
    from skills.application_tracker import get_funnel_analytics

    stats = get_funnel_analytics()
    return stats.model_dump_json(indent=2)


# ==========================================
# P3 能力补全：ATS诊断、STAR润色与岗位雷达
# ==========================================

@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
@_mcp_tool_safe
def tool_diagnose_ats(
    target_jd_text: str | None = None,
    provider: str | None = None,
) -> str:
    """
    对本地简历档案进行 ATS 关键词覆盖率、结构规范性与量化指标深度体检打分。
    支持输入对标岗位 JD（如不提供则按互联网大厂通用 ATS 标准体检）。

    Args:
        target_jd_text: 可选的目标岗位招聘 JD 文本
        provider: 可选的大模型供应商

    ⚠️ 隐私提示：本工具会将候选人简历档案摘要发送至外部大模型进行体检评估。
    """
    from skills.resume_polisher import diagnose_ats

    report = diagnose_ats(target_jd_text=target_jd_text, provider=provider)
    return report.model_dump_json(indent=2)


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True))
@_mcp_tool_safe
def tool_polish_experiences(
    provider: str | None = None,
) -> str:
    """
    基于 STAR 法则（情境/任务/行动/结果）对简历中的实习经历、项目经历与科研经历进行深度润色强化。
    遵守事实准则：仅重构表达与突出技术难点，严禁捏造未经发生的虚假指标或项目成果。

    Args:
        provider: 可选的大模型供应商

    ⚠️ 隐私提示：本工具会将候选人经历亮点描述发送至外部大模型进行重写润色。
    """
    from skills.resume_polisher import polish_experiences

    report = polish_experiences(provider=provider)
    return report.model_dump_json(indent=2)


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, open_world_hint=True))
@_mcp_tool_safe
def tool_scan_jds(
    directory: str = "storage/raw_jds",
    provider: str | None = None,
) -> str:
    """
    全网/本地批量岗位机会雷达扫描：从指定文件夹批量读取岗位 JD 文本，执行契合度排名、提炼共性技术短板并导出战略简报。

    安全限制：目录必须位于项目安全工作区内，禁止跨目录越权访问。

    Args:
        directory: 存放 .txt 格式 JD 文件的文件夹相对路径（默认 storage/raw_jds）
        provider: 可选的大模型供应商

    ⚠️ 隐私提示：批量扫描过程会将 JD 文本与用户档案发送至外部大模型进行匹配打分。
    """
    target_dir = Path(directory)
    if not target_dir.is_absolute():
        target_dir = (PROJECT_ROOT / target_dir).resolve()
    else:
        target_dir = target_dir.resolve()

    if not target_dir.is_relative_to(PROJECT_ROOT):
        raise ValueError(f"安全违规：仅允许扫描项目内部安全目录，拒绝跨目录访问: {directory}")

    from skills.job_radar import run_radar_pipeline

    report = run_radar_pipeline(dir_path=target_dir, provider=provider)
    return report.model_dump_json(indent=2)


# ==========================================
# P3 能力补全：AI 场景化模拟面试官
# ==========================================

@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, open_world_hint=True))
@_mcp_tool_safe
def tool_interview_start(
    target_company: str = "目标大厂",
    target_role: str = "后端开发工程师",
    interviewer_role: INTERVIEW_ROLE_VALUES = "strict_architect",
    provider: str | None = None,
) -> str:
    """
    初始化一场沉浸式 AI 模拟面试会话。
    面试官将根据候选人档案、目标企业岗位及所选人设（硬核架构师/实战带教Leader/HRBP）生成开场破冰提问。

    Args:
        target_company: 目标面试企业（如 字节跳动、腾讯、阿里巴巴）
        target_role: 目标应聘岗位（如 后端开发工程师、AI Infra 研究员）
        interviewer_role: 面试官人设 (strict_architect: 硬核架构师 / practical_lead: 实战带教组长 / hrbp: 敏锐HRBP)
        provider: 可选的大模型供应商

    Returns:
        JSON 包含 session_id、面试官第一句开场白及当前阶段
    """
    from skills.mock_interviewer import start_interview
    from core.state import InterviewRole

    role_enum = InterviewRole(interviewer_role)
    session, stream = start_interview(
        target_role=target_role,
        target_company=target_company,
        role=role_enum,
        provider=provider,
    )

    opening_question = "".join(list(stream)).strip()
    _interview_sessions[session.session_id] = session

    return json.dumps(
        {
            "status": "success",
            "session_id": session.session_id,
            "target_company": target_company,
            "target_role": target_role,
            "interviewer_role": interviewer_role,
            "current_stage": session.current_stage.value,
            "opening_question": opening_question,
            "message": "模拟面试已开启，请调用 tool_interview_answer 进行作答交互。",
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, open_world_hint=True))
@_mcp_tool_safe
def tool_interview_answer(
    session_id: str,
    user_answer: str,
    provider: str | None = None,
) -> str:
    """
    向正在进行的模拟面试提交回答。
    面试官将针对应答进行原理深挖、技术追问或驱动状态机推演进入下一阶段（自我介绍->项目深挖->八股场景->反问收尾）。
    用户亦可输入快捷指令：'next'（跳过当前环节）或 'finish'（申请提前结束面试）。

    Args:
        session_id: 面试会话 ID（由 tool_interview_start 返回）
        user_answer: 候选人的回答文本或快捷指令
        provider: 可选的大模型供应商
    """
    session = _interview_sessions.get(session_id)
    if not session:
        raise ValueError(f"未找到 ID 为 '{session_id}' 的活跃面试会话，可能已结束或未初始化。")

    from skills.mock_interviewer import step_interview_stream

    stream = step_interview_stream(
        session=session,
        user_answer=user_answer,
        provider=provider,
    )
    interviewer_reply = "".join(list(stream)).strip()

    return json.dumps(
        {
            "status": "success",
            "session_id": session_id,
            "current_stage": session.current_stage.value,
            "is_finished": session.is_finished,
            "interviewer_reply": interviewer_reply,
            "turns_count": len(session.history),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp_app.tool(annotations=ToolAnnotations(read_only_hint=False, open_world_hint=True))
@_mcp_tool_safe
def tool_interview_finish(
    session_id: str,
    provider: str | None = None,
) -> str:
    """
    终结指定的模拟面试会话，驱动大模型出具全维度复盘体检报告（六维能力打分、亮点与失分点、满分范例）并持久化落盘为 Markdown 文件。

    Args:
        session_id: 面试会话 ID
        provider: 可选的大模型供应商
    """
    session = _interview_sessions.get(session_id)
    if not session:
        raise ValueError(f"未找到 ID 为 '{session_id}' 的面试会话。")

    from skills.mock_interviewer import finish_interview

    report, report_path = finish_interview(session=session, provider=provider)
    _interview_sessions.pop(session_id, None)

    return json.dumps(
        {
            "status": "success",
            "session_id": session_id,
            "overall_score": report.overall_score,
            "result": report.result,
            "summary": report.summary,
            "dimension_scores": report.dimension_scores,
            "highlights": report.highlights,
            "weaknesses": report.weaknesses,
            "report_file_path": str(report_path.resolve()),
        },
        ensure_ascii=False,
        indent=2,
    )


# ==========================================
# P3 MCP 资源暴露 (Resources)
# ==========================================

@mcp_app.resource(
    "profile://summary",
    name="candidate_profile_summary",
    description="本地求职者脱敏个人画像（隐藏敏感手机号与联系方式）",
    mime_type="application/json",
)
def get_sanitized_profile_summary() -> str:
    """获取已脱敏的本地求职者档案摘要供模型或宿主直接读取"""
    from core.config import load_user_profile

    profile = load_user_profile()
    data = profile.model_dump(mode="json")
    
    # 严格脱敏：去除联系方式与敏感隐私
    if "basics" in data:
        data["basics"].pop("phone", None)
        data["basics"].pop("email", None)
        data["basics"].pop("id_card", None)
        data["basics"].pop("address", None)

    return json.dumps(data, ensure_ascii=False, indent=2)


def main():
    """以标准 stdio 协议启动 MCP 服务端"""
    mcp_app.run(transport="stdio")


if __name__ == "__main__":
    main()

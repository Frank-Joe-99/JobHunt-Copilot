"""
AI 场景化模拟面试官业务处理器 (Mock Interviewer Handler)
负责统筹状态机推进、提示词注入、流式问答对话与面试复盘体检报告生成。
"""

import time
from pathlib import Path
from typing import Generator

from core.config import load_user_profile
from core.state import (
    InterviewEvaluationReport,
    InterviewRole,
    InterviewSession,
    InterviewStage,
    InterviewTurn,
    UserProfile,
)
from skills.mock_interviewer.prompt import (
    DRILL_DOWN_DIRECTIVE,
    EVALUATION_REPORT_SYSTEM,
    INTERVIEWER_PERSONAS,
    STAGE_GUIDELINES,
)
from skills.mock_interviewer.state_machine import InterviewStateMachine
from tools.llm_client import LLMClient


def _build_profile_summary(
    profile: UserProfile, target_company: str, target_role: str
) -> str:
    """提取候选人关键画像（学历、代表项目、核心技能、实习），供面试官提问参考"""
    latest_edu = profile.education[0] if profile.education else None
    school = profile.basics.school or (latest_edu.school if latest_edu else "高校")
    degree = profile.basics.degree or (latest_edu.degree if latest_edu else "应届")
    major = latest_edu.major if latest_edu else (profile.basics.department or "")

    # 项目经历精炼
    projects_summary = []
    for p in profile.projects[:3]:
        hl = "；".join(p.highlights[:2]) if p.highlights else ""
        projects_summary.append(f"- 【{p.name}】（角色：{p.role or '核心开发'}）：{hl}")
    proj_str = "\n".join(projects_summary) if projects_summary else "（暂无具体项目经历）"

    # 实习经历精炼
    intern_summary = []
    for it in profile.internships[:2]:
        hl = "；".join(it.highlights[:2]) if it.highlights else ""
        intern_summary.append(f"- 【{it.company}】（岗位：{it.role}）：{hl}")
    intern_str = "\n".join(intern_summary) if intern_summary else "（暂无实习经历）"

    # 技能清单精炼
    skills_parts = []
    if profile.skills:
        if profile.skills.programming_languages:
            langs = [pl.name for pl in profile.skills.programming_languages]
            skills_parts.append(f"编程语言: {', '.join(langs)}")
        if profile.skills.frameworks_and_tools:
            skills_parts.append(f"框架与工具: {', '.join(profile.skills.frameworks_and_tools)}")
        if profile.skills.databases:
            skills_parts.append(f"数据库/中间件: {', '.join(profile.skills.databases)}")
    skills_str = " | ".join(skills_parts) if skills_parts else "（未提供）"

    return (
        f"【目标求职岗位】: {target_company} · {target_role}\n"
        f"【候选人信息】: {profile.basics.name} ({school} / {degree} / {major})\n"
        f"【核心技能】: {skills_str}\n"
        f"【代表实战项目】:\n{proj_str}\n"
        f"【过往实习经历】:\n{intern_str}"
    )


def start_interview(
    profile: UserProfile | None = None,
    target_role: str = "AI infra 研究员",
    target_company: str = "目标大厂",
    role: InterviewRole = InterviewRole.STRICT_ARCHITECT,
    provider: str | None = None,
) -> tuple[InterviewSession, Generator[str, None, None]]:
    """
    初始化面试会话，并返回 (session 实体, 面试官第一句开场白流式生成器)。
    """
    if profile is None:
        profile = load_user_profile()

    # 1. 创建会话实体
    session = InterviewSession(
        session_id=f"interview_{str(role.value)}_{int(time.time())}",
        role=role,
        current_stage=InterviewStage.INTRO,
        target_role=target_role,
        target_company=target_company,
    )

    # 2. 组装开场白消息
    llm_client = LLMClient(provider=provider)
    system_prompt = INTERVIEWER_PERSONAS[role]

    latest_edu = profile.education[0] if profile.education else None
    school = profile.basics.school or (latest_edu.school if latest_edu else "高校")
    degree = profile.basics.degree or (latest_edu.degree if latest_edu else "应届")
    major = latest_edu.major if latest_edu else (profile.basics.department or "")

    intro_instruction = (
        f"{STAGE_GUIDELINES[InterviewStage.INTRO]}\n\n"
        f"【面试目标】: {target_company} - {target_role}\n"
        f"【候选人姓名】: {profile.basics.name}\n"
        f"【当前学历专业】: {school} / {degree} / {major}\n"
        "请作为面试官直接说出你的第一句开场白（向候选人问好并邀请其做自我介绍）。注意：直接说出台词，不要带任何括号旁白说明。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": intro_instruction},
    ]

    # 3. 调大模型流式吐出第 1 句破冰词，并在流输出完成时将问题登记入会话历史
    raw_stream = llm_client.chat_stream(messages=messages)

    def generate_and_record() -> Generator[str, None, None]:
        full_response = []
        for chunk in raw_stream:
            full_response.append(chunk)
            yield chunk

        q_text = "".join(full_response).strip()
        session.history.append(
            InterviewTurn(
                turn_id=1,
                stage=InterviewStage.INTRO,
                question=q_text,
                answer="",
            )
        )

    return session, generate_and_record()


def step_interview_stream(
    session: InterviewSession,
    user_answer: str,
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> Generator[str, None, None]:
    """
    接收候选人当前回答，驱动状态机推演，流式生成面试官的下一句提问或追问。
    """
    if profile is None:
        profile = load_user_profile()

    clean_answer = user_answer.strip()

    # 1. 登记候选人对上一轮问题的回答
    if session.history and not session.history[-1].answer:
        session.history[-1].answer = clean_answer or "（候选人未作答）"
    elif not session.history:
        session.history.append(
            InterviewTurn(
                turn_id=1,
                stage=session.current_stage,
                question="（开场破冰）",
                answer=clean_answer or "（候选人未作答）",
            )
        )

    # 2. 状态机检查快捷指令与阶段推进
    sm = InterviewStateMachine()
    cmd = sm.handle_command(clean_answer, session=session)

    if cmd == "finish":
        session.is_finished = True
        session.current_stage = InterviewStage.COMPLETED
        yield "好的，今天的面试到此结束，感谢你的参与。正在为你出具全景复盘体检报告..."
        return

    is_advancing = False
    if cmd == "next":
        # sm.handle_command 内部已调用 advance_stage
        if session.is_finished:
            yield "所有面试环节已完成，感谢你的回答，稍后将生成复盘体检报告。"
            return
        yield f"好的，已跳过上一环节，现在进入阶段：【{session.current_stage.value}】。\n"
        is_advancing = True
    else:
        # 正常回答模式：检查当前阶段问答轮次是否达到上限，决定是否晋级
        if sm.should_advance(session=session):
            sm.advance_stage(session=session)
            is_advancing = True

        if session.is_finished:
            yield "所有面试环节已完成，感谢你的回答，稍后将生成复盘体检报告。"
            return

    # 3. 构造出题考核指引
    if is_advancing:
        directive = (
            f"{STAGE_GUIDELINES.get(session.current_stage, '')}\n"
            f"请根据候选人的背景档案与当前表现，直接提出本阶段的第 1 个核心问题（150字以内，保持考官视角，直接说台词，不要带任何括号旁白说明）。"
        )
    else:
        directive = (
            f"{DRILL_DOWN_DIRECTIVE}\n"
            f"请针对候选人刚才的回答一针见血地追问底层原理、指标量化或边界极限（150字以内，保持考官视角，直接说台词，不要带任何括号旁白说明）。"
        )

    # 4. 组装对话历史上下文
    profile_summary = _build_profile_summary(profile, session.target_company, session.target_role)
    system_prompt = (
        f"{INTERVIEWER_PERSONAS[session.role]}\n\n"
        f"【候选人背景画像】:\n{profile_summary}\n\n"
        f"【当前面试阶段】: {session.current_stage.value}"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # 注入历史对话 (上一轮以前的完整问答)
    for turn in session.history[:-1]:
        messages.append({"role": "assistant", "content": turn.question})
        messages.append({"role": "user", "content": turn.answer or "（无）"})

    # 最后一轮 (即刚才那一问一答 + 本次出题的系统考核指令)
    last_turn = session.history[-1]
    messages.append({"role": "assistant", "content": last_turn.question})
    last_user_content = (
        f"{last_turn.answer}\n\n[系统考核指令 (对候选人隐蔽)]：\n{directive}"
        if cmd != "next"
        else f"[候选人已跳过上一环节]\n\n[系统考核指令 (对候选人隐蔽)]：\n{directive}"
    )
    messages.append({"role": "user", "content": last_user_content})

    # 5. 调大模型流式输出新问题，并在结束时登记新轮次
    llm_client = LLMClient(provider=provider)
    raw_stream = llm_client.chat_stream(messages=messages)

    full_response = []
    for chunk in raw_stream:
        full_response.append(chunk)
        yield chunk

    new_question = "".join(full_response).strip()
    session.history.append(
        InterviewTurn(
            turn_id=len(session.history) + 1,
            stage=session.current_stage,
            question=new_question,
            answer="",
        )
    )


def finish_interview(
    session: InterviewSession,
    provider: str | None = None,
) -> tuple[InterviewEvaluationReport, Path]:
    """
    终结面试，调用大模型生成全维度复盘体检报告，并持久化保存为 Markdown 文件。

    Returns:
        tuple[InterviewEvaluationReport, Path]: (复盘报告实体, Markdown 文件保存路径)
    """
    session.is_finished = True
    session.current_stage = InterviewStage.COMPLETED

    # 1. 组装整场面试问答明细
    history_lines = []
    for turn in session.history:
        ans = turn.answer.strip() if turn.answer else "（未作答/已跳过）"
        history_lines.append(
            f"【轮次 {turn.turn_id} | 阶段: {turn.stage.value}】\n"
            f"面试官提问: {turn.question}\n"
            f"候选人回答: {ans}"
        )
    transcript_text = "\n\n".join(history_lines) if history_lines else "（整场无问答交互）"

    # 2. 构造复盘评估消息
    messages = [
        {"role": "system", "content": EVALUATION_REPORT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"【目标岗位】: {session.target_company} · {session.target_role}\n"
                f"【面试官风格】: {session.role.value}\n\n"
                f"【整场问答实录 (Transcript)】:\n{transcript_text}\n\n"
                "请严格按照系统提示词的 JSON 格式规范出具全维度复盘体检报告。"
            ),
        },
    ]

    # 3. 结构化反序列化生成报告实体
    llm_client = LLMClient(provider=provider)
    report = llm_client.chat_pydantic(
        messages=messages,
        model_class=InterviewEvaluationReport,
    )

    # 4. 渲染 Markdown 报告
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_dir = Path("storage/interview_logs")
    report_dir.mkdir(parents=True, exist_ok=True)
    file_path = report_dir / f"interview_report_{session.role.value}_{timestamp}.md"

    # 格式化维度评分表
    dim_rows = []
    for dim, score in report.dimension_scores.items():
        tag = "🟢 优秀" if score >= 85 else ("🟡 良好" if score >= 70 else "🔴 需加固")
        dim_rows.append(f"| {dim} | {score} | {tag} |")
    dim_table = "\n".join(dim_rows) if dim_rows else "| 综合能力 | 80 | 🟡 良好 |"

    # 格式化亮点与短板
    highlights_md = (
        "\n".join(f"- {h}" for h in report.highlights)
        if report.highlights
        else "- 暂无显著高光"
    )
    weaknesses_md = (
        "\n".join(f"- {w}" for w in report.weaknesses)
        if report.weaknesses
        else "- 表现平稳，无显著硬伤"
    )

    # 格式化标准满分范例
    model_answers_md = []
    for i, ma in enumerate(report.model_answers, 1):
        q = ma.get("question", "")
        ideal = ma.get("ideal_answer", "")
        model_answers_md.append(f"### {i}. 原问题：{q}\n> **💡 满分参考示范**：\n>\n> {ideal}\n")
    model_answers_str = (
        "\n".join(model_answers_md) if model_answers_md else "（暂无特定示范）"
    )

    # 格式化完整问答录
    transcript_md = []
    for turn in session.history:
        ans = turn.answer.strip() if turn.answer else "（未作答/已跳过）"
        transcript_md.append(
            f"**[Round {turn.turn_id} · {turn.stage.value}]**\n\n"
            f"- **面试官**：{turn.question}\n"
            f"- **候选人**：{ans}\n"
        )
    transcript_full_str = (
        "\n".join(transcript_md) if transcript_md else "（暂无交互记录）"
    )

    md_content = f"""# 🎯 AI 场景化模拟面试全景复盘体检报告

- **面试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
- **目标企业/岗位**: {session.target_company} · {session.target_role}
- **面试官人设**: {session.role.value}
- **综合得分**: **{report.overall_score} / 100**
- **建议结果**: **{report.result}**

---

## 📋 总体评语
{report.summary}

---

## 📊 全维度技能诊断
| 评估维度 | 得分 | 状态 |
| :--- | :---: | :--- |
{dim_table}

---

## 🌟 表现亮点 (Highlights)
{highlights_md}

---

## ⚠️ 致命失分点与技术硬伤 (Weaknesses)
{weaknesses_md}

---

## 💡 核心问题标准满分范例 (Model Answers)
{model_answers_str}

---

## 📜 附录：整场真实问答实录 (Full Transcript)
{transcript_full_str}
"""

    file_path.write_text(md_content, encoding="utf-8")
    report.report_file_path = str(file_path)

    return report, file_path
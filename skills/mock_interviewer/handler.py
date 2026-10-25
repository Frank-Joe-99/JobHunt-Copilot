"""
AI 场景化模拟面试官业务处理器 (Mock Interviewer Handler)
负责统筹状态机推进、提示词注入、流式问答对话与面试复盘体检报告生成。
"""

import json
import hashlib
import time
from uuid import uuid4
from pathlib import Path
from typing import Generator, Literal

from core.config import load_user_profile, PROJECT_ROOT
from core.context import candidate_context
from core.state import (
    JobDescription,
    InterviewEvaluationReport,
    InterviewPolicy,
    InterviewRequestMetrics,
    InterviewRole,
    InterviewSession,
    InterviewStage,
    InterviewTurn,
    UserProfile,
)
from skills.mock_interviewer.prompt import (
    DRILL_DOWN_DIRECTIVE,
    EVALUATION_REPORT_SYSTEM,
    FACTUALITY_GUARDRAIL,
    INTERVIEWER_PERSONAS,
    STAGE_GUIDELINES,
)
from skills.mock_interviewer.state_machine import InterviewStateMachine
from skills.mock_interviewer.adaptive import close_session, observed_stages, step_adaptive
from skills.mock_interviewer.telemetry import collect_model_metrics
from tools.llm_client import LLMClient


def _resolve_profile(profile: UserProfile | None) -> UserProfile:
    """真实档案缺失或损坏时报告配置错误，不将示例身份当成候选人事实。"""
    return profile if profile is not None else load_user_profile()


def _build_profile_summary(
    profile: UserProfile, target_company: str, target_role: str,
    job_description: JobDescription | None = None,
) -> str:
    return json.dumps({
        "target_company": target_company,
        "target_role": target_role,
        "job_description": job_description.model_dump() if job_description else None,
        "candidate_facts": candidate_context(profile),
    }, ensure_ascii=False, indent=2)


def _mode_instruction(mode: str) -> str:
    if mode == "practice":
        return "当前为训练模式：用户请求提示、讲解或重答时可以提供帮助；示范不得冒充其真实经历。"
    return "当前为模拟模式：保持考官视角，不替候选人作答；用户仍可跳过或结束。"


def _session_client(session: InterviewSession, provider: str | None) -> LLMClient:
    client = LLMClient(provider=provider or session.provider_name)
    config = getattr(client, "config", None)
    if config is not None:
        fingerprint = hashlib.sha256(json.dumps({
            "provider": client.provider_name,
            "endpoint": client.base_url,
            "model": config.model,
        }, sort_keys=True).encode()).hexdigest()
        if session.model_fingerprint and fingerprint != session.model_fingerprint and provider is None:
            client.close()
            raise ValueError("会话模型或端点配置已变化；请明确指定 --provider 后再继续。")
        session.model_fingerprint = fingerprint
    session.provider_name = getattr(client, "provider_name", provider or session.provider_name)
    return client


def start_interview(
    profile: UserProfile | None = None,
    target_role: str | None = None,
    target_company: str = "目标大厂",
    role: InterviewRole = InterviewRole.STRICT_ARCHITECT,
    provider: str | None = None,
    *,
    job_description: JobDescription | None = None,
    mode: Literal["simulation", "practice"] = "simulation",
    session_id: str | None = None,
    flow: Literal["fixed", "adaptive"] = "fixed",
    policy: InterviewPolicy | None = None,
    metrics: InterviewRequestMetrics | None = None,
    request_budget: int | None = None,
) -> tuple[InterviewSession, Generator[str, None, None]]:
    """
    初始化面试会话，并返回 (session 实体, 面试官第一句开场白流式生成器)。
    """
    profile = _resolve_profile(profile)

    target_role = target_role or (job_description.role if job_description else None) or (
        profile.objective.target_role if profile.objective else "技术岗位"
    )

    # 1. 创建会话实体
    session = InterviewSession(
        session_id=session_id or f"interview_{uuid4().hex}",
        role=role,
        current_stage=InterviewStage.INTRO,
        target_role=target_role,
        target_company=target_company,
        job_description=job_description,
        mode=mode,
        flow=flow,
        policy=policy or InterviewPolicy(),
        enforce_policy=flow == "adaptive" or policy is not None,
        started_at=time.time(),
        active_started_at=time.time(),
    )

    # 2. 组装开场白消息
    llm_client = _session_client(session, provider)
    system_prompt = (
        f"{INTERVIEWER_PERSONAS[role]}\n\n{FACTUALITY_GUARDRAIL}\n\n"
        f"{_mode_instruction(mode)}\n\n"
        f"【岗位与候选人业务材料】:\n{_build_profile_summary(profile, target_company, target_role, job_description)}"
    )
    intro_instruction = (
        f"{STAGE_GUIDELINES[InterviewStage.INTRO]}\n"
        "你正在模拟目标岗位的面试，不要声称自己实际受雇于该公司或知道其内部信息。"
        "请简短问好并邀请候选人自我介绍，不使用候选人姓名和联系方式。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": intro_instruction},
    ]

    # 3. 调大模型流式吐出第 1 句破冰词，并在流输出完成时将问题登记入会话历史
    stream_options = {
        "max_retries": min(session.policy.max_requests_per_turn, session.policy.max_requests_total, request_budget if request_budget is not None else session.policy.max_requests_total),
        "timeout": session.policy.request_timeout_seconds,
    } if session.enforce_policy else {}
    raw_stream = llm_client.chat_stream(messages=messages, **stream_options)

    def generate_and_record() -> Generator[str, None, None]:
        full_response = []
        try:
            for chunk in raw_stream:
                full_response.append(chunk)
                yield chunk
        finally:
            collect_model_metrics(llm_client, metrics)
            llm_client.close()
        q_text = "".join(full_response).strip()
        if q_text:
            session.history.append(InterviewTurn(
                turn_id=1, stage=InterviewStage.INTRO, question=q_text, answer="",
            ))

    return session, generate_and_record()


def step_interview_stream(
    session: InterviewSession,
    user_answer: str,
    profile: UserProfile | None = None,
    provider: str | None = None,
    *, metrics: InterviewRequestMetrics | None = None, request_budget: int | None = None,
) -> Generator[str, None, None]:
    """
    接收候选人当前回答，驱动状态机推演，流式生成面试官的下一句提问或追问。
    """
    profile = _resolve_profile(profile)
    metrics = metrics if metrics is not None else InterviewRequestMetrics()
    if session.flow == "adaptive":
        yield from step_adaptive(
            session, user_answer, profile,
            client_factory=lambda: _session_client(session, provider),
            metrics=metrics, request_budget=request_budget,
        )
        return

    clean_answer = user_answer.strip()

    # 1. 状态机检查快捷指令与阶段推进
    sm = InterviewStateMachine()
    cmd = sm.handle_command(clean_answer, session=session)

    # 2. 登记候选人对上一轮问题的回答（若为快捷指令则作相应说明，避免污染真实面试问答记录）
    if cmd == "finish":
        if session.history and not session.history[-1].answer:
            session.history[-1].answer = "（候选人申请提前结束面试）"
        close_session(session, "user_finish")
        metrics.action = "finish"
        yield "好的，今天的面试到此结束，感谢你的参与。正在为你出具全景复盘体检报告..."
        return

    is_advancing = False
    is_reverse_qa_response = False
    if cmd == "next":
        if session.history and not session.history[-1].answer:
            session.history[-1].answer = "（候选人申请跳过本环节）"
        # sm.handle_command 内部已调用 advance_stage
        if session.is_finished:
            yield "所有面试环节已完成，感谢你的回答，稍后将生成复盘体检报告。"
            return
        yield f"好的，已跳过上一环节，现在进入阶段：【{session.current_stage.value}】。\n"
        is_advancing = True
    else:
        # 常规用户回答
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

        # 检查当前阶段问答轮次是否达到上限，决定是否晋级
        if sm.should_advance(session=session):
            if session.current_stage == InterviewStage.REVERSE_QA:
                # 先回答候选人的反问，再结束面试；不能直接吞掉反问。
                is_reverse_qa_response = True
            else:
                sm.advance_stage(session=session)
                is_advancing = True

        if session.is_finished:
            yield "所有面试环节已完成，感谢你的回答，稍后将生成复盘体检报告。"
            return

    # 3. 构造出题考核指引
    if is_reverse_qa_response:
        directive = (
            "候选人刚刚提出了反问。请结合目标企业与岗位，以面试官身份给出简短、审慎的回应；"
            "不得编造公司内部信息。回应后礼貌结束本次面试，不再提出新问题。"
        )
    elif is_advancing:
        directive = (
            f"{STAGE_GUIDELINES.get(session.current_stage, '')}\n"
            f"请根据候选人的背景档案与当前表现，直接提出本阶段的第 1 个核心问题（150字以内，保持考官视角，直接说台词，不要带任何括号旁白说明）。"
        )
    else:
        directive = (
            f"{DRILL_DOWN_DIRECTIVE}\n"
            "请围绕当前岗位和回答提出一个有价值的追问，简短表达，不预设技术领域或强求无关指标。"
        )

    if session.mode == "practice":
        directive += "\n训练模式下，用户请求提示、讲解或重答时优先帮助其当前问题，不必机械提出新问题。"

    # 4. 组装对话历史上下文
    profile_summary = _build_profile_summary(profile, session.target_company, session.target_role, session.job_description)
    system_prompt = (
        f"{INTERVIEWER_PERSONAS[session.role]}\n\n"
        f"{FACTUALITY_GUARDRAIL}\n\n"
        f"{_mode_instruction(session.mode)}\n\n"
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
    llm_client = _session_client(session, provider)
    stream_options = {
        "max_retries": min(session.policy.max_requests_per_turn, request_budget) if request_budget is not None else session.policy.max_requests_per_turn,
        "timeout": session.policy.request_timeout_seconds,
    } if session.enforce_policy else {}
    raw_stream = llm_client.chat_stream(messages=messages, **stream_options)

    full_response = []
    try:
        for chunk in raw_stream:
            full_response.append(chunk)
            yield chunk
    finally:
        collect_model_metrics(llm_client, metrics)
        llm_client.close()
    new_question = "".join(full_response).strip()
    if new_question and is_reverse_qa_response:
        session.history[-1].feedback = new_question
        session.current_stage = InterviewStage.COMPLETED
        session.is_finished = True
    elif new_question:
        session.history.append(InterviewTurn(
            turn_id=len(session.history) + 1, stage=session.current_stage,
            question=new_question, answer="",
        ))


def finish_interview(
    session: InterviewSession,
    provider: str | None = None,
    *, report_id: str = "finish",
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
        label = "训练提示" if turn.kind == "hint" else "重答邀请" if turn.kind == "retry" else "面试官提问"
        history_lines.append(
            f"【轮次 {turn.turn_id} | 阶段: {turn.stage.value}】\n"
            f"{label}: {turn.question}\n"
            f"候选人回答: {ans}"
            + (f"\n面试官回应: {turn.feedback}" if turn.feedback else "")
        )
    transcript_text = "\n\n".join(history_lines) if history_lines else "（整场无问答交互）"

    # 2. 构造复盘评估消息
    messages = [
        {"role": "system", "content": EVALUATION_REPORT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"【目标岗位】: {session.target_company} · {session.target_role}\n"
                f"【面试官风格】: {session.role.value}\n"
                f"【流程/模式】: {session.flow} / {session.mode}\n"
                f"【结束原因】: {session.stop_reason or '用户交卷'}\n"
                f"【有回答记录的阶段】: {', '.join(observed_stages(session)) or '未观察到'}\n"
                "训练提示和重答邀请属于工具帮助，不是候选人事实或已完成成果；只按实际回答评估，证据不足标未观察到。\n"
                f"【岗位原文】: {session.job_description.raw_text if session.job_description else '未提供 JD，仅按目标岗位评估'}\n\n"
                f"【整场问答实录 (Transcript)】:\n{transcript_text}\n\n"
                "请严格按照系统提示词的 JSON 格式规范出具全维度复盘体检报告。"
            ),
        },
    ]

    # 3. 结构化反序列化生成报告实体
    with _session_client(session, provider) as llm_client:
        report = llm_client.chat_pydantic(
            messages=messages,
            model_class=InterviewEvaluationReport,
        )
    return report, export_interview_report(session, report, report_id=report_id)


def export_interview_report(
    session: InterviewSession, report: InterviewEvaluationReport, *, report_id: str = "finish",
) -> Path:
    """从已校验的完整记录导出报告；重放或补回丢失的文件不需要请求模型。"""
    report_dir = PROJECT_ROOT / "storage" / "interview_logs"
    report_dir.mkdir(parents=True, exist_ok=True)
    session_tag = hashlib.sha256(json.dumps([session.session_id, report_id]).encode()).hexdigest()[:16]
    file_path = report_dir / f"interview_report_{session.role.value}_{session_tag}.md"

    # 格式化维度评分表
    dim_rows = []
    for dim, score in report.dimension_scores.items():
        tag = "🟢 优秀" if score >= 85 else ("🟡 良好" if score >= 70 else "🔴 需加固")
        dim_rows.append(f"| {dim} | {score} | {tag} |")
    dim_table = "\n".join(dim_rows) if dim_rows else "| 未观察到 | — | 问答证据不足，未评分 |"

    # 格式化亮点与短板
    highlights_md = (
        "\n".join(f"- {h}" for h in report.highlights)
        if report.highlights
        else "- 暂无显著高光"
    )
    weaknesses_md = (
        "\n".join(f"- {w}" for w in report.weaknesses)
        if report.weaknesses
        else "- 本次未给出有依据的短板结论"
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
        label = "面试官·训练提示" if turn.kind == "hint" else "面试官·重答邀请" if turn.kind == "retry" else "面试官"
        transcript_md.append(
            f"**[Round {turn.turn_id} · {turn.stage.value}]**\n\n"
            f"- **{label}**：{turn.question}\n"
            f"- **候选人**：{ans}\n"
            + (f"- **面试官回应**：{turn.feedback}\n" if turn.feedback else "")
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

    temporary = file_path.with_suffix(".tmp")
    temporary.write_text(md_content, encoding="utf-8")
    temporary.replace(file_path)
    report.report_file_path = str(file_path)

    return file_path

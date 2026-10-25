"""CLI / MCP 共用的持久会话编排；网络期间只持有会话文件锁，不持有数据库事务。"""

from pathlib import Path
import time
from typing import Generator, Literal
from uuid import uuid4

from core.state import (
    InterviewEvaluationReport, InterviewPolicy, InterviewRequestMetrics, InterviewRole, InterviewSession, JobDescription, UserProfile,
)
from skills.mock_interviewer import handler
from skills.mock_interviewer.session_store import (
    InterviewStore, SessionConflict, SessionStoreError, profile_digest,
)


def _copy_session(target: InterviewSession, source: InterviewSession):
    copy = source.model_copy(deep=True)
    for field in InterviewSession.model_fields:
        setattr(target, field, getattr(copy, field))


def resume_interview(session_id: str, *, store: InterviewStore | None = None) -> InterviewSession:
    store = store or InterviewStore()
    current = store.load(session_id).session
    if current.is_paused:
        current = store.set_paused(session_id, False)
    pending = store.unfinished(session_id)
    current.pending_request_id = pending.request_id if pending else None
    return current


def start_interview(
    profile: UserProfile | None = None, target_role: str | None = None,
    target_company: str = "目标大厂", role: InterviewRole = InterviewRole.STRICT_ARCHITECT,
    provider: str | None = None, *, job_description: JobDescription | None = None,
    mode: Literal["simulation", "practice"] = "simulation", store: InterviewStore | None = None,
    flow: Literal["fixed", "adaptive"] = "fixed", policy: InterviewPolicy | None = None,
) -> tuple[InterviewSession, Generator[str, None, None]]:
    store = store or InterviewStore()
    profile = handler._resolve_profile(profile).model_copy(deep=True)
    opening_metrics = InterviewRequestMetrics()
    generated, raw = handler.start_interview(
        profile, target_role, target_company, role, provider,
        job_description=job_description, mode=mode,
        flow=flow, policy=policy, metrics=opening_metrics,
    )
    store.create(generated, profile, prepare_opening=True)
    session = generated.model_copy(deep=True)
    session.pending_request_id = "opening"
    return session, _stream_request(session, "opening", "opening", "", provider, store, (generated, raw, opening_metrics))


def _stream_request(
    session: InterviewSession, request_id: str, operation: str, input_text: str,
    provider: str | None, store: InterviewStore, prepared=None,
) -> Generator[str, None, None]:
    with store.locked(session.session_id):
        current, request = store.begin_request(
            session.session_id, request_id, operation, input_text, expected_revision=session.revision,
        )
        if request.status == "completed":
            if prepared is not None:
                prepared[1].close()
            if request.result_session is None:
                raise SessionStoreError("已完成请求缺少会话结果。")
            _copy_session(session, request.result_session)
            if request.output_text:
                yield request.output_text
            return
        working = current.session.model_copy(deep=True)
        expected_revision = working.revision
        chunks = []
        stream = None
        committed = False
        started = time.monotonic()
        attempt_metrics = prepared[2] if prepared is not None else InterviewRequestMetrics()
        metrics = request.metrics.model_copy(deep=True)
        recorded = False
        failed_recorded = False
        def record_metrics(failed=False):
            nonlocal recorded, failed_recorded
            if not recorded:
                metrics.known_model_requests += attempt_metrics.known_model_requests
                metrics.elapsed_seconds += max(0, time.monotonic() - started)
                metrics.first_text_seconds = attempt_metrics.first_text_seconds
                metrics.format_used = attempt_metrics.format_used
                metrics.action = attempt_metrics.action
                metrics.policy_reason = attempt_metrics.policy_reason
                metrics.generation_attempts += int(attempt_metrics.known_model_requests > 0)
                recorded = True
            if failed and not failed_recorded:
                metrics.failed_generations += int(attempt_metrics.known_model_requests > 0)
                failed_recorded = True
        try:
            stats = store.statistics(session.session_id)
            request_budget = working.policy.max_requests_total - stats["known_model_requests"] - stats["unknown_request_upper_bound"]
            finish_command = input_text.strip().lower() in ("finish", "/finish", "quit", "/quit", "交卷", "退出")
            budget_reason = None
            if working.enforce_policy and not finish_command:
                if working.active_elapsed(time.time()) >= working.policy.max_duration_seconds:
                    budget_reason = "time_budget"
                elif len(working.history) >= working.policy.max_turns and working.current_stage.value != "reverse_qa":
                    budget_reason = "turn_budget"
                elif request_budget <= 0:
                    budget_reason = "request_budget"
            if budget_reason:
                handler.close_session(working, budget_reason)
                attempt_metrics.action, attempt_metrics.policy_reason = "finish", budget_reason
                stream = (text for text in ["本次面试预算已达上限，已保存回答；未考察的能力会在复盘中标明。"])
                if prepared is not None:
                    prepared[1].close()
            elif operation == "opening":
                if prepared is not None:
                    generated, stream = prepared[:2]
                else:
                    generated, stream = handler.start_interview(
                        current.profile, working.target_role, working.target_company, working.role,
                        provider or working.provider_name, job_description=working.job_description,
                        mode=working.mode, session_id=working.session_id,
                        flow=working.flow, policy=working.policy if working.enforce_policy else None,
                        metrics=attempt_metrics,
                        request_budget=request_budget if working.enforce_policy else None,
                    )
                    if (
                        provider is None and working.model_fingerprint
                        and generated.model_fingerprint != working.model_fingerprint
                    ):
                        stream.close()
                        raise ValueError("会话模型或端点已变化，请明确指定 --provider 后重试。")
                    for field in ("started_at", "elapsed_active_seconds", "active_started_at"):
                        setattr(generated, field, getattr(working, field))
                working = generated
                working.revision = expected_revision
                working.pending_request_id = None
            else:
                stream = handler.step_interview_stream(
                    working, input_text, current.profile, provider=provider,
                    metrics=attempt_metrics, request_budget=request_budget if working.enforce_policy else None,
                )
            for chunk in stream:
                if working.enforce_policy and budget_reason is None and not finish_command and (
                    working.active_elapsed(time.time()) >= working.policy.max_duration_seconds
                    or time.monotonic() - started >= working.policy.request_timeout_seconds
                ):
                    raise RuntimeError("本轮问题超出限时，未提交部分问题；回答已保存。")
                if chunk.strip() and attempt_metrics.first_text_seconds is None:
                    attempt_metrics.first_text_seconds = max(0, time.monotonic() - started)
                chunks.append(chunk)
                if not (working.flow == "adaptive" and operation == "answer"):
                    yield chunk
            working.pending_request_id = None
            record_metrics()
            store.complete(working, request_id, expected_revision, "".join(chunks), metrics=metrics)
            committed = True
            _copy_session(session, working)
            if working.flow == "adaptive" and operation == "answer":
                yield from chunks
        except BaseException as exc:
            if committed:
                raise
            if stream is not None:
                stream.close()
            record_metrics(failed=True)
            store.fail(session.session_id, request_id, "".join(chunks), type(exc).__name__, metrics=metrics)
            _copy_session(session, store.load(session.session_id).session)
            session.pending_request_id = request_id
            raise
        finally:
            if stream is not None:
                stream.close()


def step_interview_stream(
    session: InterviewSession, user_answer: str, profile: UserProfile | None = None,
    provider: str | None = None, *, request_id: str | None = None,
    store: InterviewStore | None = None,
) -> Generator[str, None, None]:
    store = store or InterviewStore()
    current = store.load(session.session_id)
    if profile is not None and profile_digest(profile) != current.profile_hash:
        raise ValueError("会话使用创建时的事实快照；背景变化请新建会话。")
    command = user_answer.strip().lower()
    if command in ("/pause", "pause", "暂停"):
        _copy_session(session, store.set_paused(session.session_id, True))
        yield "会话已暂停，已提交的回答已保存。"
        return
    if command in ("/retry", "retry", "重试"):
        request = store.unfinished(session.session_id)
        if request is None or request.operation == "finish":
            raise SessionConflict("没有可重试的问题请求；复盘失败时请重新生成报告。")
        yield from _stream_request(
            session, request.request_id, request.operation, request.input_text, provider, store,
        )
        return
    if request_id is None:
        pending = store.unfinished(session.session_id)
        request_id = (
            pending.request_id if pending and pending.operation == "answer"
            and pending.input_text == user_answer else uuid4().hex
        )
    yield from _stream_request(session, request_id, "answer", user_answer, provider, store)


def compare_interviews(first_id: str, second_id: str, *, store: InterviewStore | None = None) -> dict:
    """只对比可测状态与输入一致性，不把模型判断或合成延迟当作质量评分。"""
    store = store or InterviewStore()
    first, second = store.load(first_id), store.load(second_id)
    def context(record):
        session = record.session
        return (record.profile_hash, session.target_company, session.target_role, session.role, session.mode, session.job_description)
    def answers(record):
        return [turn.answer for turn in record.session.history if turn.answer and not turn.answer.startswith("（候选人")]
    same_inputs = context(first) == context(second) and answers(first) == answers(second)
    shared_budget_fields = {"max_turns", "max_duration_seconds", "max_requests_per_turn", "max_requests_total", "request_timeout_seconds"}
    same_budget = first.session.enforce_policy and second.session.enforce_policy and (
        first.session.policy.model_dump(include=shared_budget_fields)
        == second.session.policy.model_dump(include=shared_budget_fields)
    )
    return {
        "same_context_and_answers": same_inputs,
        "same_enforced_budget": same_budget,
        "shared_budget_fields": sorted(shared_budget_fields),
        "same_model_identity": first.session.model_fingerprint == second.session.model_fingerprint
        if first.session.model_fingerprint and second.session.model_fingerprint else None,
        "sessions": [
            {"session_id": record.session.session_id, "flow": record.session.flow,
             "statistics": store.statistics(record.session.session_id)}
            for record in (first, second)
        ],
        "quality_review": "人工比较问题相关性、追问必要性、事实边界及覆盖；本结果不自动评分。",
    }


def finish_interview(
    session: InterviewSession, provider: str | None = None, *, request_id: str = "finish",
    store: InterviewStore | None = None,
) -> tuple[InterviewEvaluationReport, Path]:
    store = store or InterviewStore()
    with store.locked(session.session_id):
        current, request = store.begin_request(
            session.session_id, request_id, "finish", "", expected_revision=session.revision,
        )
        if request.status == "completed":
            if not request.report or not request.report_path or request.result_session is None:
                raise SessionStoreError("复盘结果记录不完整。")
            _copy_session(session, request.result_session)
            path = Path(request.report_path)
            if not path.is_file():
                path = handler.export_interview_report(session, request.report, report_id=request_id)
            return request.report, path
        working = current.session.model_copy(deep=True)
        revision = working.revision
        try:
            report, path = handler.finish_interview(working, provider=provider, report_id=request_id)
            store.complete(working, request_id, revision, "", report=report, report_path=str(path))
            _copy_session(session, working)
            return report, path
        except BaseException as exc:
            store.fail(session.session_id, request_id, "", type(exc).__name__)
            _copy_session(session, store.load(session.session_id).session)
            session.pending_request_id = request_id
            raise

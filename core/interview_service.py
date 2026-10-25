"""CLI / MCP 共用的持久会话编排；网络期间只持有会话文件锁，不持有数据库事务。"""

from pathlib import Path
from typing import Generator, Literal
from uuid import uuid4

from core.state import (
    InterviewEvaluationReport, InterviewRole, InterviewSession, JobDescription, UserProfile,
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
) -> tuple[InterviewSession, Generator[str, None, None]]:
    store = store or InterviewStore()
    profile = handler._resolve_profile(profile).model_copy(deep=True)
    generated, raw = handler.start_interview(
        profile, target_role, target_company, role, provider,
        job_description=job_description, mode=mode,
    )
    store.create(generated, profile, prepare_opening=True)
    session = generated.model_copy(deep=True)
    session.pending_request_id = "opening"
    return session, _stream_request(session, "opening", "opening", "", provider, store, (generated, raw))


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
        try:
            if operation == "opening":
                if prepared is not None:
                    generated, stream = prepared
                else:
                    generated, stream = handler.start_interview(
                        current.profile, working.target_role, working.target_company, working.role,
                        provider or working.provider_name, job_description=working.job_description,
                        mode=working.mode, session_id=working.session_id,
                    )
                    if (
                        provider is None and working.model_fingerprint
                        and generated.model_fingerprint != working.model_fingerprint
                    ):
                        stream.close()
                        raise ValueError("会话模型或端点已变化，请明确指定 --provider 后重试。")
                working = generated
                working.revision = expected_revision
                working.pending_request_id = None
            else:
                stream = handler.step_interview_stream(
                    working, input_text, current.profile, provider=provider,
                )
            for chunk in stream:
                chunks.append(chunk)
                yield chunk
            working.pending_request_id = None
            store.complete(working, request_id, expected_revision, "".join(chunks))
            _copy_session(session, working)
        except BaseException as exc:
            store.fail(session.session_id, request_id, "".join(chunks), type(exc).__name__)
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

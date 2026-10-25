"""私有会话使用合成快照、临时 SQLite 和离线模型；验证失败边界而非生成措辞。"""

from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from core import interview_service as service
from core.state import InterviewEvaluationReport, InterviewSession, InterviewStage, JobDescription
from skills.mock_interviewer import handler
from skills.mock_interviewer.session_store import InterviewStore, SessionConflict, SessionStoreError
from tools.file_lock import FileLockBusy


def opened(profile, interview_env, **kwargs):
    store, llm = interview_env
    session, stream = service.start_interview(profile, store=store, **kwargs)
    assert "".join(stream)
    return session, store, llm


def test_restart_uses_frozen_facts_and_job_context(profile, interview_env, monkeypatch):
    job = JobDescription(company="合成公司", role="前端开发", raw_text="可访问性与 React 测试")
    session, store, llm = opened(profile, interview_env, job_description=job, mode="practice")
    original = store.load(session.session_id).profile_hash
    profile.projects[-1].name = "主档案后来修改，不可污染旧会话"
    monkeypatch.setattr(handler, "load_user_profile", lambda: pytest.fail("恢复不能读当前主档案"))
    restarted = InterviewStore(store.db_path)
    restored = service.resume_interview(session.session_id, store=restarted)
    assert "".join(service.step_interview_stream(restored, "我的真实回答", store=restarted))
    prompt = llm.calls[-1]["messages"][0]["content"]
    assert "合成项目5" in prompt and "主档案后来修改" not in prompt
    assert job.raw_text in prompt and "训练模式" in prompt
    assert restarted.load(session.session_id).profile_hash == original
    with pytest.raises(ValueError, match="事实快照"):
        list(service.step_interview_stream(restored, "回答", profile, store=restarted))


def test_opening_is_recoverable_even_before_stream_is_consumed(profile, interview_env):
    store, llm = interview_env
    first, unopened = service.start_interview(profile, store=store)
    second, second_stream = service.start_interview(profile, store=store)
    assert first.session_id != second.session_id
    assert llm.calls == []
    assert store.unfinished(first.session_id).operation == "opening"
    restored = service.resume_interview(first.session_id, store=InterviewStore(store.db_path))
    assert restored.pending_request_id == "opening"
    assert "".join(service.step_interview_stream(restored, "/retry", store=store))
    assert len(store.load(first.session_id).session.history) == 1
    assert store.get_request(first.session_id, "opening").attempts == 1
    unopened.close()
    second_stream.close()


def test_partial_opening_stays_out_of_history_and_retries_once(profile, interview_env):
    store, llm = interview_env
    llm.chunks = ["不完整开场"]
    llm.stream_error = RuntimeError("synthetic interruption")
    session, stream = service.start_interview(profile, store=store)
    with pytest.raises(RuntimeError):
        list(stream)
    assert store.load(session.session_id).session.history == []
    assert store.get_request(session.session_id, "opening").output_text == "不完整开场"
    llm.chunks, llm.stream_error = ["完整开场问题"], None
    restored = service.resume_interview(session.session_id, store=store)
    assert "".join(service.step_interview_stream(restored, "/retry", store=store)) == "完整开场问题"
    assert len(restored.history) == 1
    assert store.get_request(session.session_id, "opening").attempts == 2


def test_failed_answer_is_saved_before_model_and_stage_commits_only_on_success(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.chunks, llm.stream_error = ["部分新问题"], RuntimeError("interrupted")
    with pytest.raises(RuntimeError):
        list(service.step_interview_stream(session, "已经提交的真实回答", request_id="answer_1", store=store))
    current = store.load(session.session_id).session
    assert current.current_stage == InterviewStage.INTRO
    assert len(current.history) == 1 and current.history[0].answer == "已经提交的真实回答"
    request = store.get_request(session.session_id, "answer_1")
    assert request.status == "failed" and request.output_text == "部分新问题"
    llm.chunks, llm.stream_error = ["完整下一题"], None
    assert "".join(service.step_interview_stream(session, "/retry", store=store)) == "完整下一题"
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    assert [turn.answer for turn in session.history] == ["已经提交的真实回答", ""]
    assert [turn.question for turn in session.history][-1] == "完整下一题"
    assert store.get_request(session.session_id, "answer_1").attempts == 2


def test_generator_cancellation_saves_answer_and_partial_output(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.chunks = ["尚未完整", "问题尾部"]
    stream = service.step_interview_stream(session, "保存于流开始前", request_id="cancelled_stream", store=store)
    assert next(stream) == "尚未完整"
    assert store.load(session.session_id).session.history[-1].answer == "保存于流开始前"
    # 流处于等待状态时，另一连接仍可取得 SQLite 写事务。
    with sqlite3.connect(store.db_path, timeout=0.1) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
    stream.close()
    request = store.get_request(session.session_id, "cancelled_stream")
    assert request.status == "failed" and request.error_code == "GeneratorExit"
    assert request.output_text == "尚未完整" and len(store.load(session.session_id).session.history) == 1
    assert llm.closed


def test_completed_request_replays_without_calling_model_or_rewinding_database(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    answer = "第一道回答"
    first = "".join(service.step_interview_stream(session, answer, request_id="stable", store=store))
    list(service.step_interview_stream(session, "第二道回答", request_id="second", store=store))
    latest = store.load(session.session_id).session
    before = len(llm.calls)
    replay = service.resume_interview(session.session_id, store=store)
    assert "".join(service.step_interview_stream(replay, answer, request_id="stable", store=store)) == first
    assert len(llm.calls) == before
    assert store.load(session.session_id).session == latest
    with pytest.raises(SessionConflict, match="不同"):
        list(service.step_interview_stream(replay, "同 ID 的不同输入", request_id="stable", store=store))


def test_stale_session_cannot_attach_answer_to_a_newer_question(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    stale = session.model_copy(deep=True)
    list(service.step_interview_stream(session, "已成功提交", request_id="first", store=store))
    latest = store.load(session.session_id).session
    before = len(llm.calls)
    with pytest.raises(SessionConflict, match="版本"):
        list(service.step_interview_stream(stale, "旧问题的延迟回答", request_id="late", store=store))
    assert store.load(session.session_id).session == latest
    assert store.get_request(session.session_id, "late") is None
    assert len(llm.calls) == before


def test_failed_answer_requires_retry_and_skip_preserves_accepted_answer(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.stream_error = RuntimeError("interrupted")
    with pytest.raises(RuntimeError):
        list(service.step_interview_stream(session, "原始已保存回答", request_id="failed", store=store))
    with pytest.raises(SessionConflict, match="未完成"):
        list(service.step_interview_stream(session, "不能替换原回答", request_id="another", store=store))
    llm.stream_error = None
    list(service.step_interview_stream(session, "/next", request_id="skip", store=store))
    assert session.history[0].answer == "原始已保存回答"
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    assert store.get_request(session.session_id, "failed").status == "cancelled"
    with pytest.raises(SessionConflict, match="取消"):
        list(service.step_interview_stream(session, "原始已保存回答", request_id="failed", store=store))


def test_pause_resume_and_offline_delete_cascade(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    before = len(llm.calls)
    list(service.step_interview_stream(session, "/pause", store=store))
    assert store.load(session.session_id).session.is_paused and not session.is_finished
    with pytest.raises(SessionConflict, match="暂停"):
        list(service.step_interview_stream(session, "暂停时不能作答", store=store))
    restored = service.resume_interview(session.session_id, store=InterviewStore(store.db_path))
    assert not restored.is_paused and len(llm.calls) == before
    summary = json.dumps(store.list_sessions(), ensure_ascii=False)
    assert profile.basics.name not in summary and profile.basics.phone not in summary
    assert store.delete(session.session_id)
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM interview_requests").fetchone()[0] == 0
    assert not store.delete(session.session_id)


def test_finish_can_cancel_an_unstarted_opening_without_model_call(profile, interview_env):
    store, llm = interview_env
    session, unstarted = service.start_interview(profile, store=store)
    list(service.step_interview_stream(session, "/finish", store=store))
    assert session.is_finished and session.history == [] and llm.calls == []
    assert store.get_request(session.session_id, "opening").status == "cancelled"
    unstarted.close()


def test_report_uses_accepted_records_and_replays_or_reexports_without_model(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.chunks, llm.stream_error = ["失败流的问题片段"], RuntimeError("interrupted")
    with pytest.raises(RuntimeError):
        list(service.step_interview_stream(session, "完整保存的候选人回答", request_id="failed", store=store))
    llm.stream_error = None
    report, path = service.finish_interview(session, store=store)
    prompt = json.dumps(llm.calls[-1]["messages"], ensure_ascii=False)
    assert "完整保存的候选人回答" in prompt and "失败流的问题片段" not in prompt
    assert "失败流的问题片段" not in path.read_text(encoding="utf-8")
    assert store.get_request(session.session_id, "failed").status == "cancelled"
    before = len(llm.calls)
    repeated, repeated_path = service.finish_interview(session, store=InterviewStore(store.db_path))
    assert report == repeated and path == repeated_path and len(llm.calls) == before
    path.unlink()
    _, repaired = service.finish_interview(session, store=store)
    assert repaired.is_file() and len(llm.calls) == before
    # 明确使用不同请求 ID 生成的报告保留独立文件，不覆盖此前的幂等结果。
    _, another = service.finish_interview(session, request_id="another_report", store=store)
    assert another != repaired and repaired.is_file()
    store.delete(session.session_id)
    assert repaired.is_file()  # 单独导出的报告不被会话删除隐式删除。


def test_report_failure_keeps_session_recoverable(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    def broken(*args):
        raise RuntimeError("synthetic report error")
    llm.responder = broken
    with pytest.raises(RuntimeError):
        service.finish_interview(session, store=store)
    assert store.load(session.session_id).session.is_finished
    assert store.get_request(session.session_id, "finish").status == "failed"
    llm.responder = lambda messages, model: InterviewEvaluationReport(
        overall_score=0, result="证据不足", summary="恢复后完成",
    )
    report, path = service.finish_interview(service.resume_interview(session.session_id, store=store), store=store)
    assert report.summary == "恢复后完成" and path.is_file()
    assert store.get_request(session.session_id, "finish").attempts == 2


def test_snapshot_corruption_is_rejected_without_echoing_private_values(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("UPDATE interview_sessions SET profile_hash='SYNTHETIC-PRIVATE-MARKER'")
    before = len(llm.calls)
    with pytest.raises(SessionStoreError) as exc:
        service.resume_interview(session.session_id, store=store)
    assert "SYNTHETIC-PRIVATE-MARKER" not in str(exc.value) and len(llm.calls) == before


@pytest.mark.parametrize("foreign", [False, True])
def test_unsupported_or_foreign_database_is_not_migrated(tmp_path, foreign):
    path = tmp_path / "foreign.db"
    with sqlite3.connect(path) as conn:
        if foreign:
            conn.execute("CREATE TABLE applications (id INTEGER, notes TEXT)")
            conn.execute("INSERT INTO applications VALUES (1,'synthetic application')")
        else:
            conn.execute("PRAGMA user_version=99")
    with pytest.raises(SessionStoreError, match="未进行迁移或覆盖"):
        InterviewStore(path).list_sessions()
    with sqlite3.connect(path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "interview_sessions" not in tables
        if foreign:
            assert conn.execute("SELECT notes FROM applications").fetchone()[0] == "synthetic application"
        else:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 99


def test_optimistic_commit_cannot_overwrite_a_later_revision(profile, interview_env):
    session, store, _ = opened(profile, interview_env)
    current, _ = store.begin_request(session.session_id, "old", "answer", "保存的回答")
    stale = current.session.model_copy(deep=True)
    current.session.is_paused = True
    store._update(current.session, current.session.revision)
    stale.current_stage = InterviewStage.FUNDAMENTALS
    with pytest.raises(SessionConflict, match="版本"):
        store.complete(stale, "old", stale.revision, "旧生成结果")
    latest = store.load(session.session_id).session
    assert latest.is_paused and latest.current_stage == InterviewStage.INTRO
    assert store.get_request(session.session_id, "old").status == "pending"


def test_unversioned_existing_tables_are_not_assumed_to_be_a_migration(tmp_path):
    path = tmp_path / "unversioned.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE interview_sessions (session_id TEXT)")
        conn.execute("INSERT INTO interview_sessions VALUES ('synthetic_legacy')")
    with pytest.raises(SessionStoreError):
        InterviewStore(path).list_sessions()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT session_id FROM interview_sessions").fetchone()[0] == "synthetic_legacy"


def test_parallel_session_request_is_rejected_without_blocking_other_database_writes(
    profile, interview_env, monkeypatch,
):
    session, store, llm = opened(profile, interview_env)
    entered, release = threading.Event(), threading.Event()
    def waiting_stream(self, messages, **kwargs):
        entered.set()
        assert release.wait(5), "test must release the synthetic model"
        yield "完整问题"
    monkeypatch.setattr(llm, "chat_stream", waiting_stream)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: "".join(service.step_interview_stream(
            session, "先到的回答", request_id="first", store=store,
        )))
        try:
            assert entered.wait(5)
            other = service.resume_interview(session.session_id, store=store)
            with pytest.raises(FileLockBusy):
                list(service.step_interview_stream(other, "并发回答", request_id="second", store=store))
            store.create(InterviewSession(session_id="independent_session"), profile)
        finally:
            release.set()
        assert future.result(timeout=5) == "完整问题"
    assert store.get_request(session.session_id, "second") is None
    assert store.load(session.session_id).session.history[0].answer == "先到的回答"


def test_session_file_lock_is_shared_between_processes_and_released_after_exit(interview_env):
    store, _ = interview_env
    code = """
import sys
from skills.mock_interviewer.session_store import InterviewStore
from tools.file_lock import FileLockBusy
try:
    with InterviewStore(sys.argv[1]).locked('cross_process'):
        pass
except FileLockBusy:
    sys.exit(23)
"""
    command = [sys.executable, "-X", "utf8", "-c", code, str(store.db_path)]
    with store.locked("cross_process"):
        assert subprocess.run(command, capture_output=True, timeout=10).returncode == 23
    assert subprocess.run(command, capture_output=True, timeout=10).returncode == 0


def test_process_crash_releases_lock_and_pending_answer_can_be_retried(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    code = """
import os, sys
from skills.mock_interviewer.session_store import InterviewStore
store = InterviewStore(sys.argv[1])
with store.locked(sys.argv[2]):
    store.begin_request(sys.argv[2], 'crashed', 'answer', '崩溃前已提交')
    os._exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", code, str(store.db_path), session.session_id],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0
    restored = service.resume_interview(session.session_id, store=store)
    assert restored.pending_request_id == "crashed"
    assert restored.history[0].answer == "崩溃前已提交"
    assert restored.current_stage == InterviewStage.INTRO
    list(service.step_interview_stream(restored, "/retry", store=store))
    assert restored.history[0].answer == "崩溃前已提交" and len(restored.history) == 2
    assert store.get_request(session.session_id, "crashed").attempts == 2


def test_finish_while_paused_closes_questions_without_reopening_them(profile, interview_env):
    session, store, _ = opened(profile, interview_env)
    list(service.step_interview_stream(session, "/pause", store=store))
    _, path = service.finish_interview(session, store=store)
    assert path.is_file() and session.is_finished and not session.is_paused


def test_model_change_requires_explicit_provider_and_is_then_persisted(profile, interview_env, monkeypatch):
    store, llm = interview_env
    class Identified(llm):
        model_name = "model_a"
        def __init__(self, provider=None):
            super().__init__(provider)
            self.provider_name = provider or "synthetic_provider"
            self.base_url = "https://synthetic.invalid/v1"
            self.config = SimpleNamespace(model=type(self).model_name)
    monkeypatch.setattr(handler, "LLMClient", Identified)
    session, stream = service.start_interview(profile, store=store)
    list(stream)
    original_fingerprint = session.model_fingerprint
    Identified.model_name = "model_b"
    with pytest.raises(ValueError, match="配置已变化"):
        list(service.step_interview_stream(session, "已保存回答", request_id="changed", store=store))
    assert store.load(session.session_id).session.model_fingerprint == original_fingerprint
    list(service.step_interview_stream(
        session, "已保存回答", request_id="changed", provider="synthetic_provider", store=store,
    ))
    assert store.load(session.session_id).session.model_fingerprint != original_fingerprint

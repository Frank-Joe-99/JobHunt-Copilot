"""验证 CLI 的实际输入循环，以及 stdio 服务退出后的会话恢复。"""

import json
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from core import interview_service as service
from core.state import InterviewStage
from main import app


def test_cli_pause_resume_skips_current_profile_and_interactive_wizard(profile, interview_env, monkeypatch):
    import run_interview
    store, llm = interview_env
    monkeypatch.setattr(run_interview, "load_user_profile", lambda: profile)
    runner = CliRunner()
    first = runner.invoke(app, [
        "interview", "--role", "strict_architect", "--company", "合成企业", "--target-role", "前端开发",
    ], input="/pause\n")
    assert first.exit_code == 0, first.output
    session_id = store.list_sessions()[0]["session_id"]
    assert session_id in first.output
    assert store.load(session_id).session.is_paused
    assert len(llm.calls) == 1 and store.get_request(session_id, "finish") is None
    monkeypatch.setattr(run_interview, "load_user_profile", lambda: (_ for _ in ()).throw(AssertionError("must use snapshot")))
    monkeypatch.setattr(run_interview, "select_role", lambda *args: (_ for _ in ()).throw(AssertionError("no wizard")))
    resumed = runner.invoke(app, ["interview", "--resume-session", session_id], input="/finish\n")
    assert resumed.exit_code == 0, resumed.output
    assert store.load(session_id).session.is_finished
    assert len(llm.calls) == 2 and store.get_request(session_id, "finish").status == "completed"


def test_cli_eof_pauses_instead_of_looping_or_generating_report(profile, interview_env, monkeypatch):
    import run_interview
    store, llm = interview_env
    monkeypatch.setattr(run_interview, "load_user_profile", lambda: profile)
    result = CliRunner().invoke(app, [
        "interview", "--role", "hrbp", "--company", "合成企业", "--target-role", "前端开发",
    ], input="")
    assert result.exit_code == 0, result.output
    assert store.list_sessions()[0]["is_paused"]
    assert len(llm.calls) == 1


def test_cli_failed_answer_can_retry_in_same_terminal(profile, interview_env, monkeypatch):
    import run_interview
    store, llm = interview_env
    monkeypatch.setattr(run_interview, "load_user_profile", lambda: profile)
    def fail_once(self, messages, **kwargs):
        type(self).calls.append({"messages": messages})
        if len(type(self).calls) == 2:
            yield "不完整追问"
            raise RuntimeError("离线模拟流中断")
        yield "完整问题"
    monkeypatch.setattr(llm, "chat_stream", fail_once)
    result = CliRunner().invoke(app, [
        "interview", "--role", "practical_lead", "--company", "合成企业", "--target-role", "前端开发",
    ], input="我提交的完整回答\n\n/retry\n/pause\n")
    assert result.exit_code == 0, result.output
    session = store.load(store.list_sessions()[0]["session_id"]).session
    assert session.is_paused and len(session.history) == 2
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    assert session.history[0].answer == "我提交的完整回答"
    assert "不完整追问" not in session.history[-1].question
    assert len(llm.calls) == 3


def test_cli_session_management_is_offline_and_does_not_expose_profile(profile, interview_env):
    store, _ = interview_env
    session, stream = service.start_interview(profile, store=store)
    list(stream)
    runner = CliRunner()
    for args in (["interview-sessions"], ["interview-sessions", "show", session.session_id]):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output
        assert profile.basics.name not in result.output and profile.basics.phone not in result.output
        assert session.session_id in result.output
    result = runner.invoke(app, ["interview-sessions", "delete", session.session_id])
    assert result.exit_code == 0 and store.list_sessions() == []
    assert runner.invoke(app, ["interview-sessions", "show"]).exit_code == 2
    assert runner.invoke(app, ["interview-sessions", "unknown"]).exit_code == 2


def test_cli_resumes_failed_mcp_debrief_without_reopening_questions(profile, interview_env, monkeypatch):
    from core.state import InterviewEvaluationReport
    store, llm = interview_env
    session, stream = service.start_interview(profile, store=store)
    list(stream)
    def fail_report(*args):
        raise RuntimeError("synthetic report failure")
    llm.responder = fail_report
    with pytest.raises(RuntimeError):
        service.finish_interview(session, store=store)
    llm.responder = lambda messages, model: InterviewEvaluationReport(
        overall_score=0, result="证据不足", summary="已恢复的报告",
    )
    import run_interview
    monkeypatch.setattr(run_interview, "get_candidate_input", lambda: pytest.fail("问答已经结束"))
    result = CliRunner().invoke(app, ["interview", "--resume-session", session.session_id])
    assert result.exit_code == 0, result.output
    assert store.get_request(session.session_id, "finish").status == "completed"


async def call(session, name, arguments):
    response = await session.call_tool(name, arguments)
    assert not response.is_error, response.content
    return json.loads(response.content[0].text)


async def test_stdio_restart_preserves_failed_answer_retries_and_cached_report(interview_mcp_params, tmp_path):
    params = interview_mcp_params
    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert len(tools) == 13
        assert "resume_session_id" in tools["tool_interview_start"].input_schema["properties"]
        assert "request_id" in tools["tool_interview_answer"].input_schema["properties"]
        started = await call(client, "tool_interview_start", {
            "target_company": "合成企业", "target_role": "前端开发", "jd_text": "React 测试", "mode": "practice",
        })
        session_id = started["session_id"]

    # 第二个服务进程从 SQLite 读取，不依赖第一进程的 _interview_sessions。
    answer = "TRIGGER_STREAM_FAILURE：已经提交的回答"
    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        restored = await call(client, "tool_interview_start", {"resume_session_id": session_id})
        assert restored["target_role"] == "前端开发" and restored["target_company"] == "合成企业"
        failed = await call(client, "tool_interview_answer", {
            "session_id": session_id, "user_answer": answer, "request_id": "stable_answer",
        })
        assert failed["status"] == "recoverable_error" and failed["pending_request_id"] == "stable_answer"
        assert failed["turns_count"] == 1 and failed["interviewer_reply"] == ""
        paused = await call(client, "tool_interview_answer", {"session_id": session_id, "user_answer": "/pause"})
        assert paused["is_paused"] and not paused["is_finished"]

    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        restored = await call(client, "tool_interview_start", {"resume_session_id": session_id})
        assert not restored["is_paused"] and restored["pending_request_id"] == "stable_answer"
        retried = await call(client, "tool_interview_answer", {"session_id": session_id, "user_answer": "/retry"})
        assert retried["status"] == "success" and retried["turns_count"] == 2
        replayed = await call(client, "tool_interview_answer", {
            "session_id": session_id, "user_answer": answer, "request_id": "stable_answer",
        })
        assert replayed["interviewer_reply"] == retried["interviewer_reply"]
        finished = await call(client, "tool_interview_finish", {"session_id": session_id})
        report_path = Path(finished["report_file_path"])
        assert report_path.is_file()
        transcript = report_path.read_text(encoding="utf-8")
        assert answer in transcript and "失败问题片段" not in transcript

    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        cached = await call(client, "tool_interview_finish", {"session_id": session_id})
        assert cached == finished
    assert (tmp_path / "model_calls.txt").read_text(encoding="utf-8").splitlines() == [
        "stream", "stream", "stream", "report",
    ]

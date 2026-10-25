"""受控自适应的确定性边界；合成模型结果不代表真实生成质量或延迟。"""

import json
import sqlite3

import httpx
import pytest
from typer.testing import CliRunner

from core import interview_service as service
from core.state import (
    AppSettings, InterviewDecision, InterviewEvaluationReport, InterviewPolicy, InterviewStage, JobDescription,
    LLMConfig, LLMProviderConfig,
)
from main import app
from skills.mock_interviewer import adaptive, handler, session_store
from skills.mock_interviewer.adaptive import InterviewPolicyError
from skills.mock_interviewer.session_store import InterviewStore, SessionStoreError
from tools import llm_client


def opened(profile, interview_env, *, policy=None, mode="simulation", flow="adaptive"):
    store, llm = interview_env
    llm.responder = lambda messages, model: InterviewDecision(
        action="advance", question="请说明这个模块的边界与实现。", next_stage="resume_deep_dive",
    )
    session, stream = service.start_interview(
        profile, target_role="前端开发", target_company="合成企业", flow=flow, mode=mode,
        policy=policy, job_description=JobDescription(company="合成企业", role="前端开发", raw_text="React 可访问性"),
        store=store,
    )
    list(stream)
    return session, store, llm


def test_single_decision_sees_full_context_and_can_advance_immediately(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    result = list(service.step_interview_stream(session, "已充分说明个人贡献", request_id="one", store=store))
    assert result == ["请说明这个模块的边界与实现。"]
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE and session.consecutive_followups == 0
    assert len(llm.calls) == 2  # 开场一次，决策一次，没有串联评审模型。
    prompt = json.dumps(llm.calls[-1]["messages"], ensure_ascii=False)
    assert "已充分说明个人贡献" in prompt and "合成项目5" in prompt and "React 可访问性" in prompt
    assert profile.basics.phone not in prompt and profile.basics.name not in prompt
    stats = store.statistics(session.session_id)
    assert stats["known_model_requests"] == 2 and stats["generation_attempts"] == 2
    assert stats["first_text_seconds_median"] is not None


def test_followups_are_optional_and_program_forces_coverage_after_limit(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    choices = iter([
        InterviewDecision(action="clarify", question="你具体负责哪个模块？"),
        InterviewDecision(action="follow_up", question="这个决策的取舍是什么？"),
        InterviewDecision(action="advance", question="请介绍另一个项目的实现边界。", next_stage="resume_deep_dive"),
    ])
    llm.responder = lambda messages, model: next(choices)
    for index in range(3):
        list(service.step_interview_stream(session, f"真实回答{index}", store=store))
    context = json.loads(llm.calls[-1]["messages"][0]["content"].splitlines()[-1])
    assert context["allowed_actions"] == ["advance"]
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    assert session.consecutive_followups == 0 and len(session.history) == 4


@pytest.mark.parametrize("decision,reason", [
    (InterviewDecision(action="finish", question="过早结束"), "invalid_action"),
    (InterviewDecision(action="hint", question="模拟时不应代答"), "invalid_action"),
    (InterviewDecision(action="advance", question="跳过阶段", next_stage="behavioral"), "stage_jump"),
    (InterviewDecision(action="clarify", question="澄清却改阶段", next_stage="fundamentals"), "unexpected_stage_change"),
    (InterviewDecision(action="follow_up", question="请介绍与你应聘岗位相关的经历！"), "duplicate_question"),
    (InterviewDecision(action="follow_up", question="？？！！"), "invalid_question"),
])
def test_invalid_decisions_do_not_commit_stage_or_lose_answer(profile, interview_env, decision, reason):
    session, store, llm = opened(profile, interview_env)
    llm.responder = lambda messages, model: decision
    with pytest.raises(InterviewPolicyError):
        list(service.step_interview_stream(session, "需要保留的回答", request_id="bad", store=store))
    stored = store.load(session.session_id).session
    assert stored.current_stage == InterviewStage.INTRO and len(stored.history) == 1
    assert stored.history[0].answer == "需要保留的回答"
    assert store.get_request(session.session_id, "bad").metrics.policy_reason == reason


def test_practice_can_hint_and_retry_without_replacing_original_answer(profile, interview_env):
    session, store, llm = opened(profile, interview_env, mode="practice")
    choices = iter([
        InterviewDecision(action="hint", question="可以先从输入、输出和约束整理思路。"),
        InterviewDecision(action="retry_answer", question="现在请重新组织你的回答。"),
    ])
    llm.responder = lambda messages, model: next(choices)
    list(service.step_interview_stream(session, "请给一个提示", store=store))
    list(service.step_interview_stream(session, "我想重答", store=store))
    assert [turn.kind for turn in session.history] == ["question", "hint", "retry"]
    assert session.history[0].answer == "请给一个提示" and session.history[1].answer == "我想重答"
    assert session.current_stage == InterviewStage.INTRO


def test_reverse_qa_gets_a_response_at_question_limit(profile, interview_env):
    session, store, llm = opened(profile, interview_env, policy=InterviewPolicy(max_turns=5))
    order = iter(["resume_deep_dive", "fundamentals", "behavioral", "reverse_qa"])
    llm.responder = lambda messages, model: InterviewDecision(
        action="advance", question="下一阶段问题：" + (stage := next(order)), next_stage=stage,
    )
    for index in range(4):
        list(service.step_interview_stream(session, f"阶段回答{index}", store=store))
    llm.responder = lambda messages, model: InterviewDecision(
        action="respond", question="我无法确认公司内部安排，可以向招聘方核实。感谢参与。",
    )
    list(service.step_interview_stream(session, "岗位的培养机制是什么？", store=store))
    assert session.is_finished and len(session.history) == 5
    assert session.history[-1].answer == "岗位的培养机制是什么？"
    assert "无法确认" in session.history[-1].feedback
    assert len(llm.calls) == 6


@pytest.mark.parametrize("policy,reason", [
    (InterviewPolicy(max_turns=1), "turn_budget"),
    (InterviewPolicy(max_requests_total=1), "request_budget"),
])
def test_global_limits_close_without_extra_model_call(profile, interview_env, policy, reason):
    session, store, llm = opened(profile, interview_env, policy=policy)
    list(service.step_interview_stream(session, "预算结束前的回答", store=store))
    assert session.is_finished and session.stop_reason == reason
    assert session.history[0].answer == "预算结束前的回答" and len(llm.calls) == 1


def test_active_time_budget_excludes_pause_and_survives_resume(profile, interview_env, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(adaptive.time, "time", lambda: clock[0])
    session, store, llm = opened(profile, interview_env, policy=InterviewPolicy(max_duration_seconds=5))
    clock[0] = 102
    list(service.step_interview_stream(session, "/pause", store=store))
    clock[0] = 1000
    session = service.resume_interview(session.session_id, store=store)
    clock[0] = 1001
    list(service.step_interview_stream(session, "暂停后继续回答", store=store))
    assert not session.is_finished and session.elapsed_active_seconds == 2
    clock[0] = 1004
    list(service.step_interview_stream(session, "总时长到达上限", store=store))
    assert session.is_finished and session.stop_reason == "time_budget" and len(llm.calls) == 2


def test_retry_replay_and_failed_calls_have_consistent_metrics(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.responder = lambda messages, model: InterviewDecision(action="finish", question="不允许提前结束")
    with pytest.raises(InterviewPolicyError):
        list(service.step_interview_stream(session, "完整回答", request_id="stable", store=store))
    llm.responder = lambda messages, model: InterviewDecision(action="advance", question="请说明实现边界。")
    list(service.step_interview_stream(session, "/retry", store=store))
    stats = store.statistics(session.session_id)
    assert stats["known_model_requests"] == stats["generation_attempts"] == 3
    assert stats["failed_generations"] == 1 and stats["retry_count"] == 1
    assert stats["failure_rate"] == pytest.approx(1 / 3)
    list(service.step_interview_stream(session, "完整回答", request_id="stable", store=store))
    assert store.statistics(session.session_id) == stats and len(llm.calls) == 3


def test_failed_generation_cannot_bypass_total_request_limit(profile, interview_env):
    session, store, llm = opened(profile, interview_env, policy=InterviewPolicy(max_requests_total=2))
    llm.responder = lambda messages, model: InterviewDecision(action="finish", question="不允许提前结束")
    with pytest.raises(InterviewPolicyError):
        list(service.step_interview_stream(session, "完整回答", request_id="stable", store=store))
    list(service.step_interview_stream(session, "/retry", store=store))
    assert session.is_finished and session.stop_reason == "request_budget"
    assert len(llm.calls) == 2 and store.statistics(session.session_id)["known_model_requests"] == 2


def test_crash_leaves_explicit_unknown_request_upper_bound(profile, interview_env):
    session, store, llm = opened(profile, interview_env, policy=InterviewPolicy(max_requests_total=2))
    store.begin_request(session.session_id, "crashed", "answer", "已经保存的回答")
    restored = service.resume_interview(session.session_id, store=store)
    list(service.step_interview_stream(restored, "/retry", store=store))
    stats = store.statistics(session.session_id)
    assert stats["known_model_requests"] == 1 and stats["unknown_request_upper_bound"] == 1
    assert restored.is_finished and len(llm.calls) == 1


def test_v1_migration_preserves_facts_history_and_cached_results(profile, interview_env):
    session, store, llm = opened(profile, interview_env, flow="fixed")
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("ALTER TABLE interview_requests DROP COLUMN metrics_json")
        conn.execute("PRAGMA user_version=1")
        old_session = json.loads(conn.execute("SELECT session_json FROM interview_sessions").fetchone()[0])
        for key in ("flow", "policy", "enforce_policy", "started_at", "elapsed_active_seconds", "active_started_at", "consecutive_followups", "stop_reason"):
            old_session.pop(key)
        for turn in old_session["history"]:
            turn.pop("kind")
        conn.execute("UPDATE interview_sessions SET session_json=?", (json.dumps(old_session, ensure_ascii=False),))
        original = conn.execute("SELECT profile_json,profile_hash,session_json FROM interview_sessions").fetchone()
    restored = InterviewStore(store.db_path).load(session.session_id)
    assert restored.session.history == session.history and restored.profile == profile
    assert restored.session.flow == "fixed" and not restored.session.enforce_policy
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT profile_json,profile_hash,session_json FROM interview_sessions").fetchone() == original
    assert store.get_request(session.session_id, "opening").status == "completed"
    assert store.statistics(session.session_id)["unmeasured_legacy_requests"] == 1


def test_migration_failure_rolls_back_without_adding_column(tmp_path):
    path = tmp_path / "broken_v1.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE interview_sessions (session_id TEXT)")
        conn.execute("CREATE TABLE interview_requests (request_id TEXT)")
        conn.execute("INSERT INTO interview_sessions VALUES ('synthetic_keep')")
        conn.execute("PRAGMA user_version=1")
    with pytest.raises(SessionStoreError, match="未猜测迁移"):
        InterviewStore(path).list_sessions()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT session_id FROM interview_sessions").fetchone()[0] == "synthetic_keep"
        assert [row[1] for row in conn.execute("PRAGMA table_info(interview_requests)")] == ["request_id"]


def test_comparison_reports_conditions_and_statistics_without_claiming_quality(profile, interview_env):
    policy = InterviewPolicy(max_requests_per_turn=1)
    fixed, store, llm = opened(profile, interview_env, policy=policy, flow="fixed")
    list(service.step_interview_stream(fixed, "相同的合成回答", store=store))
    adaptive_session, _, _ = opened(profile, interview_env, policy=policy)
    list(service.step_interview_stream(adaptive_session, "相同的合成回答", store=store))
    comparison = service.compare_interviews(fixed.session_id, adaptive_session.session_id, store=store)
    assert comparison["same_context_and_answers"] and comparison["same_enforced_budget"]
    assert comparison["same_model_identity"] is None
    assert "人工比较" in comparison["quality_review"]
    result = CliRunner().invoke(app, ["interview-sessions", "compare", fixed.session_id, "--with-session", adaptive_session.session_id])
    assert result.exit_code == 0, result.output
    assert profile.basics.phone not in result.output and "first_text_seconds_median" in result.output


@pytest.mark.parametrize("finish", ["stop", "length"])
def test_real_client_native_schema_integrates_with_atomic_interview_state(profile, monkeypatch, tmp_path, finish):
    config = LLMProviderConfig(
        api_key="synthetic-key-not-real", base_url="https://unit.invalid/v1", model="synthetic-model",
        supports_json_schema=True,
    )
    monkeypatch.setattr(llm_client, "load_app_settings", lambda: AppSettings(llm=LLMConfig(default_provider="unit", providers={"unit": config})))
    payloads = []
    def transport(request):
        payload = json.loads(request.content)
        payloads.append(payload)
        if payload["stream"]:
            return httpx.Response(200, content=b'data: {"choices":[{"delta":{"content":"opening"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({
            "action": "advance", "question": "next question", "next_stage": "resume_deep_dive",
        })}, "finish_reason": finish}]})
    def factory(provider=None):
        client = llm_client.LLMClient(provider)
        client._client = httpx.Client(transport=httpx.MockTransport(transport))
        return client
    monkeypatch.setattr(handler, "LLMClient", factory)
    store = InterviewStore(tmp_path / "native.db")
    session, stream = service.start_interview(profile, flow="adaptive", store=store)
    list(stream)
    if finish == "stop":
        assert list(service.step_interview_stream(session, "真实回答", request_id="native", store=store)) == ["next question"]
        assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    else:
        with pytest.raises(llm_client.LLMResponseError):
            list(service.step_interview_stream(session, "真实回答", request_id="native", store=store))
        assert store.load(session.session_id).session.current_stage == InterviewStage.INTRO
        assert len(store.load(session.session_id).session.history) == 1
    assert payloads[-1]["response_format"]["type"] == "json_schema"
    assert len(payloads) == store.statistics(session.session_id)["known_model_requests"] == 2


def test_adaptive_skip_and_finish_override_failed_model_decision(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    llm.responder = lambda messages, model: InterviewDecision(action="finish", question="不允许提前结束")
    with pytest.raises(InterviewPolicyError):
        list(service.step_interview_stream(session, "原回答仍需保留", request_id="failed", store=store))
    llm.responder = lambda messages, model: InterviewDecision(action="advance", question="跳过后询问项目边界。")
    list(service.step_interview_stream(session, "/next", store=store))
    assert session.history[0].answer == "原回答仍需保留"
    assert session.current_stage == InterviewStage.RESUME_DEEP_DIVE
    assert store.get_request(session.session_id, "failed").status == "cancelled"
    before = len(llm.calls)
    list(service.step_interview_stream(session, "/finish", store=store))
    assert session.is_finished and len(llm.calls) == before


def test_cli_adaptive_options_are_saved_and_resume_keeps_original_policy(profile, interview_env, monkeypatch):
    import run_interview
    store, llm = interview_env
    monkeypatch.setattr(run_interview, "load_user_profile", lambda: profile)
    llm.responder = lambda messages, model: InterviewDecision(action="advance", question="请说明个人贡献边界。")
    runner = CliRunner()
    result = runner.invoke(app, [
        "interview", "--flow", "adaptive", "--role", "hrbp", "--company", "合成企业", "--target-role", "前端开发",
        "--max-followups", "0", "--request-budget", "1", "--max-turns", "8",
    ], input="完整的合成回答\n\n/pause\n")
    assert result.exit_code == 0, result.output
    stored = store.load(store.list_sessions()[0]["session_id"]).session
    assert stored.flow == "adaptive" and stored.policy.max_followups == 0 and stored.policy.max_turns == 8
    invalid = runner.invoke(app, ["interview", "--resume-session", stored.session_id, "--max-turns", "2"])
    assert invalid.exit_code == 2
    assert store.load(stored.session_id).session.policy.max_turns == 8
    restored = runner.invoke(app, ["interview", "--resume-session", stored.session_id], input="/pause\n")
    assert restored.exit_code == 0 and len(llm.calls) == 2


def test_invalid_cli_flow_does_not_open_wizard(monkeypatch):
    import run_interview
    monkeypatch.setattr(run_interview, "main", lambda **kwargs: pytest.fail("invalid flow"))
    assert CliRunner().invoke(app, ["interview", "--flow", "unknown"]).exit_code == 2


def test_slow_valid_result_is_not_displayed_or_committed(profile, interview_env, monkeypatch):
    session, store, llm = opened(profile, interview_env, policy=InterviewPolicy(request_timeout_seconds=1))
    clock = [0.0]
    monkeypatch.setattr(adaptive.time, "monotonic", lambda: clock[0])
    def slow(messages, model):
        clock[0] = 2
        return InterviewDecision(action="advance", question="完整但已超时的问题。")
    llm.responder = slow
    stream = service.step_interview_stream(session, "已接受的回答", request_id="slow", store=store)
    with pytest.raises(RuntimeError, match="限时"):
        next(stream)
    current = store.load(session.session_id).session
    assert len(current.history) == 1 and current.history[0].answer == "已接受的回答"
    assert store.get_request(session.session_id, "slow").metrics.first_text_seconds is None


def test_valid_adaptive_question_is_committed_before_visible_output(profile, interview_env):
    session, store, llm = opened(profile, interview_env)
    stream = service.step_interview_stream(session, "已接受的回答", request_id="visible", store=store)
    assert next(stream)
    assert store.get_request(session.session_id, "visible").status == "completed"
    assert len(store.load(session.session_id).session.history) == 2
    stream.close()
    stats = store.statistics(session.session_id)
    list(service.step_interview_stream(session, "已接受的回答", request_id="visible", store=store))
    assert len(llm.calls) == 2 and store.statistics(session.session_id) == stats


def test_practice_debrief_distinguishes_tool_hints_from_candidate_facts(profile, interview_env):
    session, store, llm = opened(profile, interview_env, mode="practice")
    llm.responder = lambda messages, model: InterviewDecision(action="hint", question="先列出输入和输出，再比较取舍。")
    list(service.step_interview_stream(session, "请求提示", store=store))
    llm.responder = lambda messages, model: InterviewEvaluationReport(overall_score=0, result="证据不足", summary="尚未观察到独立回答")
    _, path = service.finish_interview(session, store=store)
    prompt = llm.calls[-1]["messages"][-1]["content"]
    assert "训练提示:" in prompt and "不是候选人事实" in prompt
    assert "面试官·训练提示" in path.read_text(encoding="utf-8")


async def test_adaptive_mcp_round_survives_restart_and_replay(interview_mcp_params, tmp_path):
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    async def call(client, tool, arguments):
        result = await client.call_tool(tool, arguments)
        assert not result.is_error, result.content
        return json.loads(result.content[0].text)
    async with stdio_client(interview_mcp_params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        started = await call(client, "tool_interview_start", {"flow": "adaptive", "max_followups": 0})
        session_id = started["session_id"]
        assert started["flow"] == "adaptive"
    async with stdio_client(interview_mcp_params) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        resumed = await call(client, "tool_interview_start", {"resume_session_id": session_id})
        assert resumed["flow"] == "adaptive" and resumed["policy"]["max_followups"] == 0
        arguments = {"session_id": session_id, "user_answer": "完整合成回答", "request_id": "adaptive_once"}
        answer = await call(client, "tool_interview_answer", arguments)
        assert answer["status"] == "success" and answer["current_stage"] == "resume_deep_dive"
        repeated = await call(client, "tool_interview_answer", arguments)
        assert repeated["metrics"] == answer["metrics"] and repeated["metrics"]["known_model_requests"] == 2
        await call(client, "tool_interview_finish", {"session_id": session_id})
    assert (tmp_path / "model_calls.txt").read_text(encoding="utf-8").splitlines() == ["stream", "decision", "report"]

import json

import pytest

from core import config
from core.state import InterviewRole, JobDescription
from skills.mock_interviewer import handler


@pytest.mark.parametrize("target,requirement", [
    ("前端开发", "React 与布局"),
    ("后端开发", "接口设计与数据库"),
    ("数值算法研究", "数值稳定性与误差分析"),
])
def test_interview_context_follows_role_and_keeps_all_projects(
    profile, llm_stub, monkeypatch, target, requirement,
):
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    job = JobDescription(company="合成公司", role=target, raw_text=requirement)
    session, stream = handler.start_interview(
        profile, target_role=target, job_description=job, role=InterviewRole.STRICT_ARCHITECT,
    )
    assert "".join(stream)
    prompt = "\n".join(message["content"] for message in llm_stub.calls[0]["messages"])
    assert target in prompt and requirement in prompt
    assert "合成项目5" in prompt
    assert "CUDA" not in prompt
    assert "核心开发" not in prompt
    assert profile.basics.name not in prompt
    assert profile.basics.email not in prompt
    assert profile.basics.phone not in prompt
    assert session.job_description.raw_text == requirement


def test_missing_profile_never_generates_fake_identity(llm_stub, monkeypatch):
    def missing():
        raise FileNotFoundError("合成的配置缺失")
    monkeypatch.setattr(handler, "load_user_profile", missing)
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    with pytest.raises(FileNotFoundError):
        handler.start_interview()
    assert not llm_stub.calls


def test_practice_mode_and_finish_remain_available(profile, llm_stub, monkeypatch):
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    session, stream = handler.start_interview(profile, mode="practice")
    list(stream)
    assert "训练模式" in llm_stub.calls[0]["messages"][0]["content"]
    before = len(llm_stub.calls)
    assert "结束" in "".join(handler.step_interview_stream(session, "/finish", profile))
    assert session.is_finished
    assert len(llm_stub.calls) == before


def test_incomplete_opening_not_registered_as_full_question(profile, llm_stub, monkeypatch):
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    llm_stub.chunks = ["未完整的问题"]
    llm_stub.stream_error = RuntimeError("synthetic interruption")
    session, stream = handler.start_interview(profile)
    with pytest.raises(RuntimeError):
        list(stream)
    assert session.history == []
    assert llm_stub.closed


def test_new_question_still_contains_jd(profile, llm_stub, monkeypatch):
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    job = JobDescription(company="合成", role="前端开发", raw_text="测试可访问性需求")
    session, stream = handler.start_interview(profile, job_description=job)
    list(stream)
    list(handler.step_interview_stream(session, "介绍我的真实项目", profile))
    assert "测试可访问性需求" in llm_stub.calls[-1]["messages"][0]["content"]
    assert len(session.history) == 2


@pytest.mark.parametrize("text", [
    "basics: {name: SYNTHETIC-PRIVATE-MARKER}",
    "basics: [SYNTHETIC-PRIVATE-MARKER",
])
def test_config_validation_errors_do_not_echo_values(tmp_path, text):
    path = tmp_path / "profile.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        config.load_user_profile(path)
    assert "SYNTHETIC-PRIVATE-MARKER" not in str(exc.value)


def test_debrief_never_fills_missing_dimensions_with_fake_scores(profile, llm_stub, monkeypatch, tmp_path):
    from core.state import InterviewEvaluationReport
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    monkeypatch.setattr(handler, "PROJECT_ROOT", tmp_path)
    session, stream = handler.start_interview(profile)
    list(stream)
    llm_stub.responder = lambda messages, model: InterviewEvaluationReport(
        overall_score=0, result="证据不足", summary="未观察到，需继续练习", dimension_scores={},
    )
    report, path = handler.finish_interview(session)
    content = path.read_text(encoding="utf-8")
    assert "未观察到" in content
    assert "| 综合能力 | 80" not in content
    assert report.dimension_scores == {}

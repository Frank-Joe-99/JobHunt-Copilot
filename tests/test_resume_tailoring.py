import json
from pathlib import Path

import pytest

from core.context import candidate_context
from core.resume_edits import apply_resume_edits, build_resume_snapshot, review_polish_report
from core.state import JobDescription, MatchResult, PolishedItem, ResumePolishReport, SkillGap
from skills.jd_matcher import handler as matcher
from skills.resume_polisher import handler as polisher


def report_for(snapshot, index=0, polished="参与接口和页面开发，并验证功能"):
    target = snapshot.targets[index]
    return ResumePolishReport(
        summary="合成修改建议", snapshot_id=snapshot.snapshot_id,
        items=[PolishedItem(
            snapshot_id=snapshot.snapshot_id, target_ref=target.target_ref,
            expected_original_hash=target.original_hash, source="模型重新抄写的来源",
            original="模型重新抄写的标点不一致！", polished=polished,
        )],
    )


def test_business_context_keeps_all_evidence_without_contact_fields(profile):
    context = candidate_context(profile)
    text = json.dumps(context, ensure_ascii=False)
    assert len(context["projects"]) == 6
    assert "合成项目5" in text
    for value in (profile.basics.name, profile.basics.phone, profile.basics.email):
        assert value not in text
    assert "repo_url" not in context["projects"][0]
    assert "role" not in context["projects"][0]  # 未说明不变成“核心开发”。


def test_polish_receives_different_jds_and_full_facts(profile, llm_stub, monkeypatch):
    monkeypatch.setattr(polisher, "LLMClient", llm_stub)
    captured = []

    def respond(messages, model_class):
        payload = json.loads(messages[-1]["content"])
        captured.append(payload)
        target = payload["highlights"][-1]
        focus = payload["target_job_description"]["hard_requirements"][0]
        return ResumePolishReport(
            summary=focus, snapshot_id=payload["snapshot_id"],
            items=[PolishedItem(
                **target, polished="参与页面开发，验证功能" if focus == "React" else "参与接口开发，验证功能",
                improvement_reason=focus,
            )],
        )

    llm_stub.responder = respond
    reports = []
    for requirement in ("React", "FastAPI"):
        jd = JobDescription(
            company="合成企业", role="研发工程师", hard_requirements=[requirement],
            raw_text=f"合成岗位原文：使用 {requirement}",
        )
        reports.append(polisher.polish_experiences(
            profile, job_description=jd,
            match_result=MatchResult(score=80, overview="合成分析", resume_tuning_advice=[requirement]),
        ))
    assert reports[0].items[0].polished != reports[1].items[0].polished
    for payload in captured:
        assert len(payload["candidate_facts"]["projects"]) == 6
        assert len(payload["highlights"]) == 6
        assert payload["raw_jd_text"] == payload["target_job_description"]["raw_text"]
        assert payload["analysis_suggestions_not_facts"]["score"] == 80
        assert profile.basics.email not in json.dumps(payload)
    # Stub 验证传参和定位，不代表真实模型生成质量已通过在线评测。


def test_match_keeps_raw_jd_and_all_projects(profile, llm_stub, monkeypatch):
    monkeypatch.setattr(matcher, "LLMClient", llm_stub)
    llm_stub.responder = lambda messages, model: MatchResult(score=70, overview="证据不足保持未知")
    jd = JobDescription(company="测试", role="研发", raw_text="原始条件：有相关经历优先")
    matcher.match_profile_with_jd(profile, jd)
    payload = json.loads(llm_stub.calls[0]["messages"][-1]["content"])
    assert payload["target_job_description"]["raw_text"] == jd.raw_text
    assert len(payload["candidate_profile"]["projects"]) == 6
    assert profile.basics.name not in json.dumps(payload)


def test_same_original_text_only_changes_target_id(profile):
    snapshot = build_resume_snapshot(profile)
    original = profile.model_copy(deep=True)
    report = report_for(snapshot, index=5)
    assert apply_resume_edits(profile, report, snapshot) == 1
    assert profile.projects[0].highlights == original.projects[0].highlights
    assert profile.projects[5].highlights != original.projects[5].highlights
    assert report.items[0].original == original.projects[5].highlights[0]


@pytest.mark.parametrize("invalid", ["unknown", "duplicate", "hash", "snapshot", "missing"])
def test_invalid_proposals_fail_without_partial_write(profile, invalid):
    snapshot = build_resume_snapshot(profile)
    report = report_for(snapshot)
    valid = report.items[0].model_copy(deep=True)
    report.items.insert(0, valid)
    item = report.items[-1]
    if invalid == "unknown":
        item.target_ref = "__class__.__dict__"
    elif invalid == "hash":
        item.expected_original_hash = "invalid"
        report.items = [item]
    elif invalid == "snapshot":
        item.snapshot_id = "stale"
        report.items = [item]
    elif invalid == "missing":
        item.target_ref = None
        report.items = [item]
    before = profile.model_dump()
    with pytest.raises(ValueError):
        apply_resume_edits(profile, report, snapshot)
    assert profile.model_dump() == before


def test_reordered_profile_invalidates_snapshot(profile):
    snapshot = build_resume_snapshot(profile)
    report = report_for(snapshot)
    profile.projects.reverse()
    with pytest.raises(ValueError, match="过期"):
        apply_resume_edits(profile, report, snapshot)


@pytest.mark.parametrize("polished", [
    "主导接口和页面开发，性能提高90%",
    "独立实现 Redis 集群",
])
def test_fact_risks_preserve_original(profile, polished):
    snapshot = build_resume_snapshot(profile)
    report = report_for(snapshot, polished=polished)
    before = profile.model_dump()
    assert apply_resume_edits(profile, report, snapshot) == 0
    assert report.needs_confirmation
    assert report.items[0].review_reasons
    assert profile.model_dump() == before


def test_learning_boundary_is_preserved(profile):
    profile.projects[0].highlights = ["学习教程并复现功能，尚未测量"]
    snapshot = build_resume_snapshot(profile)
    report = report_for(snapshot, polished="完成系统功能验证")
    review_polish_report(profile, report, snapshot)
    assert report.items[0].needs_confirmation


def test_unknown_skill_does_not_trigger_repository_search(monkeypatch):
    from skills.project_recommender import handler as recommender
    monkeypatch.setattr(recommender, "GitHubClient", lambda: pytest.fail("unknown is not missing"))
    report = recommender.recommend_projects_report([SkillGap(skill="缓存", status="unknown")])
    assert report.recommendations == []
    assert "需先澄清" in report.overview


def test_tailor_flow_exports_diff_and_records_preparation(profile, llm_stub, monkeypatch, tmp_path):
    from core import workflow
    from skills.application_tracker import handler as tracker
    from skills.application_tracker import database

    original = profile.model_dump()
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(database, "DEFAULT_DB_PATH", tmp_path / "tracker.db")
    monkeypatch.setattr(workflow, "parse_jd", lambda text, provider=None: JobDescription(
        company="合成企业", role="研发工程师", hard_requirements=["React"], raw_text=text,
    ))
    monkeypatch.setattr(workflow, "match_profile_with_jd", lambda *args, **kwargs: MatchResult(
        score=80, overview="合成匹配", missing_skills=[SkillGap(skill="缓存", status="unknown")],
    ))

    def fake_polish(**kwargs):
        assert kwargs["jd_text"] == "合成 JD 原文"
        assert kwargs["job_description"].raw_text == "合成 JD 原文"
        assert kwargs["match_result"].score == 80
        return report_for(kwargs["snapshot"], index=5)

    monkeypatch.setattr(workflow, "polish_experiences", fake_polish)
    def unavailable(**kwargs):
        raise RuntimeError("not included in logs")
    monkeypatch.setattr(workflow, "recommend_projects_report", unavailable)
    rendered = []
    def render(profile, output_name, template):
        rendered.append(profile.model_copy(deep=True))
        paths = {kind: tmp_path / f"{output_name}.{kind}" for kind in ("pdf", "docx")}
        for path in paths.values():
            path.write_bytes(b"synthetic renderer output")
        return paths
    monkeypatch.setattr(workflow, "generate_resume", render)
    package = workflow.tailor_application_flow("合成 JD 原文", profile=profile)
    assert profile.model_dump() == original
    assert Path(package.resume_diff_path).is_file()
    assert Path(package.resume_snapshot_path).is_file()
    assert "projects[5]" in Path(package.resume_diff_path).read_text(encoding="utf-8")
    backup = json.loads(Path(package.resume_snapshot_path).read_text(encoding="utf-8"))
    assert backup["profile"]["projects"][5]["highlights"] == profile.projects[5].highlights
    assert rendered[0].projects[5].highlights != profile.projects[5].highlights
    records = tracker.list_applications(db_path=database.DEFAULT_DB_PATH)
    assert len(records) == 1
    assert records[0].status.value == "wishlist"
    assert tracker.get_funnel_analytics(db_path=database.DEFAULT_DB_PATH).applied_count == 0
    assert package.preparation_status == "draft"
    report = Path(package.package_report_path).read_text(encoding="utf-8")
    assert "并不表示已覆盖" not in report or "技能缺口" in report
    assert "服务不可用" in report
    assert "不表示已经投递" in report
    # 原有禁用开关仍有效，不会追加第二条记录。
    workflow.tailor_application_flow("合成 JD 原文", profile=profile, auto_track=False, enable_github_search=False)
    assert len(tracker.list_applications(db_path=database.DEFAULT_DB_PATH)) == 1

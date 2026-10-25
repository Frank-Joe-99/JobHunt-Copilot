"""经历润色与 ATS 诊断；所有模型输入经过业务字段白名单处理。"""

import json

from core.config import load_user_profile
from core.context import candidate_context
from core.resume_edits import build_resume_snapshot, review_polish_report
from core.state import (
    ATSScoreReport, JobDescription, MatchResult, ResumePolishReport, ResumeSnapshot, UserProfile,
)
from skills.resume_polisher.prompt import ATS_DIAGNOSIS_SYSTEM, STAR_REWRITE_SYSTEM
from tools.llm_client import LLMClient


def polish_experiences(
    profile: UserProfile | None = None,
    provider: str | None = None,
    *,
    job_description: JobDescription | None = None,
    match_result: MatchResult | None = None,
    jd_text: str | None = None,
    snapshot: ResumeSnapshot | None = None,
) -> ResumePolishReport:
    """旧的 profile/provider 调用不变；定制时接收完整 JD 和分析建议。"""
    if profile is None:
        profile = load_user_profile()
    snapshot = snapshot or build_resume_snapshot(profile)
    if not snapshot.targets:
        return ResumePolishReport(
            summary="档案中未检测到经历亮点，请先补充真实经历。",
            snapshot_id=snapshot.snapshot_id, items=[],
        )
    payload = {
        "candidate_facts": candidate_context(profile),
        "target_job_description": job_description.model_dump() if job_description else None,
        "raw_jd_text": jd_text if jd_text is not None else (
            job_description.raw_text if job_description else None
        ),
        "analysis_suggestions_not_facts": match_result.model_dump() if match_result else None,
        "snapshot_id": snapshot.snapshot_id,
        "highlights": [
            {
                "snapshot_id": snapshot.snapshot_id,
                "target_ref": target.target_ref,
                "expected_original_hash": target.original_hash,
                "source": target.source,
                "original": target.original,
            }
            for target in snapshot.targets
        ],
    }
    with LLMClient(provider=provider) as client:
        report = client.chat_pydantic([
            {"role": "system", "content": STAR_REWRITE_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ], ResumePolishReport)
    return review_polish_report(profile, report, snapshot)


def diagnose_ats(
    profile: UserProfile | None = None,
    target_jd_text: str | None = None,
    provider: str | None = None,
) -> ATSScoreReport:
    """评估业务材料的表达和证据覆盖，不冒充招聘平台实际筛选结果。"""
    if profile is None:
        profile = load_user_profile()
    payload = {
        "candidate_facts": candidate_context(profile),
        "raw_jd_text": target_jd_text,
    }
    with LLMClient(provider=provider) as client:
        return client.chat_pydantic([
            {"role": "system", "content": ATS_DIAGNOSIS_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ], ATSScoreReport)


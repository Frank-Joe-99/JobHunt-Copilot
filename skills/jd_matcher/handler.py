"""岗位结构化解析和候选人匹配；保留完整原文与业务材料。"""

import json
from core.config import load_user_profile
from core.context import candidate_context
from core.state import UserProfile, JobDescription, MatchResult
from tools.llm_client import LLMClient
from skills.jd_matcher.prompt import JD_PARSE_SYSTEM, JD_MATCH_SYSTEM


def parse_jd(jd_text: str, provider: str | None = None) -> JobDescription:
    if not jd_text.strip():
        raise ValueError("岗位 JD 不能为空。")
    with LLMClient(provider=provider) as client:
        jd = client.chat_pydantic([
            {"role": "system", "content": JD_PARSE_SYSTEM},
            {"role": "user", "content": jd_text.strip()},
        ], JobDescription)
    jd.raw_text = jd_text.strip()
    return jd


def match_profile_with_jd(
    profile: UserProfile, jd: JobDescription, provider: str | None = None,
) -> MatchResult:
    payload = {
        "candidate_profile": candidate_context(profile),
        "target_job_description": jd.model_dump(),
    }
    with LLMClient(provider=provider) as client:
        return client.chat_pydantic([
            {"role": "system", "content": JD_MATCH_SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ], MatchResult)


def analyze_jd(
    jd_text: str, profile: UserProfile | None = None, provider: str | None = None,
) -> MatchResult:
    if profile is None:
        profile = load_user_profile()
    return match_profile_with_jd(profile, parse_jd(jd_text, provider=provider), provider=provider)


"""
目标岗位 JD 深度穿透与匹配分析业务调度器 (JD Matcher Handler)
"""

import json
from core.config import load_user_profile
from core.state import UserProfile, JobDescription, MatchResult
from tools.llm_client import LLMClient
from skills.jd_matcher.prompt import JD_PARSE_SYSTEM, JD_MATCH_SYSTEM


def parse_jd(jd_text: str, provider: str | None = None) -> JobDescription:
    """将非结构化岗位招聘描述文本，解析为 JobDescription 实体。"""
    client = LLMClient(provider=provider)
    messages = [
        {"role": "system", "content": JD_PARSE_SYSTEM},
        {"role": "user", "content": f"【待解析招聘 JD 原文】：\n{jd_text.strip()}"},
    ]
    jd_obj = client.chat_pydantic(messages, JobDescription)
    jd_obj.raw_text = jd_text.strip()
    return jd_obj


def match_profile_with_jd(
    profile: UserProfile,
    jd: JobDescription,
    provider: str | None = None,
) -> MatchResult:
    """将用户档案与结构化岗位要求进行深度穿透比对。"""
    client = LLMClient(provider=provider)

    profile_summary = {
        "basics": {
            "name": profile.basics.name,
            "school": profile.basics.school,
            "degree": profile.basics.degree,
        },
        "objective": profile.objective.model_dump() if profile.objective else None,
        "education": [
            {"school": e.school, "degree": e.degree, "major": e.major, "gpa": e.gpa}
            for e in profile.education
        ],
        "skills": profile.skills.model_dump() if profile.skills else None,
        "internships": [
            {"company": i.company, "role": i.role, "highlights": i.highlights}
            for i in profile.internships
        ],
        "projects": [
            {"name": p.name, "tech_stack": p.tech_stack, "highlights": p.highlights}
            for p in profile.projects
        ],
        "research": [
            {"name": r.name, "highlights": r.highlights}
            for r in profile.research
        ],
        "articles": [
            {"cite": a.cite, "author_order": a.author_order}
            for a in profile.articles
        ],
    }

    user_payload = {
        "candidate_profile": profile_summary,
        "target_job_description": {
            "company": jd.company,
            "role": jd.role,
            "department": jd.department,
            "hard_requirements": jd.hard_requirements,
            "soft_requirements": jd.soft_requirements,
            "bonus_items": jd.bonus_items,
        },
    }

    messages = [
        {"role": "system", "content": JD_MATCH_SYSTEM},
        {
            "role": "user",
            "content": f"请对以下候选人档案与目标岗位 JD 进行深度比对：\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}",
        },
    ]

    return client.chat_pydantic(messages, MatchResult)


def analyze_jd(
    jd_text: str,
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> MatchResult:
    """一键门面函数：输入原始 JD 文本，自动完成解析 + 穿透比对。"""
    if profile is None:
        profile = load_user_profile()

    parsed_jd = parse_jd(jd_text, provider=provider)
    return match_profile_with_jd(profile, parsed_jd, provider=provider)


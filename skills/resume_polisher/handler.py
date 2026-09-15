"""
简历润色与 ATS 诊断业务调度器 (Resume Polisher Handler)
"""

import json
from core.config import load_user_profile
from core.state import UserProfile, ResumePolishReport, ATSScoreReport
from tools.llm_client import LLMClient
from skills.resume_polisher.prompt import STAR_REWRITE_SYSTEM, ATS_DIAGNOSIS_SYSTEM


def polish_experiences(
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> ResumePolishReport:
    """对用户档案中的实习与项目经历按 STAR 法则进行深度润色。"""
    if profile is None:
        profile = load_user_profile()

    client = LLMClient(provider=provider)

    # 抽取所有需要润色的亮点描述
    items_to_polish = []
    for intern in profile.internships:
        header = f"实习-{intern.company}"
        if intern.role:
            header += f"({intern.role})"
        for h in intern.highlights:
            items_to_polish.append({"source": header, "text": h})

    for proj in profile.projects:
        header = f"项目-{proj.name}"
        if proj.role:
            header += f"({proj.role})"
        for h in proj.highlights:
            items_to_polish.append({"source": header, "text": h})

    for res in profile.research:
        header = f"科研-{res.name}"
        for h in res.highlights:
            items_to_polish.append({"source": header, "text": h})

    if not items_to_polish:
        return ResumePolishReport(
            summary="档案中未检测到任何经历亮点，请先在 profile.yaml 中补充。",
            items=[],
        )

    target_role = profile.objective.target_role if profile.objective else "技术研发"

    prompt_lines = [f"【求职目标岗位】：{target_role}", "【待润色经历清单】："]
    for idx, item in enumerate(items_to_polish, start=1):
        prompt_lines.append(f"{idx}. 来源：[{item['source']}] | 原始描述：{item['text']}")

    messages = [
        {"role": "system", "content": STAR_REWRITE_SYSTEM},
        {"role": "user", "content": "\n".join(prompt_lines)},
    ]

    return client.chat_pydantic(messages, ResumePolishReport)


def diagnose_ats(
    profile: UserProfile | None = None,
    target_jd_text: str | None = None,
    provider: str | None = None,
) -> ATSScoreReport:
    """对简历档案进行 ATS 关键词覆盖率与规范性体检打分。"""
    if profile is None:
        profile = load_user_profile()

    client = LLMClient(provider=provider)

    profile_summary = {
        "basics": {"name": profile.basics.name, "degree": profile.basics.degree},
        "objective": profile.objective.model_dump() if profile.objective else None,
        "education": [
            {"school": e.school, "major": e.major, "degree": e.degree}
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
    }

    user_parts = [
        "【候选人当前简历全貌】：",
        json.dumps(profile_summary, ensure_ascii=False, indent=2),
    ]
    if target_jd_text:
        user_parts.extend(["\n【对标的目标企业招聘 JD】：", target_jd_text.strip()])
    else:
        user_parts.append("\n（未提供特定 JD，请按通用大厂 ATS 标准体检）")

    messages = [
        {"role": "system", "content": ATS_DIAGNOSIS_SYSTEM},
        {"role": "user", "content": "\n".join(user_parts)},
    ]

    return client.chat_pydantic(messages, ATSScoreReport)


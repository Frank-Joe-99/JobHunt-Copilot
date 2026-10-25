"""送给模型的业务材料白名单；与展示用的完整个人档案分离。"""

from core.state import UserProfile


def candidate_context(profile: UserProfile) -> dict:
    """保留全部业务经历与限定词，不包含 basics 姓名/联系方式/照片等字段。"""
    return {
        "background": {
            key: value for key, value in {
                "school": profile.basics.school,
                "department": profile.basics.department,
                "degree": profile.basics.degree,
            }.items() if value is not None
        },
        "objective": profile.objective.model_dump(exclude_none=True) if profile.objective else None,
        "education": [
            item.model_dump(exclude={"logo", "advisor"}, exclude_none=True)
            for item in profile.education
        ],
        "skills": profile.skills.model_dump(exclude_none=True) if profile.skills else None,
        "internships": [item.model_dump(exclude_none=True) for item in profile.internships],
        "projects": [
            item.model_dump(exclude={"repo_url"}, exclude_none=True) for item in profile.projects
        ],
        "research": [item.model_dump(exclude_none=True) for item in profile.research],
        "articles": [item.model_dump(exclude_none=True) for item in profile.articles],
        "honors_and_awards": [item.model_dump(exclude_none=True) for item in profile.honors_and_awards],
        "certifications": [item.model_dump(exclude_none=True) for item in profile.certifications],
    }

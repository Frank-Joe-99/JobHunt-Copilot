"""
开源实战项目推荐与技能补短板业务调度器 (Project Recommender Handler)
根据技能差距清单，智能检索 GitHub 开源仓库，并由 LLM 挑选优质练手项目并生成简历 STAR 范文。
"""

import json
import re
from core.state import SkillGap, ProjectRecommendation, ProjectRecommendationReport
from tools.github_client import GitHubClient, GitHubRepo
from tools.llm_client import LLMClient
from skills.project_recommender.prompt import PROJECT_EVAL_SYSTEM


def _extract_search_terms(skill_text: str) -> list[str]:
    """从技能描述中提取适合 GitHub 搜索的核心英文技术词汇，例如 '分布式消息队列 Kafka' -> ['Kafka']"""
    # 提取英文技术词（包含字母、数字、特定符号如 C++, C#）
    english_terms = re.findall(r"[A-Za-z0-9+#.-]+", skill_text)
    # 过滤过短或通用无效词汇
    ignored = {"and", "or", "the", "in", "of", "to", "for", "with", "a", "an"}
    filtered = [t for t in english_terms if len(t) > 1 and t.lower() not in ignored]
    return filtered if filtered else [skill_text.strip()]


def recommend_projects_report(
    skills_gaps: list[SkillGap],
    language: str | None = "python",
    provider: str | None = None,
) -> ProjectRecommendationReport:
    """
    根据技能缺口列表，搜索并推荐适合练手的 GitHub 开源项目，返回完整报告。

    Args:
        skills_gaps: 技能差距清单 (SkillGap 列表)
        language: 偏好的编程语言 (默认 python)
        provider: 大模型供应商名称
    """
    # 1. 过滤出存在缺口的技能 (missing 或 partial)
    target_gaps = [gap for gap in skills_gaps if gap.status != "matched"]
    if not target_gaps:
        return ProjectRecommendationReport(
            overview="候选人当前技术栈已全部命中目标岗位要求，无需额外补充练手项目！",
            recommendations=[],
        )

    github = GitHubClient()
    llm = LLMClient(provider=provider)

    # 2. 针对各个技能缺口，逐项检索 GitHub 仓库并去重
    candidate_repos: list[GitHubRepo] = []
    seen_names: set[str] = set()

    for gap in target_gaps:
        terms = _extract_search_terms(gap.skill)
        # 用提取到的核心技术词（如 Kafka, Redis）进行针对性搜索
        search_query_terms = terms[:2] if terms else [gap.skill]
        
        try:
            repos = github.search_repos(
                keywords=search_query_terms,
                language=language,
                min_stars=200,
                max_stars=15000,
                per_page=4,
            )
            for r in repos:
                if r.full_name not in seen_names:
                    seen_names.add(r.full_name)
                    candidate_repos.append(r)
        except Exception as e:
            # 单个关键词搜索失败时降级容错，记录提示并继续流程
            if "403" in str(e):
                print("[!] 提示: GitHub API 触发未认证请求速率限制 (403)，可在 config/settings.yaml 配置 github.token 提升配额。")
            else:
                print(f"[!] 警告: 检索开源项目异常 ({search_query_terms}): {e}")
            continue

    # 如果有语言限定且结果较少，尝试不限语言兜底搜索一次
    if len(candidate_repos) < 2 and language:
        for gap in target_gaps[:2]:
            terms = _extract_search_terms(gap.skill)
            try:
                repos = github.search_repos(
                    keywords=terms[:1] if terms else [gap.skill],
                    language=None,
                    min_stars=300,
                    per_page=3,
                )
                for r in repos:
                    if r.full_name not in seen_names:
                        seen_names.add(r.full_name)
                        candidate_repos.append(r)
            except Exception as e:
                if "403" in str(e):
                    print("[!] 提示: GitHub API 触发未认证请求速率限制 (403)。")
                continue

    if not candidate_repos:
        return ProjectRecommendationReport(
            overview="未能检索到与当前缺口匹配的合适开源项目，建议调整技能关键词后重试。",
            recommendations=[],
        )

    # 3. 构造大模型提示词，挑选最具价值的 2~4 个项目并深度解析
    user_payload = {
        "missing_skill_gaps": [
            {"skill": g.skill, "status": g.status, "suggestion": g.suggestion}
            for g in target_gaps
        ],
        "candidate_github_repositories": [
            {
                "full_name": r.full_name,
                "html_url": r.html_url,
                "stars": r.stargazers_count,
                "language": r.language,
                "description": r.description,
                "topics": r.topics,
            }
            for r in candidate_repos[:10]  # 最多送入 10 个候选供模型精挑细选
        ],
    }

    messages = [
        {"role": "system", "content": PROJECT_EVAL_SYSTEM},
        {
            "role": "user",
            "content": f"请针对以下技能缺口与候选 GitHub 仓库进行智能筛选评估，并输出推荐方案：\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}",
        },
    ]

    return llm.chat_pydantic(messages, ProjectRecommendationReport)


def recommend_projects(
    skills_gaps: list[SkillGap],
    language: str | None = "python",
    provider: str | None = None,
) -> list[ProjectRecommendation]:
    """
    向后兼容的主入口函数：输入技能缺口，直接返回精选的项目推荐列表。
    """
    report = recommend_projects_report(
        skills_gaps=skills_gaps,
        language=language,
        provider=provider,
    )
    return report.recommendations
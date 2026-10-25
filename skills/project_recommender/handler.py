"""根据已确认缺口推荐公开项目；网络预算与证据由应用层约束。"""

import json
import logging
import re

from core.state import (
    ProjectRecommendation, ProjectRecommendationReport, RepositoryEvidence, SkillGap,
)
from skills.project_recommender.prompt import PROJECT_EVAL_SYSTEM
from tools.github_client import GitHubClient, GitHubRepo, GitHubUnavailable
from tools.llm_client import LLMClient

logger = logging.getLogger(__name__)
STAR_TEMPLATE = (
    "【仅供完成项目后填写，不可直接作为已完成经历投递】"
    "背景：[实际问题与目标]；行动：[本人实际完成的模块与贡献]；"
    "结果：[可复现的实测结果及测试口径；没有数据时如实描述，不编造指标]。"
)


def _extract_search_terms(skill_text: str) -> list[str]:
    terms = re.findall(r"[A-Za-z0-9+#.-]+", skill_text)
    ignored = {"and", "or", "the", "in", "of", "to", "for", "with", "a", "an"}
    return [term for term in terms if len(term) > 1 and term.lower() not in ignored] or [skill_text.strip()]


def recommend_projects_report(
    skills_gaps: list[SkillGap], language: str | None = "python", provider: str | None = None,
) -> ProjectRecommendationReport:
    gaps = [gap for gap in skills_gaps if gap.status in ("missing", "partial")]
    if not gaps:
        return ProjectRecommendationReport(
            status="no_gaps", overview="暂无已确认的技能缺口；未提供证据的技能需先澄清，不直接判为不会。",
        )
    try:
        github = GitHubClient()
    except (ValueError, OSError, RuntimeError):
        return ProjectRecommendationReport(
            status="unavailable", degraded=True, notices=["github_configuration"],
            overview="项目检索配置暂不可用，已跳过推荐；不代表没有技能缺口。",
        )
    candidates: dict[str, GitHubRepo] = {}
    readmes = {}
    with github:
        for gap in gaps:
            if github.monotonic() - github.started_at >= github.config.total_timeout_seconds:
                github._note("time_budget")
                break
            try:
                repos = github.search_repos(
                    _extract_search_terms(gap.skill)[:2], language=language,
                    min_stars=200, max_stars=15000, per_page=4,
                )
                for repo in repos:
                    candidates.setdefault(repo.full_name.casefold(), repo)
            except GitHubUnavailable:
                continue
        if len(candidates) < 2 and language:
            for gap in gaps[:2]:
                try:
                    for repo in github.search_repos(
                        _extract_search_terms(gap.skill)[:1], language=None,
                        min_stars=300, per_page=3,
                    ):
                        candidates.setdefault(repo.full_name.casefold(), repo)
                except GitHubUnavailable:
                    continue

        selected = list(candidates.values())[:10]
        for repo in selected[:github.config.max_readmes]:
            try:
                readmes[repo.full_name.casefold()] = github.get_readme(repo.full_name)
            except GitHubUnavailable:
                continue

        def finish(report: ProjectRecommendationReport):
            report.request_count = github.request_count
            report.cache_hits = github.cache_hits
            report.notices = list(dict.fromkeys([*report.notices, *github.notices]))
            report.degraded = report.degraded or bool(report.notices)
            return report

        if not selected:
            unavailable = bool(github.notices)
            return finish(ProjectRecommendationReport(
                status="unavailable" if unavailable else "no_match",
                overview="项目资料服务不可用，已跳过推荐。" if unavailable else "未找到合适的公开项目。",
            ))

        payload = {
            "missing_skill_gaps": [gap.model_dump() for gap in gaps],
            "candidate_github_repositories": [
                {
                    **repo.model_dump(),
                    "readme": readmes[repo.full_name.casefold()].model_dump()
                    if repo.full_name.casefold() in readmes else None,
                } for repo in selected
            ],
        }
        try:
            with LLMClient(provider=provider) as llm:
                report = llm.chat_pydantic([
                    {"role": "system", "content": PROJECT_EVAL_SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
                ], ProjectRecommendationReport)
        except (ValueError, RuntimeError):
            return finish(ProjectRecommendationReport(
                status="unavailable", degraded=True, notices=["evaluation_unavailable"],
                overview="公开资料已取得，但推荐评估暂不可用；已跳过推荐，不代表缺口已消失。",
            ))

        grounded = []
        seen = set()
        for item in report.recommendations[:4]:
            key = item.repo_name.casefold()
            repo = candidates.get(key)
            if repo is None or key in seen:
                github._note("invalid_recommendation")
                continue
            seen.add(key)
            item.repo_name, item.repo_url = repo.full_name, repo.html_url
            item.stars, item.language = repo.stargazers_count, repo.language
            item.star_resume_sample = STAR_TEMPLATE
            item.evidence = [RepositoryEvidence(
                kind="metadata", source_url=repo.html_url, fetched_at=repo.fetched_at,
                cache_status=repo.cache_status,
            )]
            readme = readmes.get(key)
            allowed_paths = set()
            if readme:
                allowed_paths.add(readme.path)
                item.evidence.append(RepositoryEvidence(
                    kind="readme", source_url=readme.html_url, source_version=readme.sha,
                    fetched_at=readme.fetched_at, cache_status=readme.cache_status,
                ))
            references = re.findall(
                r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|"
                r"[A-Za-z0-9_.-]+\.(?:py|md|cpp|cc|h|hpp|js|ts|tsx|jsx|go|rs|java)\b",
                item.learning_path,
            )
            if any(path.removeprefix("./") not in allowed_paths for path in references):
                item.learning_path = "先从公开说明确认与技能缺口相关的模块入口，再完成一个可验证的小练习。"
                github._note("unverified_path_removed")
            item.learning_path += "（源码学习计划待验证；仅所列 README 引用有读取证据。）"
            grounded.append(item)
        report.recommendations = grounded
        report.status = "completed" if grounded else "no_match"
        return finish(report)


def recommend_projects(
    skills_gaps: list[SkillGap], language: str | None = "python", provider: str | None = None,
) -> list[ProjectRecommendation]:
    return recommend_projects_report(skills_gaps, language, provider).recommendations

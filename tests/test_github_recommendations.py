import base64
import json
import sqlite3

import httpx
import pytest

from core.state import GithubConfig, ProjectRecommendation, ProjectRecommendationReport, SkillGap
from tools.github_client import GitHubClient, GitHubUnavailable


def repo_payload(private=False):
    return {"items": [{
        "full_name": "sample/cache", "private": private,
        "html_url": "https://unsafe.invalid/ignored", "description": "Public cache exercise",
        "stargazers_count": 500, "language": "Python", "topics": ["cache"],
    }]}


def readme_payload():
    return {
        "type": "file", "encoding": "base64", "path": "README.md", "sha": "a" * 40,
        "content": base64.b64encode(b"# Public README\nRead docs first.").decode(),
    }


def test_cache_survives_new_client_and_contains_only_public_material(tmp_path):
    requests = []
    now = [100.0]
    def transport(request):
        requests.append(request)
        return httpx.Response(200, json=repo_payload())
    kwargs = dict(cache_path=tmp_path / "public.db", clock=lambda: now[0])
    with GitHubClient(config=GithubConfig(token="synthetic-secret"), transport=httpx.MockTransport(transport), **kwargs) as client:
        result = client.search_repos(["PRIVATE-JD-KEYWORD"])
        assert result[0].html_url == "https://github.com/sample/cache"
    with GitHubClient(config=GithubConfig(offline=True), **kwargs) as client:
        cached = client.search_repos(["PRIVATE-JD-KEYWORD"])
        assert cached[0].cache_status == "fresh"
        assert client.request_count == 0 and client.cache_hits == 1
    assert len(requests) == 1
    with sqlite3.connect(kwargs["cache_path"]) as conn:
        dump = "\n".join(conn.iterdump())
    assert "synthetic-secret" not in dump
    assert "PRIVATE-JD-KEYWORD" not in dump


def test_private_repositories_not_saved(tmp_path):
    with GitHubClient(
        config=GithubConfig(), cache_path=tmp_path / "public.db",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=repo_payload(private=True))),
    ) as client:
        assert client.search_repos(["cache"]) == []
    with sqlite3.connect(tmp_path / "public.db") as conn:
        assert "sample/cache" not in "\n".join(conn.iterdump())


def test_stale_cache_has_original_date_when_offline(tmp_path):
    now = [100.0]
    kwargs = dict(cache_path=tmp_path / "cache.db", clock=lambda: now[0])
    with GitHubClient(
        config=GithubConfig(cache_ttl_seconds=1), **kwargs,
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=repo_payload())),
    ) as client:
        first = client.search_repos(["cache"])[0]
    now[0] += 5
    with GitHubClient(config=GithubConfig(offline=True, cache_ttl_seconds=1), **kwargs) as client:
        cached = client.search_repos(["cache"])[0]
        assert cached.cache_status == "stale" and cached.fetched_at == first.fetched_at
        assert "stale_cache" in client.notices


@pytest.mark.parametrize("config,reason", [
    (GithubConfig(max_requests=0), "request_budget"),
    (GithubConfig(max_search_requests=0), "search_budget"),
    (GithubConfig(offline=True), "offline"),
])
def test_budget_or_offline_never_reaches_transport(tmp_path, config, reason):
    with GitHubClient(
        config=config, cache_path=tmp_path / "cache.db",
        transport=httpx.MockTransport(lambda req: pytest.fail("unexpected HTTP")),
    ) as client:
        with pytest.raises(GitHubUnavailable, match=reason):
            client.search_repos(["cache"])


def test_time_budget(tmp_path):
    now = [0.0]
    with GitHubClient(
        config=GithubConfig(total_timeout_seconds=2), cache_path=tmp_path / "cache.db",
        monotonic=lambda: now[0], transport=httpx.MockTransport(lambda req: pytest.fail("HTTP")),
    ) as client:
        now[0] = 3
        with pytest.raises(GitHubUnavailable, match="time_budget"):
            client.search_repos(["cache"])


@pytest.mark.parametrize("status,headers,reason", [
    (403, {"x-ratelimit-remaining": "4"}, "forbidden"),
    (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "200"}, "rate_limited"),
    (429, {"retry-after": "120"}, "rate_limited"),
])
def test_rate_limit_classification_and_persisted_cooldown(tmp_path, status, headers, reason):
    requests = []
    def transport(request):
        requests.append(request)
        return httpx.Response(status, headers=headers, json={"error": "DO-NOT-LOG"})
    kwargs = dict(cache_path=tmp_path / "cache.db", clock=lambda: 100.0)
    for _ in range(2):
        with GitHubClient(
            config=GithubConfig(), transport=httpx.MockTransport(transport), **kwargs,
        ) as client:
            with pytest.raises(GitHubUnavailable, match=reason) as exc:
                client.search_repos(["cache"])
            assert "DO-NOT-LOG" not in str(exc.value)
    assert len(requests) == (2 if reason == "forbidden" else 1)


def test_large_response_stops_without_caching(tmp_path):
    with GitHubClient(
        config=GithubConfig(max_response_bytes=10), cache_path=tmp_path / "cache.db",
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=repo_payload())),
    ) as client:
        with pytest.raises(GitHubUnavailable, match="response_too_large"):
            client.search_repos(["cache"])


def test_readme_is_public_budgeted_and_versioned(tmp_path):
    requests = []
    def transport(request):
        requests.append(request)
        return httpx.Response(200, json=readme_payload())
    with GitHubClient(
        config=GithubConfig(token="synthetic-secret", max_readmes=1, readme_excerpt_chars=10),
        cache_path=tmp_path / "cache.db", transport=httpx.MockTransport(transport),
    ) as client:
        readme = client.get_readme("sample/cache")
        assert "Authorization" not in requests[0].headers
        assert readme.sha == "a" * 40 and readme.excerpt_truncated
        assert len(readme.excerpt) == 10
        with pytest.raises(GitHubUnavailable, match="readme_budget"):
            client.get_readme("sample/other")
        assert client.get_readme("sample/cache").cache_status == "fresh"


def test_recommendations_ground_urls_and_strip_invented_paths(tmp_path, monkeypatch, llm_stub):
    from skills.project_recommender import handler
    def transport(request):
        data = repo_payload() if request.url.path.startswith("/search") else readme_payload()
        return httpx.Response(200, json=data)
    monkeypatch.setattr(handler, "GitHubClient", lambda: GitHubClient(
        config=GithubConfig(), cache_path=tmp_path / "cache.db",
        transport=httpx.MockTransport(transport),
    ))
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    def response(messages, model):
        payload = json.loads(messages[-1]["content"])
        assert payload["candidate_github_repositories"][0]["readme"]["sha"] == "a" * 40
        return ProjectRecommendationReport(overview="合成推荐", recommendations=[
            ProjectRecommendation(
                repo_name="sample/cache", repo_url="https://evil.invalid",
                stars=999999, why_recommended="学习缓存", learning_path="阅读 src/invented.py，文件已验证",
                interview_tips="解释设计权衡", star_resume_sample="已实现高性能系统",
            ),
        ])
    llm_stub.responder = response
    report = handler.recommend_projects_report([SkillGap(skill="Redis", status="missing")])
    assert report.status == "completed" and report.degraded
    item = report.recommendations[0]
    assert item.stars == 500 and item.repo_url == "https://github.com/sample/cache"
    assert "invented.py" not in item.learning_path
    assert "未验证" in item.learning_path or "待验证" in item.learning_path
    assert len(item.evidence) == 2
    assert "不可直接" in item.star_resume_sample
    assert report.request_count <= 6


def test_unavailable_recommendation_does_not_call_evaluator(tmp_path, monkeypatch, llm_stub):
    from skills.project_recommender import handler
    monkeypatch.setattr(handler, "GitHubClient", lambda: GitHubClient(
        config=GithubConfig(offline=True), cache_path=tmp_path / "cache.db",
    ))
    monkeypatch.setattr(handler, "LLMClient", llm_stub)
    report = handler.recommend_projects_report([SkillGap(skill="Redis", status="missing")])
    assert report.status == "unavailable"
    assert report.recommendations == [] and not llm_stub.calls

import httpx
from pydantic import BaseModel, Field
from core.config import load_app_settings

class GitHubRepo(BaseModel):
    """
    单个 GitHub 仓库的结构化信息。
    """
    full_name: str              # 如 "onwer/repo-name"
    html_url: str               # 仓库链接
    description: str = ""       # 项目简介
    language: str | None = None # 主要编程语言
    stargazers_count: int = 0
    forks_count: int = 0
    topics: list[str] = Field(default_factory=list)  # 仓库标签

class GitHubClient:
    """
    GitHub REST API 轻量封装
    """
    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        # 从 settings.yaml 读取可选的 GitHub Token（提高速率限制）
        settings = load_app_settings()
        self.token = settings.github.token or None

    def search_repos(self, keywords: list[str],
                     language: str | None = None,
                     min_stars: int = 100,
                     max_stars: int = 10000,
                     per_page: int = 5,) -> list[GitHubRepo]:
        """
        根据关键词搜索 GitHub 仓库。
        实现要点：
        1. 将 keywords 拼接为搜索查询字符串
        2. 添加 language、stars 范围过滤
        3. 按 stars 排序
        4. 解析响应中的 items 列表，映射为 GitHubRepo
        """
        query_parts = keywords.copy()
        if language:
            query_parts.append(f"language:{language}")
        query_parts.append(f"stars:{min_stars}..{max_stars}")
        q = " ".join(query_parts)

        # 发送请求
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "JobHunt-Copilot",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        params = {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{self.BASE_URL}/search/repositories",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        repos = []
        for item in data.get("items", []):
            repos.append(
                GitHubRepo(
                    full_name=item.get("full_name", ""),
                    html_url=item.get("html_url", ""),
                    description=item.get("description") or "",
                    language=item.get("language"),
                    stargazers_count=item.get("stargazers_count", 0),
                    forks_count=item.get("forks_count", 0),
                    topics=item.get("topics", []),
                )
            )
        return repos
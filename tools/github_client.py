"""公开 GitHub 资料读取：缓存、资源配额、请求/流量/时间预算。"""

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Callable

import httpx
from pydantic import BaseModel, Field, ValidationError

from core.config import PROJECT_ROOT, load_app_settings
from core.state import GithubConfig

DEFAULT_CACHE_PATH = PROJECT_ROOT / "storage" / "github_cache.db"


class GitHubUnavailable(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"GitHub 资料暂不可用 ({reason})；未输出请求、认证或响应正文。")


class GitHubRepo(BaseModel):
    full_name: str
    html_url: str
    description: str = ""
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    topics: list[str] = Field(default_factory=list)
    fetched_at: str = ""
    cache_status: str = "network"


class GitHubReadme(BaseModel):
    path: str
    sha: str
    html_url: str
    excerpt: str
    excerpt_truncated: bool = False
    fetched_at: str = ""
    cache_status: str = "network"


class GitHubClient:
    BASE_URL = "https://api.github.com"

    def __init__(
        self, *, config: GithubConfig | None = None, cache_path: str | Path | None = None,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.time,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.config = config if config is not None else load_app_settings().github
        self.token = self.config.token or None
        self.cache_path = Path(cache_path) if cache_path is not None else DEFAULT_CACHE_PATH
        self.clock, self.monotonic = clock, monotonic
        self.started_at = monotonic()
        self.request_count = 0
        self.search_count = 0
        self.readme_count = 0
        self.download_bytes = 0
        self.cache_hits = 0
        self.notices: list[str] = []
        self._client = httpx.Client(transport=transport, follow_redirects=False)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._client.close()

    def _note(self, reason: str):
        if reason not in self.notices:
            self.notices.append(reason)

    def _cache_connection(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.cache_path, timeout=1)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            conn.close()
            raise sqlite3.DatabaseError("Unsupported cache schema")
        if version == 0:
            try:
                conn.executescript("""
            CREATE TABLE IF NOT EXISTS public_cache (
                cache_key TEXT PRIMARY KEY, fetched_at REAL NOT NULL, payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cooldowns (
                resource TEXT PRIMARY KEY, blocked_until REAL NOT NULL
            );
            PRAGMA user_version=1;
                """)
            except sqlite3.Error:
                conn.close()
                raise
        return conn

    def _cached(self, key: str):
        try:
            with closing(self._cache_connection()) as conn:
                row = conn.execute(
                    "SELECT fetched_at, payload FROM public_cache WHERE cache_key=?", (key,),
                ).fetchone()
                return (row[0], json.loads(row[1])) if row else None
        except (OSError, sqlite3.Error, ValueError):
            self._note("cache_unavailable")
            return None

    def _save(self, key: str, payload: dict, timestamp: float):
        try:
            with closing(self._cache_connection()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO public_cache VALUES (?, ?, ?)",
                    (key, timestamp, json.dumps(payload, ensure_ascii=False)),
                )
        except (OSError, sqlite3.Error):
            self._note("cache_unavailable")

    def _cooldown(self, resource: str, until: float | None = None) -> float:
        try:
            with closing(self._cache_connection()) as conn, conn:
                if until is not None:
                    conn.execute(
                        "INSERT INTO cooldowns VALUES (?, ?) ON CONFLICT(resource) "
                        "DO UPDATE SET blocked_until=MAX(blocked_until, excluded.blocked_until)",
                        (resource, until),
                    )
                row = conn.execute(
                    "SELECT blocked_until FROM cooldowns WHERE resource=?", (resource,),
                ).fetchone()
                return row[0] if row else 0
        except (OSError, sqlite3.Error):
            self._note("cache_unavailable")
            return 0

    @staticmethod
    def _safe_repo_name(name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ValueError("仓库名必须为合法的 owner/repo。")
        return name

    def _budget(self, resource: str):
        if self.config.offline:
            raise GitHubUnavailable("offline")
        if self.request_count >= self.config.max_requests:
            raise GitHubUnavailable("request_budget")
        if resource.startswith("search") and self.search_count >= self.config.max_search_requests:
            raise GitHubUnavailable("search_budget")
        if resource.startswith("core") and self.readme_count >= self.config.max_readmes:
            raise GitHubUnavailable("readme_budget")
        if self.download_bytes >= self.config.max_download_bytes:
            raise GitHubUnavailable("download_budget")
        if self.monotonic() - self.started_at >= self.config.total_timeout_seconds:
            raise GitHubUnavailable("time_budget")
        if self._cooldown(resource) > self.clock():
            raise GitHubUnavailable("rate_limited")

    def _request(self, path: str, params: dict, clean: Callable, *, search: bool):
        # 搜索词只进入哈希，不在缓存中保存候选人的原始技能/JD。
        key = hashlib.sha256(json.dumps([path, params], sort_keys=True).encode()).hexdigest()
        cached = self._cached(key)
        now = self.clock()
        if cached and now - cached[0] <= self.config.cache_ttl_seconds:
            self.cache_hits += 1
            return cached[1], cached[0], "fresh"
        resource = "search:" + ("auth" if self.token else "anon") if search else "core:anon"
        try:
            self._budget(resource)
            remaining = self.config.total_timeout_seconds - (self.monotonic() - self.started_at)
            headers = {"Accept": "application/vnd.github+json", "User-Agent": "JobHunt-Copilot"}
            if search and self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            # README 匿名读取，避免将 Token 可访问的私有内容混入公共缓存。
            self.request_count += 1
            if search:
                self.search_count += 1
            else:
                self.readme_count += 1
            timeout = min(self.config.request_timeout_seconds, remaining)
            with self._client.stream(
                "GET", self.BASE_URL + path, params=params, headers=headers, timeout=timeout,
            ) as response:
                reset = response.headers.get("x-ratelimit-reset", "")
                if response.headers.get("x-ratelimit-remaining") == "0":
                    until = float(reset) if reset.replace(".", "", 1).isdigit() else self.clock() + 60
                    self._cooldown(resource, until)
                if response.status_code == 429 or (
                    response.status_code == 403 and (
                        response.headers.get("x-ratelimit-remaining") == "0"
                        or "retry-after" in response.headers
                    )
                ):
                    wait = response.headers.get("retry-after", "")
                    self._cooldown(resource, self.clock() + (float(wait) if wait.isdigit() else 60))
                    raise GitHubUnavailable("rate_limited")
                if response.status_code == 403:
                    raise GitHubUnavailable("forbidden")
                if response.status_code != 200:
                    raise GitHubUnavailable("not_found" if response.status_code == 404 else "http_error")
                limit = min(self.config.max_response_bytes, self.config.max_download_bytes - self.download_bytes)
                length = response.headers.get("content-length", "")
                if length.isdigit() and int(length) > limit:
                    raise GitHubUnavailable("response_too_large")
                chunks, size = [], 0
                for chunk in response.iter_bytes(chunk_size=max(1, min(8192, limit + 1))):
                    size += len(chunk)
                    self.download_bytes += len(chunk)
                    if size > limit:
                        raise GitHubUnavailable("download_budget")
                    if self.monotonic() - self.started_at >= self.config.total_timeout_seconds:
                        raise GitHubUnavailable("time_budget")
                    chunks.append(chunk)
                payload = clean(json.loads(b"".join(chunks)))
            fetched_at = self.clock()
            self._save(key, payload, fetched_at)
            return payload, fetched_at, "network"
        except GitHubUnavailable as exc:
            reason = exc.reason
        except (httpx.HTTPError, OSError):
            reason = "network_error"
        except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
            reason = "invalid_response"
        self._note(reason)
        if cached and now - cached[0] <= self.config.max_stale_seconds:
            self.cache_hits += 1
            self._note("stale_cache")
            return cached[1], cached[0], "stale"
        raise GitHubUnavailable(reason) from None

    def search_repos(
        self, keywords: list[str], language: str | None = None,
        min_stars: int = 100, max_stars: int = 10000, per_page: int = 5,
    ) -> list[GitHubRepo]:
        if not 1 <= per_page <= 100 or not keywords:
            raise ValueError("需要搜索词，且 per_page 必须在 1～100。")
        parts = [*keywords, "is:public", f"stars:{min_stars}..{max_stars}"]
        if language:
            parts.append(f"language:{language}")
        def clean(data):
            result = []
            for item in data["items"]:
                if item.get("private") is not False:
                    continue
                name = self._safe_repo_name(item["full_name"])
                repo = GitHubRepo(
                    full_name=name, html_url=f"https://github.com/{name}",
                    description=(item.get("description") or "")[:5000], language=item.get("language"),
                    stargazers_count=item.get("stargazers_count", 0),
                    forks_count=item.get("forks_count", 0), topics=(item.get("topics") or [])[:50],
                )
                result.append(repo.model_dump(exclude={"fetched_at", "cache_status"}))
            return {"items": result}
        data, timestamp, state = self._request(
            "/search/repositories", {"q": " ".join(parts), "sort": "stars", "order": "desc", "per_page": per_page},
            clean, search=True,
        )
        fetched = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
        return [GitHubRepo(**item, fetched_at=fetched, cache_status=state) for item in data["items"]]

    def get_readme(self, repo_name: str) -> GitHubReadme:
        import base64
        name = self._safe_repo_name(repo_name)
        def clean(data):
            if data.get("type") != "file" or data.get("encoding") != "base64":
                raise ValueError("Expected README file")
            content = base64.b64decode("".join(data["content"].split()), validate=True).decode("utf-8", errors="replace")
            path, sha = data["path"], data["sha"]
            if not isinstance(path, str) or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
                raise ValueError("Invalid README reference")
            return {
                "path": path, "sha": sha,
                "html_url": f"https://api.github.com/repos/{name}/git/blobs/{sha}",
                "excerpt": content[:self.config.readme_excerpt_chars],
                "excerpt_truncated": len(content) > self.config.readme_excerpt_chars,
            }
        data, timestamp, state = self._request(f"/repos/{name}/readme", {}, clean, search=False)
        return GitHubReadme(
            **data, fetched_at=datetime.fromtimestamp(timestamp, timezone.utc).isoformat(), cache_status=state,
        )

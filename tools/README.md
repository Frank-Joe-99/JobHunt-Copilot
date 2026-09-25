# 🔧 tools/ 目录：底层基础设施与外设驱动层

`tools/` 负责充当系统的**“手和脚”**。它专门处理与现实外部世界的具体协议对接（HTTP 请求、网络通信、大模型厂商 API、GitHub REST API 等）。

---

## 🛑 纯粹性铁律（重要架构准则）

> **`tools/` 里的代码只管“怎么发请求、怎么反序列化、怎么复用连接”，绝不包含任何“应届生怎么写简历”这类业务策略或大模型提示词（Prompt）。**
> 
> 业务策略属于 `skills/`，数据契约属于 `core/`，底层工具属于 `tools/`。这种设计保证了底层技术更换（例如更换网络库或升级大模型接口）时，上层业务层代码完全不受影响。

---

## 🗂️ 核心工具结构与实现现状

```text
tools/
├── __init__.py
├── llm_client.py       # 统一大模型请求客户端封装（连接池复用、重试、流式、Pydantic结构化反序列化）
├── github_client.py    # GitHub REST API 交互封装（按技术关键词、语言、Star数检索开源实战项目）
└── README.md
```

> **注**：PDF 与 Word 排版编译能力由专门的高保真技能模块 `skills/resume_generator/`（基于 `typst` 与 `python-docx`）承载，不放在 `tools/` 中以避免臃肿。

---

## 🔌 核心工具模块 API 规范

### 1. `llm_client.py`（统一大模型客户端）

基于 `httpx` 实现高并发 Keep-Alive 连接池复用、指数退避容错重试与容错 JSON 修复机制，原生兼容 DeepSeek、OpenAI、Moonshot (Kimi)、智谱 GLM、Aliyun DashScope 等所有 OpenAI-compatible 协议厂商。

#### 核心方法：
- **`chat(messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs) -> str`**  
  发送常规对话请求，返回模型回复的纯文本字符串。
- **`chat_pydantic(messages: list[dict], model_class: type[T], max_retries: int = 3, timeout: float = 60.0, **kwargs) -> T`**  
  结构化请求接口。借助 `json-repair` 与 Pydantic，强约束大模型返回指定 Schema 的实例对象，格式异常自动修复。
- **`chat_json(messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs) -> dict`**  
  返回经过容错解析的原始 Python 字典。
- **`chat_stream(messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs) -> Generator[str, None, None]`**  
  Server-Sent Events (SSE) 流式请求接口。逐字吐出大模型内容，具备连接异常安全保护与自动重试。
- **`close() -> None`** / 支持上下文管理器 `with LLMClient() as client:`  
  安全关闭底层 HTTP 连接池。

---

### 2. `github_client.py`（GitHub 开放接口封装）

负责与 GitHub REST API (`https://api.github.com/search/repositories`) 交互，检索工业级优质开源练手项目。

#### 核心数据契约：
- **`GitHubRepo`**（Pydantic 模型）：
  - `full_name: str`（如 `redis/redis`）
  - `html_url: str`（仓库主页链接）
  - `description: str`（项目简介）
  - `language: str | None`（主力编程语言）
  - `stargazers_count: int`（Star 收藏数）
  - `forks_count: int`（Fork 数）
  - `topics: list[str]`（技术标签）

#### 核心方法：
- **`search_repos(keywords, language=None, min_stars=100, max_stars=10000, per_page=5) -> list[GitHubRepo]`**  
  根据技能短板关键词与技术栈条件组装 GitHub Search 查询表达式，按 Star 数量降序排序，过滤适合应届生研读练手的项目。自动支持可选的 `GITHUB_TOKEN` 授权认证以提升 API 速率限制配额。

---

## 🧪 独立调用与验证

```bash
# 测试 LLM 基础连通性
uv run python -c "from tools.llm_client import LLMClient; print(LLMClient().chat([{'role': 'user', 'content': 'hi'}]))"

# 测试 GitHub 检索连通性
uv run python -c "from tools.github_client import GitHubClient; repos = GitHubClient().search_repos(['redis', 'cache'], language='python', per_page=2); print([r.full_name for r in repos])"
```

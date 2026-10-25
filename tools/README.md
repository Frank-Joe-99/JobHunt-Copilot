# 🔧 tools/ 目录：底层基础设施与外设驱动层

模型能力配置新增 `supports_temperature`、可空的 `temperature`、`token_limit_parameter`、`output_token_limit`、`context_char_limit` 和 `supports_json_mode`，见 `config/settings.example.yaml`。只修改本地配置时才影响具体端点；不按模型名称猜测能力。输入按字符预算检查，超限明确报错而不裁掉经历；输出不再统一截为 8192。

`chat()` 仍返回字符串，`chat_stream()` 仍返回字符串生成器。调用状态通过 `last_response` 暴露（包括结束原因、HTTP 状态、用量和 JSON 修复标记，不含正文）。拒绝、截断、缺少正常结束原因和流中断会报错；经过结构修复的 JSON 不直接作为正式 Pydantic 业务结果。原生 schema 与分层自动降级留待 M08，不在本批实施。

> 本模块为 JobHunt-Copilot 提供**底层网络通信与外部 API 驱动封装**。负责处理与大模型服务提供商及 GitHub REST API 的网络交互，实现连接池复用、故障重试与数据反序列化。

---

## 🛑 架构设计准则

> [!IMPORTANT]
> **业务纯粹性准则**：`tools/` 模块专门负责网络请求发送、连接复用与异常恢复，**绝对不包含任何业务 Prompt 提示词**（Prompt 严格归属于 `skills/`）。当底层网络库升级或大模型厂商协议变更时，上层业务逻辑不受任何影响。

---

## 🗂️ 组件结构

```text
tools/
├── __init__.py
├── llm_client.py       # 统一大模型网络客户端（HTTPX 连接池、指数退避重试、流式 SSE、Pydantic 结构化解析）
├── github_client.py    # GitHub REST 检索驱动（按技术关键词、语言与 Star 阈值检索高星练手项目）
└── README.md
```

---

## 🔌 核心工具接口规范

### 1. `llm_client.py`（统一大模型客户端）
基于 `httpx` 构建，原生兼容 DeepSeek、OpenAI、月之暗面 (Kimi)、阿里百炼 (DashScope)、智谱 GLM 等所有兼容 OpenAI 格式的 API 厂商。

#### 核心方法说明：
| 方法名称 | 入参摘要 | 返回类型 | 功能说明 |
| :--- | :--- | :--- | :--- |
| `chat` | `messages: list[dict], max_retries=3, timeout=60.0` | `str` | 发送常规对话请求，返回模型回复文本 |
| `chat_pydantic` | `messages: list[dict], model_class: type[T]` | `T` | 结构化请求，结合 `json-repair` 强制校验并反序列化为 Pydantic 实例 |
| `chat_json` | `messages: list[dict], max_retries=3` | `dict` | 返回经过容错修复的字典对象 |
| `chat_stream` | `messages: list[dict], max_retries=3` | `Generator[str, None, None]` | SSE 流式请求，逐字生成回复内容 |
| `close` | 无 | `None` | 安全关闭底层 HTTP 连接池（支持 `with LLMClient() as client:` 上下文语法） |

---

### 2. `github_client.py`（GitHub 检索驱动）
与 GitHub 官方 Search API (`https://api.github.com/search/repositories`) 交互，定位适合应届生实操的开源练手项目。

#### 核心数据契约（`GitHubRepo`）：
- `full_name: str`：仓库全名（例如 `redis/redis`）
- `html_url: str`：仓库链接
- `description: str`：仓库简介
- `language: str | None`：主力编程语言
- `stargazers_count: int`：Star 收藏数量
- `topics: list[str]`：主题标签列表

#### 核心方法说明：
```python
search_repos(
    keywords: list[str],
    language: str | None = None,
    min_stars: int = 100,
    max_stars: int = 10000,
    per_page: int = 5
) -> list[GitHubRepo]
```
组装技术关键词查询表达式，按 Star 数量降序排序，自动识别 `GITHUB_TOKEN` 环境变量以提升 API 速率配额。

---

## 🛠️ 操作与连通性验证指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/settings.yaml` 中已配置有效的 `api_key` 和 `base_url`。
- 如果需要高频检索 GitHub，可在 `config/settings.yaml` 或系统环境变量中配置 `GITHUB_TOKEN`。

---

### 2. 验证大模型连通性操作

#### 步骤 1：执行基础连通性测试
在终端运行下列单行命令验证 API 握手与文本生成：
```bash
uv run python -c "from tools.llm_client import LLMClient; print(LLMClient().chat([{'role': 'user', 'content': '请回复 OK'}]))"
```
*预期结果*：终端返回包含 `OK` 的大模型响应文本。

#### 步骤 2：验证结构化 Pydantic 输出
在终端运行下列命令验证 JSON 模式修复与强类型反序列化能力：
```bash
uv run python -c "from pydantic import BaseModel; from tools.llm_client import LLMClient; class TestModel(BaseModel): status: str; res = LLMClient().chat_pydantic([{'role': 'user', 'content': '输出 JSON: {\"status\": \"success\"}'}], TestModel); print(type(res), res.status)"
```
*预期结果*：终端打印 `<class 'TestModel'> success`。

---

### 3. 验证 GitHub 检索驱动操作

#### 步骤 1：执行仓库检索命令
在终端运行下列命令检索 Python 分布式相关高星项目：
```bash
uv run python -c "from tools.github_client import GitHubClient; repos = GitHubClient().search_repos(['redis', 'cache'], language='python', per_page=2); print([r.full_name for r in repos])"
```
*预期结果*：终端输出符合条件的 GitHub 仓库名称列表（例如包含 redis 相关 Python 客户端项目）。

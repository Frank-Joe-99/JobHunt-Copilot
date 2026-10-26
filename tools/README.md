# 基础工具

提供网络、协议和锁，不包含业务 prompt。

| 文件 | 用途 |
| --- | --- |
| [llm_client.py](llm_client.py) | Chat Completions 兼容文本接口、参数预算、SSE 和完成状态 |
| [llm_formats.py](llm_formats.py) | 严格 schema 转换、格式错误分类与能力缓存 |
| [github_client.py](github_client.py) | 公开仓库检索、README、预算和带日期缓存 |
| [file_lock.py](file_lock.py) | 跨线程 / 进程的非阻塞锁 |

## 模型客户端

`LLMClient(provider=None)` 读取已配置供应商，可作为上下文管理器使用。

| 方法 | 返回 |
| --- | --- |
| `chat(messages, ...)` | 文本 |
| `chat_stream(messages, ...)` | 文本生成器，需消费完成 |
| `chat_json(messages, ...)` | JSON 对象或数组，修复情况见元数据 |
| `chat_pydantic(messages, model_class, ...)` | 经过核心字段校验的对象 |

参数能力显式配置；输入超预算报错而不静默裁剪。结构化输出按配置选择原生 schema、JSON mode 或提示词 JSON，仅明确“不支持格式”才降级。拒绝、截断和修复草稿不直接成为正式业务结果。

`last_response` 提供状态、结束原因、用量、格式、尝试次数和耗时，不保存正文或密钥。配置及降级边界见 [M08](../future-upgrade/M08-STRUCTURED-OUTPUT.md)。

## GitHub 与锁

`GitHubClient` 保留 `search_repos()`，支持配置、缓存路径、transport 和时钟注入。搜索、README、下载量及耗时分别限额；区分权限失败和限流，保存冷却时间，不循环重试。

缓存只保存经白名单筛选的公开资料；陈旧数据保留原日期。README 匿名读取，版本引用为内容 blob SHA。配置见 [settings 示例](../config/settings.example.yaml)，业务证据边界见[推荐模块](../skills/project_recommender/README.md)。

会话使用文件锁保护同一会话，网络等待期间不占 SQLite 写事务；锁竞争明确失败，不静默覆盖。

## 离线验证

```powershell
uv run pytest -q tests/test_llm_client.py tests/test_github_recommendations.py tests/test_interview_persistence.py
```

完整数据契约见 [core/state.py](../core/state.py)。

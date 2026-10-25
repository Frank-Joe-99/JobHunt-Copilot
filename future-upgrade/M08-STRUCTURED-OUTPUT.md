# M08：结构化输出分层适配

本功能保持 `chat_pydantic()`、`chat_json()` 的调用和返回类型兼容，不切换模型、供应商或 API 协议。默认仍使用现有 Chat Completions 兼容端点。

## 选择和校验

`structured_output: auto` 按显式能力选择：

1. `supports_json_schema: true` 且业务 schema 能严格表示时，发送原生 `json_schema`。
2. 按 `supports_json_mode` 使用 `json_object`；null 保留原供应商兼容默认。
3. 使用提示词 JSON，并继续校验 Pydantic 业务契约。

也可显式指定 `json_schema`、`json_object`、`prompt_json`。固定属性对象递归设置 `additionalProperties: false`、所有属性 required，并保留可空字段；动态字典在 auto 下直接走兼容格式。显式强制严格格式但 schema 无法表示时，在联网前报错。无效根 schema 也不会通过自动降级掩盖。

原生严格格式的字段要求和拒绝处理参考 [OpenAI 官方 Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)。其他兼容端点须按实际能力配置，不能从模型名称推断支持程度。

## 何时可以降级

仅识别 400/422 中有明确 code、response_format 参数位置及“不支持对应格式”说明的能力错误。普通 400、无效 schema、401/403、拒绝和截断不会授权降级；429/5xx 仍走有限的暂时性失败重试，不改变格式。

`storage/llm_capabilities.db` 只缓存“不支持某格式”的能力摘要与时间，不存请求、回复或密钥。缓存身份包含端点、模型、供应商与能力版本；TTL 到期、`capability_revision` 变化或禁用缓存可重新验证。缓存故障不阻断合法请求。

## 统一预算

示例配置位于 `config/settings.example.yaml`：

```yaml
supports_json_schema: false
structured_output: auto
allow_format_fallback: true
structured_max_attempts: 3
structured_total_timeout_seconds: 60
structured_validation_retries: 0
structured_max_response_bytes: 2000000
format_cache_ttl_seconds: 86400
capability_revision: "1"
```

次数由调用方 `max_retries` 与配置共同约束；网络重试、格式降级和字段重生成共享此预算。流式读取响应体时检查大小和期限，不提交超时或超体积的部分结果。底层阻塞读取仍受 HTTP 超时控制。

字段重生成默认关闭。显式开启时只重发原输入与技术格式要求，不附带失败结果、私有错误或其他模型分析。修复过的 JSON 不直接作为正式业务结果；如后续有限重生成获得完整有效结果才允许返回，元数据保留曾发生修复和校验失败的标记。

## 验证

`uv run --no-sync pytest -q tests/test_llm_client.py`：42 项通过，包括原生严格 schema、兼容默认、限定降级、缓存跨客户端复用与失效、预算耗尽、字段重生成、拒绝/截断、响应大小和错误脱敏。使用模拟 HTTP，没有调用真实模型；真实端点的支持程度和延迟仍需单独验证。

"""OpenAI 兼容文本客户端：显式参数能力、有限重试和完整性检查。"""

import json
import math
import re
import time
from typing import Generator, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from core.config import load_app_settings
from core.state import LLMProviderConfig, LLMResponseMetadata
from tools.llm_formats import FormatCache, UnsupportedStrictSchema, format_unsupported, strict_schema

T = TypeVar("T", bound=BaseModel)


class LLMResponseError(RuntimeError):
    """安全错误：不携带响应正文、请求内容或认证信息。"""


class LLMClient:
    def __init__(self, provider: str | None = None):
        settings = load_app_settings()
        self.provider_name = provider or settings.llm.default_provider
        if self.provider_name not in settings.llm.providers:
            raise ValueError("未配置指定的大模型供应商，请检查本地 settings.yaml。")
        self.config: LLMProviderConfig = settings.llm.providers[self.provider_name]
        api_key = self.config.api_key.strip()
        if not api_key or api_key.startswith("$" + "{") or "your-" in api_key.lower() or "replace" in api_key.lower():
            raise ValueError("模型供应商尚未配置可用 API Key，请检查本地环境变量或 settings.yaml。")
        self.base_url = self._resolve_base_url(self.provider_name)
        self._client: httpx.Client | None = None
        self.last_response: LLMResponseMetadata | None = None

    def _get_client(self, timeout: float = 60.0) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=timeout)
        return self._client

    def close(self) -> None:
        client = getattr(self, "_client", None)
        if client is not None and not client.is_closed:
            client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def _resolve_base_url(self, provider_name: str) -> str:
        if self.config.base_url:
            return self.config.base_url.rstrip("/")
        return {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "kimi": "https://api.moonshot.cn/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        }.get(provider_name, "https://api.openai.com/v1")

    def _get_endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _build_payload(self, messages: list[dict], stream: bool, **kwargs) -> dict:
        messages = self._sanitize_messages(messages)
        char_count = len(json.dumps(messages, ensure_ascii=False))
        if self.config.context_char_limit is not None and char_count > self.config.context_char_limit:
            raise ValueError(
                f"输入共 {char_count} 字符，超过 context_char_limit={self.config.context_char_limit}；"
                "未发送、未截断，请缩小材料或明确调整输入预算。"
            )
        payload = {"model": kwargs.get("model", self.config.model), "messages": messages, "stream": stream}
        temperature = kwargs.get("temperature", self.config.temperature)
        if self.config.supports_temperature and temperature is not None:
            if not isinstance(temperature, (float, int)) or not math.isfinite(temperature) or not 0 <= temperature <= 2:
                raise ValueError("temperature 必须为 0～2 的有限数值或 null。")
            payload["temperature"] = temperature
        parameter = self.config.token_limit_parameter
        if "max_completion_tokens" in kwargs:
            if "max_tokens" in kwargs:
                raise ValueError("不能同时指定两种输出 token 预算。")
            parameter = "max_completion_tokens"
            amount = kwargs["max_completion_tokens"]
        else:
            amount = kwargs.get("max_tokens", self.config.max_tokens)
        if amount is None:
            amount = self.config.output_token_limit
        if amount is not None:
            if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
                raise ValueError("输出 token 预算必须是正整数。")
            if self.config.output_token_limit is not None and amount > self.config.output_token_limit:
                raise ValueError("请求的输出预算超过 output_token_limit；未静默截断。")
            payload[parameter] = amount
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        return payload

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}

    def _fail(self, status: str, message: str):
        if self.last_response is None:
            self.last_response = LLMResponseMetadata()
        self.last_response.status = status
        raise LLMResponseError(message) from None

    def _check_http(self, response: httpx.Response) -> None:
        self.last_response.request_id = response.headers.get("x-request-id")
        self.last_response.http_status = response.status_code
        if response.is_success:
            return
        self.last_response.status = "http_error"
        if response.status_code in (400, 401, 403, 404, 422):
            advice = {
                400: "请求参数不兼容，请检查能力配置和 token_limit_parameter。",
                401: "认证失败，请检查本地 API Key。",
                403: "服务拒绝访问，请检查账号权限。",
                404: "端点或模型不存在，请检查 base_url 和 model。",
                422: "请求参数校验失败，请检查能力配置。",
            }[response.status_code]
            raise ValueError(f"模型服务 HTTP {response.status_code}：{advice}")
        response.raise_for_status()

    def _record_usage(self, data: dict) -> None:
        usage = data.get("usage")
        if isinstance(usage, dict):
            self.last_response.usage = {
                key: value for key, value in usage.items()
                if isinstance(value, int) and not isinstance(value, bool)
            }

    def _check_finish(self, finish_reason: str | None) -> None:
        self.last_response.finish_reason = finish_reason
        if finish_reason == "length":
            self._fail("truncated", "模型输出被预算截断，未作为完整业务结果，请调整输出预算后重试。")
        if finish_reason == "content_filter":
            self._fail("refused", "模型服务未提供可用结果。")
        if finish_reason != "stop":
            self._fail("invalid_response", "模型没有正常结束文本输出，未作为完整业务结果。")
        self.last_response.status = "completed"

    @staticmethod
    def _retryable(error: Exception) -> bool:
        return not isinstance(error, httpx.HTTPStatusError) or (
            error.response.status_code in (408, 429) or error.response.status_code >= 500
        )

    def chat(
        self, messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs,
    ) -> str:
        if max_retries < 1:
            raise ValueError("max_retries 必须至少为 1。")
        self.last_response = LLMResponseMetadata()
        payload = self._build_payload(messages, False, **kwargs)
        for attempt in range(max_retries):
            self.last_response.attempts = attempt + 1
            try:
                response = self._get_client(timeout).post(
                    self._get_endpoint(), headers=self._headers(), json=payload, timeout=timeout,
                )
                self._check_http(response)
                try:
                    data = response.json()
                    choice = data["choices"][0]
                    message = choice["message"]
                    if message.get("refusal"):
                        self._fail("refused", "模型拒绝生成该结果。")
                    self._check_finish(choice.get("finish_reason"))
                    content = message.get("content")
                    if not isinstance(content, str) or not content.strip():
                        self._fail("invalid_response", "模型没有返回非空文本。")
                    self._record_usage(data)
                    return content
                except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError):
                    self._fail("invalid_response", "模型响应格式不符合文本接口契约。")
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                self.last_response.status = (
                    "rate_limited" if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
                    else "http_error" if isinstance(exc, httpx.HTTPStatusError) else "network_error"
                )
                if self._retryable(exc) and attempt + 1 < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                self._fail(self.last_response.status, "模型请求失败；已在有限重试内停止，请检查服务状态。")
        self._fail("network_error", "模型请求未完成。")

    def _structured(
        self, messages, model_class, max_retries, timeout, options,
    ):
        if max_retries < 1 or timeout <= 0:
            raise ValueError("请求次数和 timeout 必须大于零。")
        started = time.monotonic()
        total_timeout = options.pop("total_timeout", self.config.structured_total_timeout_seconds)
        if not isinstance(total_timeout, (int, float)) or not math.isfinite(total_timeout) or total_timeout <= 0:
            raise ValueError("total_timeout 必须是有限正数。")
        deadline = started + min(total_timeout, self.config.structured_total_timeout_seconds)
        budget = min(max_retries, self.config.structured_max_attempts)
        self.last_response = LLMResponseMetadata()
        meta = self.last_response
        schema = model_class.model_json_schema() if model_class else None
        selected = options.pop("structured_output", self.config.structured_output)
        supplied = options.pop("response_format", None)
        if supplied is not None:
            selected = supplied.get("type") if isinstance(supplied, dict) else None
        if selected not in ("auto", "json_schema", "json_object", "prompt_json"):
            raise ValueError("未知的结构化输出格式。")
        native = None
        if schema is not None and (selected == "json_schema" or selected == "auto" and self.config.supports_json_schema):
            try:
                native = strict_schema(schema)
            except UnsupportedStrictSchema:
                if selected != "auto":
                    raise
                meta.fallback_reasons.append("local_dynamic_schema")
        if selected == "json_schema" and native is None:
            if not supplied or "json_schema" not in supplied:
                raise ValueError("原生 schema 模式需要明确的对象 schema。")
            native = strict_schema(supplied["json_schema"]["schema"])
        json_mode = self.config.supports_json_mode
        if json_mode is None:
            json_mode = self.provider_name in ("deepseek", "openai")
        if selected == "auto":
            modes = (["json_schema"] if native is not None else []) + (["json_object"] if json_mode else []) + ["prompt_json"]
        else:
            modes = [selected]
            if self.config.allow_format_fallback and selected == "json_schema":
                modes += (["json_object"] if json_mode else []) + ["prompt_json"]
            elif self.config.allow_format_fallback and selected == "json_object":
                modes += ["prompt_json"]
        if not self.config.allow_format_fallback:
            modes = modes[:1]
        cache = FormatCache({
            "endpoint": self._get_endpoint(), "provider": self.provider_name,
            "model": options.get("model", self.config.model),
            "revision": self.config.capability_revision,
            "supports_json_schema": self.config.supports_json_schema,
            "supports_json_mode": json_mode,
        }, self.config.format_cache_ttl_seconds)
        if self.config.allow_format_fallback:
            available = []
            for mode in modes:
                if cache.unsupported(mode):
                    meta.fallback_reasons.append("cached_unsupported_" + mode)
                else:
                    available.append(mode)
            modes = available
        instruction = "Return valid JSON only, without markdown or commentary."
        if schema is not None:
            instruction += " Match this JSON Schema: " + json.dumps(schema, ensure_ascii=False)
        request_messages = [{"role": "system", "content": instruction}, *messages]
        validations = 0
        last_invalid = "模型结果未通过业务字段校验（未输出私有内容）。"
        try:
            while modes and meta.attempts < budget:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._fail("budget_exhausted", "结构化请求总耗时预算已耗尽。")
                mode = modes[0]
                meta.format_used = mode
                call_options = dict(options)
                if mode == "json_schema":
                    call_options["response_format"] = {
                        "type": "json_schema", "json_schema": {
                            "name": re.sub(r"[^a-zA-Z0-9_-]", "_", model_class.__name__ if model_class else "output")[:64],
                            "strict": True, "schema": native,
                        },
                    }
                elif mode == "json_object":
                    call_options["response_format"] = {"type": "json_object"}
                payload = self._build_payload(request_messages, False, **call_options)
                meta.attempts += 1
                try:
                    with self._get_client(timeout).stream(
                        "POST", self._get_endpoint(), headers=self._headers(), json=payload,
                        timeout=min(timeout, remaining),
                    ) as streamed:
                        content = bytearray()
                        for chunk in streamed.iter_bytes():
                            if time.monotonic() >= deadline:
                                self._fail("budget_exhausted", "结构化请求总耗时预算已耗尽，未提交超时结果。")
                            if len(content) + len(chunk) > self.config.structured_max_response_bytes:
                                self._fail("invalid_response", "结构化响应超过体积预算，未提交部分结果。")
                            content.extend(chunk)
                        response = httpx.Response(
                            streamed.status_code, content=bytes(content), headers=streamed.headers,
                            request=streamed.request,
                        )
                    if time.monotonic() >= deadline:
                        self._fail("budget_exhausted", "结构化请求总耗时预算已耗尽，未提交超时结果。")
                    if format_unsupported(response, mode) and self.config.allow_format_fallback and len(modes) > 1:
                        cache.remember(mode)
                        meta.fallback_reasons.append("unsupported_" + mode)
                        modes.pop(0)
                        continue
                    self._check_http(response)
                    try:
                        body = response.json()
                        choice = body["choices"][0]
                        message = choice["message"]
                        if message.get("refusal"):
                            self._fail("refused", "模型拒绝生成该结果。")
                        self._check_finish(choice.get("finish_reason"))
                        raw = message.get("content")
                        if not isinstance(raw, str) or not raw.strip():
                            self._fail("invalid_response", "模型没有返回非空文本。")
                        self._record_usage(body)
                    except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError):
                        self._fail("invalid_response", "模型响应格式不符合文本接口契约。")
                    try:
                        data, repaired = self._parse_json(raw)
                        meta.json_repaired = meta.json_repaired or repaired
                        if model_class is None:
                            return data
                        if repaired:
                            last_invalid = "JSON 需要结构修复，未作为正式业务结果，请重新生成。"
                            raise ValueError("repaired")
                        if not isinstance(data, dict):
                            raise ValueError("object required")
                        return model_class.model_validate(data)
                    except (ValueError, ValidationError):
                        meta.validation_failures += 1
                        if validations >= self.config.structured_validation_retries or meta.attempts >= budget:
                            self._fail("invalid_response", last_invalid)
                        validations += 1
                        # 只发送相同输入和技术格式要求，不附带原输出、私有错误内容或调用其他模型。
                        continue
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                    status = (
                        "rate_limited" if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
                        else "http_error" if isinstance(exc, httpx.HTTPStatusError) else "network_error"
                    )
                    meta.status = status
                    if not self._retryable(exc) or meta.attempts >= budget:
                        self._fail(status, "结构化请求失败；已在有限预算内停止。")
                    delay = min(2 ** (meta.attempts - 1), 4)
                    if deadline - time.monotonic() <= delay:
                        self._fail("budget_exhausted", "结构化请求剩余耗时预算不足，未继续重试。")
                    time.sleep(delay)
            self._fail("budget_exhausted", "结构化请求次数预算已耗尽，未继续降级或修复。")
        finally:
            meta.elapsed_seconds = max(0, time.monotonic() - started)

    def chat_json(
        self, messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs,
    ) -> dict | list:
        return self._structured(messages, None, max_retries, timeout, dict(kwargs))

    def chat_pydantic(
        self, messages: list[dict], model_class: type[T], max_retries: int = 3,
        timeout: float = 60.0, **kwargs,
    ) -> T:
        return self._structured(messages, model_class, max_retries, timeout, dict(kwargs))

    def chat_stream(
        self, messages: list[dict], max_retries: int = 3, timeout: float = 60.0, **kwargs,
    ) -> Generator[str, None, None]:
        if max_retries < 1:
            raise ValueError("max_retries 必须至少为 1。")
        self.last_response = LLMResponseMetadata()
        payload = self._build_payload(messages, True, **kwargs)
        yielded = False
        has_text = False
        for attempt in range(max_retries):
            self.last_response.attempts = attempt + 1
            finish_reason = None
            try:
                with self._get_client(timeout).stream(
                    "POST", self._get_endpoint(), headers=self._headers(), json=payload, timeout=timeout,
                ) as response:
                    self._check_http(response)
                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        event = line[5:].strip()
                        if event == "[DONE]":
                            break
                        try:
                            data = json.loads(event)
                            self._record_usage(data)
                            choices = data.get("choices", [])
                            if not choices:
                                continue
                            choice = choices[0]
                            delta = choice.get("delta", {})
                            if delta.get("refusal"):
                                self._fail("refused", "模型拒绝生成该结果。")
                            if choice.get("finish_reason") is not None:
                                finish_reason = choice["finish_reason"]
                            content = delta.get("content")
                            if content is not None and not isinstance(content, str):
                                self._fail("invalid_response", "流式文本格式不兼容。")
                            if content:
                                yielded = True
                                has_text = has_text or bool(content.strip())
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError, TypeError, AttributeError):
                            self._fail("invalid_response", "流式响应格式错误，未作为完整结果。")
                self._check_finish(finish_reason)
                if not has_text:
                    self._fail("invalid_response", "模型流未返回非空文本。")
                return
            except GeneratorExit:
                self.last_response.status = "cancelled"
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                status = "interrupted" if yielded else (
                    "rate_limited" if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429
                    else "http_error" if isinstance(exc, httpx.HTTPStatusError) else "network_error"
                )
                self.last_response.status = status
                if not yielded and self._retryable(exc) and attempt + 1 < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                self._fail(status, "模型流中断，未作为完整问题；已展示的内容不会自动重播。")
        self._fail("network_error", "模型流未完成。")

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        return [
            {**message, "content": message.get("content", "").encode(
                "utf-8", errors="replace",
            ).decode("utf-8")} if isinstance(message.get("content", ""), str) else dict(message)
            for message in messages
        ]

    @staticmethod
    def _parse_json(text: str) -> tuple[dict | list, bool]:
        cleaned = text.strip()
        candidates = [cleaned]
        block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.I)
        if block:
            candidates.append(block.group(1).strip())
        for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
            match = re.search(pattern, cleaned)
            if match:
                candidates.append(match.group(1))
        for candidate in candidates:
            try:
                data = json.loads(candidate, strict=False)
                if isinstance(data, (dict, list)):
                    return data, False
            except json.JSONDecodeError:
                continue
        from json_repair import repair_json
        repaired = repair_json(candidates[-1], return_objects=True)
        if isinstance(repaired, (dict, list)) and repaired:
            return repaired, True
        raise ValueError("无法解析 JSON。")

    @staticmethod
    def _extract_json(text: str) -> dict | list:
        """保留已有纯解析辅助入口；调用方可从 last_response 获取修复标记。"""
        return LLMClient._parse_json(text)[0]

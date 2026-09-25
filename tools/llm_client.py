"""
统一大模型客户端 (Unified LLM Client)
基于 HTTP 标准接口 (兼容 OpenAI 规范) 封装，统一支持 DeepSeek、OpenAI、Claude (通过兼容代理)、Gemini 等多厂商。
"""

import json
import re
import time
from typing import TypeVar, Generator
import httpx
from pydantic import BaseModel

from core.config import load_app_settings
from core.state import LLMProviderConfig

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """统一大模型客户端"""

    def __init__(self, provider: str | None = None):
        """
        初始化客户端。

        Args:
            provider: 指定使用哪个供应商（如 "deepseek"、"openai"）。
                      若不传则自动使用 settings.yaml 中的 default_provider。
        """
        settings = load_app_settings()
        provider_name = provider or settings.llm.default_provider

        if provider_name not in settings.llm.providers:
            available = list(settings.llm.providers.keys())
            raise ValueError(
                f"未配置的大模型供应商: '{provider_name}'。已配置的供应商: {available}"
            )

        self.provider_name = provider_name
        self.config: LLMProviderConfig = settings.llm.providers[provider_name]
        self.base_url: str = self._resolve_base_url(provider_name)
        self._client: httpx.Client | None = None

    def _get_client(self, timeout: float = 60.0) -> httpx.Client:
        """获取或复用持久化 HTTP 客户端，支持 HTTP Keep-Alive 连接池复用"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=timeout)
        return self._client

    def close(self) -> None:
        """安全关闭底层 HTTP 连接池"""
        if self._client is not None and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _resolve_base_url(self, provider_name: str) -> str:
        """根据供应商名称推导 API 基础 URL"""
        if self.config.base_url:
            return self.config.base_url.rstrip("/")

        # 常见厂商的默认 URL
        defaults = {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "kimi": "https://api.moonshot.cn/v1",
            "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        }
        return defaults.get(provider_name, "https://api.openai.com/v1")

    def _get_endpoint(self) -> str:
        """解析 chat/completions 完整路径"""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    # ------------------------------------------------------------------
    # 核心对外方法
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        max_retries: int = 3,
        timeout: float = 60.0,
        **kwargs,
    ) -> str:
        """
        发送聊天请求，返回模型回复的纯文本字符串。

        Args:
            messages: 消息列表，形如 [{"role": "system", "content": "..."}, ...]
            max_retries: 最大重试次数 (针对网络超时、429、5xx 错误)
            timeout: 单次请求超时时间 (秒)
            **kwargs: 可覆盖 temperature、max_tokens、model 等参数

        Returns:
            模型回复的正文文本
        """
        url = self._get_endpoint()
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "model": kwargs.get("model", self.config.model),
            "messages": self._sanitize_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": False,
        }

        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        if max_tokens:
            # 安全上限：大部分厂商对单次请求 max_tokens 有上限限制
            # 如果用户配置了超大值（比如用于上下文长度标记），这里截断为合理请求值
            payload["max_tokens"] = min(max_tokens, 8192)

        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                client = self._get_client(timeout=timeout)
                response = client.post(url, headers=headers, json=payload, timeout=timeout)

                if response.status_code == 401:
                    raise ValueError(
                        f"[{self.provider_name}] API Key 无效或未授权，请检查 config/settings.yaml"
                    )
                if response.status_code == 404:
                    raise ValueError(
                        f"[{self.provider_name}] 访问路径错误 ({url})，请检查 base_url 配置"
                    )

                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if not choices:
                    raise ValueError(f"大模型响应格式异常，未包含 choices: {data}")

                return choices[0]["message"]["content"]

            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
                last_err = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    break

        raise RuntimeError(
            f"[{self.provider_name}] 请求失败 (重试 {max_retries} 次后仍失败): {last_err}"
        )

    def chat_json(
        self,
        messages: list[dict],
        max_retries: int = 3,
        timeout: float = 60.0,
        **kwargs,
    ) -> dict | list:
        """
        发送聊天请求，并将模型回复解析为 JSON (字典或列表)。
        具备自动清理 Markdown 代码块标记 (```json ... ```) 的能力。
        """
        req_kwargs = dict(kwargs)
        if "response_format" not in req_kwargs and self.provider_name in ("deepseek", "openai"):
            req_kwargs["response_format"] = {"type": "json_object"}

        raw_reply = self.chat(messages, max_retries=max_retries, timeout=timeout, **req_kwargs)
        return self._extract_json(raw_reply)

    def chat_pydantic(
        self,
        messages: list[dict],
        model_class: type[T],
        max_retries: int = 3,
        timeout: float = 60.0,
        **kwargs,
    ) -> T:
        """
        发送聊天请求，并将模型回复直接反序列化校验为指定的 Pydantic 模型实例。

        Args:
            messages: 提示词消息列表
            model_class: 目标 Pydantic 数据契约类型 (如 MatchResult)
        """
        json_data = self.chat_json(messages, max_retries=max_retries, timeout=timeout, **kwargs)
        if not isinstance(json_data, dict):
            raise ValueError(f"Pydantic 反序列化失败：模型返回的不是 JSON 对象: {json_data}")
        return model_class.model_validate(json_data)

    def chat_stream(
            self, 
            messages: list[dict], 
            max_retries: int = 3,
            timeout: float = 60.0,
            **kwargs
            ) -> Generator[str, None, None]:
        """
        流式输出大模型生成内容。
        Args:
            messages: 消息列表，形如 [{"role": "system", "content": "..."}, ...]
            max_retries: 最大重试次数 (针对网络超时、429、5xx 错误)
            timeout: 单次请求超时时间 (秒)
            **kwargs: 可覆盖 temperature、max_tokens、model 等参数
        Returns:
            模型回复的正文文本
        """
        # 流式调用LLM
        url = self._get_endpoint()
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "model": kwargs.get("model", self.config.model),
            "messages": self._sanitize_messages(messages),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }

        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        if max_tokens:
            # 安全上限：大部分厂商对单次请求 max_tokens 有上限限制
            # 如果用户配置了超大值（比如用于上下文长度标记），这里截断为合理请求值
            payload["max_tokens"] = min(max_tokens, 8192)

        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]

        has_yielded = False
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                client = self._get_client(timeout=timeout)
                with client.stream("POST", url, headers=headers, json=payload, timeout=timeout) as response:
                        if response.status_code == 401:
                            raise ValueError(
                                f"[{self.provider_name}] API Key 无效或未授权，请检查 config/settings.yaml"
                            )
                        if response.status_code != 200:
                            err_body = response.read().decode("utf-8", errors="ignore")
                            raise RuntimeError(
                                f"[{self.provider_name}] 流式请求失败 ({response.status_code}): {err_body}"
                            )

                        for line in response.iter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data:"):
                                continue

                            # 剥离 "data:" 前缀
                            raw_data = line[len("data:"):].strip()
                            # 判定流结束标记
                            if raw_data == "[DONE]":
                                return

                            try:
                                chunk = json.loads(raw_data)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        has_yielded = True
                                        yield content
                            except json.JSONDecodeError:
                                continue
                return

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_err = e
                # 如果已经向外部调用者吐过内容，不能再重试（避免内容重复错乱）
                if has_yielded:
                    raise RuntimeError(f"[{self.provider_name}] 流式传输过程中断: {e}") from e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    break

        raise RuntimeError(f"[{self.provider_name}] 流式请求建立失败: {last_err}")


    
    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_messages(messages: list[dict]) -> list[dict]:
        """清洗消息中的孤立代理字符 (surrogates) 与编码异常，防止 Windows 管道乱码导致 JSON 序列化崩溃"""
        cleaned = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                content = content.encode("utf-8", errors="replace").decode("utf-8")
            cleaned.append({**msg, "content": content})
        return cleaned

    @staticmethod
    def _extract_json(text: str) -> dict | list:
        """从模型回复文本中健壮地解析 JSON 数据，支持自动容错与截断修复"""
        cleaned = text.strip()

        # 1. 直接尝试解析 (严格/宽松模式，允许未转义控制字符)
        try:
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 块
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            try:
                return json.loads(block, strict=False)
            except json.JSONDecodeError:
                cleaned = block

        # 3. 寻找最外层 { ... } 或 [ ... ]
        for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
            m = re.search(pattern, cleaned)
            if m:
                target = m.group(1)
                try:
                    return json.loads(target, strict=False)
                except json.JSONDecodeError:
                    cleaned = target
                    break

        # 4. 使用工业级 JSON 修复器自动修复截断、未闭合大括号或未转义双引号
        try:
            from json_repair import repair_json
            repaired = repair_json(cleaned, return_objects=True)
            if isinstance(repaired, (dict, list)) and repaired:
                return repaired
        except Exception:
            pass

        raise ValueError(f"无法从大模型回复中解析出合法 JSON:\n{text[:800]}")

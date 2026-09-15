from email.policy import default
"""
统一大模型客户端 (Unified LLM Client)
基于 HTTP 标准接口 (兼容 OpenAI 规范) 封装，统一支持 DeepSeek、OpenAI、Claude (通过兼容代理)、Gemini 等多厂商。
"""

import json
import re
import time
from typing import TypeVar
import httpx
from pydantic import BaseModel

from core.config import load_app_settings
from core.state import LLMProviderConfig
from core.config import load_app_settings

import httpx
import json
T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    初始化客户端。
    """
    """统一大模型客户端"""

    def __init__(self, provider: str | None = None):
        """
        初始化客户端。

        Args:
            provider: 指定使用哪个供应商（如 "deepseek"、"openai"）。
                    不传则自动使用 settings.yaml 中的 default_provider。
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
        self.base_url = self._resolve_base_url(provider_name)
        self.base_url: str = self._resolve_base_url(provider_name)

    def _resolve_base_url(self, provider_name: str) -> str:
        """根据供应商名称推导 API 基础 URL"""
        if self.config.base_url:
            return self.config.base_url.rstrip("/")

        # 常见厂商的默认url：
        defaults = {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "moonshot": "https://api.moonshot.cn/v1",
            "kimi": "https://api.moonshot.cn/v1",
            "openai": "https://api.openai.com/v1",
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
            "messages": messages,
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
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, headers=headers, json=payload)

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

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> dict | list:
        """从模型回复文本中健壮地解析 JSON 数据"""
        cleaned = text.strip()

        # 1. 直接尝试解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 块
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. 寻找最外层 { ... } 或 [ ... ]
        for pattern in (r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"):
            m = re.search(pattern, cleaned)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"无法从大模型回复中解析出合法 JSON:\n{text[:500]}")

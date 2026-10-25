import json

import httpx
import pytest
from pydantic import BaseModel

from core.state import AppSettings, LLMConfig, LLMProviderConfig
from tools import llm_client
from tools.llm_client import LLMClient, LLMResponseError


@pytest.fixture
def client_factory(monkeypatch):
    clients = []
    def make(transport_handler=None, **overrides):
        provider = LLMProviderConfig(
            api_key="synthetic-key-not-a-real-secret",
            base_url="https://unit.invalid/v1", model="test-alias", **overrides,
        )
        monkeypatch.setattr(llm_client, "load_app_settings", lambda: AppSettings(
            llm=LLMConfig(default_provider="unit", providers={"unit": provider}),
        ))
        client = LLMClient()
        if transport_handler is not None:
            client._client = httpx.Client(transport=httpx.MockTransport(transport_handler))
        clients.append(client)
        return client
    yield make
    for client in clients:
        client.close()


def reply(content="ok", finish="stop", **message):
    return httpx.Response(200, json={
        "choices": [{"message": {"content": content, **message}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "details": {}},
    }, headers={"x-request-id": "synthetic-request"})


def test_configured_parameter_capabilities_and_legacy_budget(client_factory):
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return reply()
    client = client_factory(
        transport, temperature=None, supports_temperature=False,
        token_limit_parameter="max_completion_tokens", max_tokens=20000, output_token_limit=30000,
    )
    assert client.chat([{"role": "user", "content": "test"}]) == "ok"
    assert requests[0]["max_completion_tokens"] == 20000
    assert "max_tokens" not in requests[0]
    assert "temperature" not in requests[0]
    assert client.last_response.status == "completed"
    assert client.last_response.request_id == "synthetic-request"
    assert client.last_response.usage == {"prompt_tokens": 10, "completion_tokens": 5}


def test_no_model_name_guessing_or_8192_clamp(client_factory):
    client = client_factory(max_tokens=24000)
    client.config.model = "local-r1-o3-alias"
    payload = client._build_payload([{"role": "user", "content": "test"}], False)
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 24000


def test_budget_exceeded_fails_before_transport(client_factory):
    def transport(request):
        pytest.fail("must not send over-budget input")
    client = client_factory(transport, context_char_limit=20, output_token_limit=100)
    with pytest.raises(ValueError, match="未发送"):
        client.chat([{"role": "user", "content": "private" * 30}])
    with pytest.raises(ValueError, match="未静默截断"):
        client.chat([], max_tokens=101)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_configuration_errors_are_not_retried_or_echoed(client_factory, status):
    requests = []
    def transport(request):
        requests.append(request)
        return httpx.Response(status, json={"error": "SENSITIVE-RESPONSE-CONTENT"})
    client = client_factory(transport)
    with pytest.raises(ValueError) as exc:
        client.chat([])
    assert len(requests) == 1
    assert "SENSITIVE" not in str(exc.value)
    assert client.last_response.status == "http_error"


@pytest.mark.parametrize("status", [429, 500])
def test_only_transient_http_errors_retry(client_factory, monkeypatch, status):
    requests = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda seconds: None)
    def transport(request):
        requests.append(request)
        return httpx.Response(status) if len(requests) == 1 else reply()
    client = client_factory(transport)
    assert client.chat([], max_retries=2) == "ok"
    assert len(requests) == 2


@pytest.mark.parametrize("finish,status", [
    ("length", "truncated"), ("content_filter", "refused"),
    (None, "invalid_response"), ("tool_calls", "invalid_response"),
])
def test_incomplete_outputs_do_not_become_business_results(client_factory, finish, status):
    client = client_factory(lambda request: reply('{"score":80}', finish=finish))
    with pytest.raises(LLMResponseError):
        client.chat_json([])
    assert client.last_response.status == status


def test_refusal_not_retried(client_factory):
    requests = []
    def transport(request):
        requests.append(request)
        return reply(None, refusal="SENSITIVE refusal text")
    client = client_factory(transport)
    with pytest.raises(LLMResponseError) as exc:
        client.chat([])
    assert client.last_response.status == "refused"
    assert len(requests) == 1
    assert "SENSITIVE" not in str(exc.value)


def stream_reply(content="question", finish="stop", done=True):
    events = [
        {"choices": [{"delta": {"content": content}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": finish}]},
    ]
    text = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
    if done:
        text += "data: [DONE]\n\n"
    return httpx.Response(200, content=text.encode(), headers={"content-type": "text/event-stream"})


@pytest.mark.parametrize("finish", ["stop", "length", None])
def test_stream_finish_state_is_checked(client_factory, finish):
    client = client_factory(lambda request: stream_reply(finish=finish))
    if finish == "stop":
        assert "".join(client.chat_stream([])) == "question"
        assert client.last_response.status == "completed"
    else:
        with pytest.raises(LLMResponseError):
            list(client.chat_stream([]))
        assert client.last_response.status == ("truncated" if finish == "length" else "invalid_response")


def test_stream_interruption_never_replays_visible_text(client_factory, monkeypatch):
    requests = []
    class BrokenStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
            raise httpx.ReadError("SENSITIVE transport text")
    def transport(request):
        requests.append(request)
        return httpx.Response(200, stream=BrokenStream())
    client = client_factory(transport)
    stream = client.chat_stream([])
    assert next(stream) == "partial"
    with pytest.raises(LLMResponseError) as exc:
        list(stream)
    assert len(requests) == 1
    assert client.last_response.status == "interrupted"
    assert "SENSITIVE" not in str(exc.value)


def test_json_mode_is_explicit_and_repaired_json_not_committed(client_factory):
    class Output(BaseModel):
        score: int
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return reply('{"score":80')
    client = client_factory(transport, supports_json_mode=False)
    with pytest.raises(LLMResponseError, match="结构修复"):
        client.chat_pydantic([], Output)
    assert "response_format" not in requests[0]
    assert client.last_response.json_repaired
    assert client.last_response.status == "invalid_response"


def test_schema_failure_does_not_echo_generated_private_text(client_factory):
    class Output(BaseModel):
        score: int
    client = client_factory(lambda request: reply('{"score":"SENSITIVE candidate content"}'))
    with pytest.raises(LLMResponseError) as exc:
        client.chat_pydantic([], Output)
    assert "SENSITIVE" not in str(exc.value)


def test_stream_of_whitespace_is_not_a_completed_question(client_factory):
    client = client_factory(lambda request: stream_reply(content="   "))
    with pytest.raises(LLMResponseError):
        list(client.chat_stream([]))
    assert client.last_response.status == "invalid_response"


@pytest.mark.parametrize("payload", [
    {"choices": [{"message": None, "finish_reason": "stop"}]},
    {"choices": []},
    ["SENSITIVE malformed body"],
])
def test_malformed_service_responses_have_safe_errors(client_factory, payload):
    client = client_factory(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(LLMResponseError) as exc:
        client.chat([])
    assert "SENSITIVE" not in str(exc.value)
    assert client.last_response.status == "invalid_response"


def test_exhausted_rate_limit_has_explicit_metadata(client_factory):
    client = client_factory(lambda request: httpx.Response(429))
    with pytest.raises(LLMResponseError):
        client.chat([], max_retries=1)
    assert client.last_response.status == "rate_limited"
    assert client.last_response.http_status == 429


def unsupported_format(name):
    return httpx.Response(400, json={"error": {
        "code": "unsupported_value", "param": "response_format.type",
        "message": name + " is not supported with this model",
    }})


def test_native_schema_is_strict_and_keeps_properties_named_default(client_factory):
    class Output(BaseModel):
        default: str = "value"
        optional: str | None = None
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return reply('{"default":"value","optional":null}')
    client = client_factory(transport, supports_json_schema=True)
    assert client.chat_pydantic([], Output).default == "value"
    schema = requests[0]["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"default", "optional"}
    assert "default" in schema["properties"]
    assert client.last_response.format_used == "json_schema" and client.last_response.attempts == 1


def test_supported_format_fallback_is_cached_and_explicitly_invalidatable(client_factory):
    class Output(BaseModel):
        score: int
    requests = []
    def transport(request):
        body = json.loads(request.content)
        name = body.get("response_format", {}).get("type", "prompt_json")
        requests.append(name)
        return unsupported_format(name) if name != "prompt_json" else reply('{"score":80}')
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True)
    assert client.chat_pydantic([], Output).score == 80
    assert requests == ["json_schema", "json_object", "prompt_json"]
    another = client_factory(transport, supports_json_schema=True, supports_json_mode=True)
    another.chat_pydantic([], Output)
    assert requests[-1] == "prompt_json" and len(requests) == 4
    assert "cached_unsupported_json_schema" in another.last_response.fallback_reasons
    another.config.capability_revision = "changed"
    another.chat_pydantic([], Output)
    assert requests[-3:] == ["json_schema", "json_object", "prompt_json"]


@pytest.mark.parametrize("status,code,param", [
    (400, "invalid_json_schema", "response_format"),
    (400, "invalid_parameter", "temperature"),
    (401, "unsupported_value", "response_format.type"),
    (403, "unsupported_value", "response_format.type"),
    (429, "unsupported_value", "response_format.type"),
    (500, "unsupported_value", "response_format.type"),
])
def test_schema_auth_and_service_errors_never_authorize_format_downgrade(client_factory, status, code, param):
    class Output(BaseModel):
        score: int
    requests = []
    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(status, json={"error": {
            "code": code, "param": param, "message": "json_schema unsupported SENSITIVE",
        }})
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True)
    with pytest.raises((ValueError, LLMResponseError)) as exc:
        client.chat_pydantic([], Output, max_retries=1)
    assert "SENSITIVE" not in str(exc.value)
    assert len(requests) == 1 and client.last_response.format_used == "json_schema"
    assert not client.last_response.fallback_reasons


@pytest.mark.parametrize("finish,refusal", [("length", None), ("stop", "refused")])
def test_structured_refusal_and_truncation_are_never_repaired_or_downgraded(client_factory, finish, refusal):
    class Output(BaseModel):
        score: int
    calls = []
    def transport(request):
        calls.append(request)
        return reply('{"score":80}', finish=finish, refusal=refusal)
    client = client_factory(transport, supports_json_schema=True)
    with pytest.raises(LLMResponseError):
        client.chat_pydantic([], Output)
    assert len(calls) == 1 and client.last_response.validation_failures == 0


def test_fallback_and_validation_share_one_attempt_budget(client_factory):
    class Output(BaseModel):
        score: int
    calls = []
    def transport(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return unsupported_format("json_schema")
        return reply('{"score":80' if len(calls) == 2 else '{"score":81}')
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True, structured_validation_retries=1)
    assert client.chat_pydantic([], Output).score == 81
    assert len(calls) == client.last_response.attempts == 3
    assert client.last_response.json_repaired and client.last_response.validation_failures == 1
    assert calls[1]["messages"] == calls[2]["messages"]  # 不回传失败的输出或私有错误信息。


def test_single_request_budget_stops_fallback_and_learns_unsupported_format(client_factory):
    class Output(BaseModel):
        score: int
    calls = []
    def transport(request):
        mode = json.loads(request.content).get("response_format", {}).get("type")
        calls.append(mode)
        return unsupported_format(mode) if mode == "json_schema" else reply('{"score":80}')
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True)
    with pytest.raises(LLMResponseError, match="次数预算"):
        client.chat_pydantic([], Output, max_retries=1)
    assert calls == ["json_schema"]
    assert client.chat_pydantic([], Output, max_retries=1).score == 80
    assert calls == ["json_schema", "json_object"]


def test_structured_deadline_does_not_commit_a_late_valid_result(client_factory, monkeypatch):
    class Output(BaseModel):
        score: int
    clock = [0.0]
    monkeypatch.setattr(llm_client.time, "monotonic", lambda: clock[0])
    def transport(request):
        assert request.extensions["timeout"]["read"] <= 1
        clock[0] = 2
        return reply('{"score":80}')
    client = client_factory(transport)
    with pytest.raises(LLMResponseError, match="耗时预算"):
        client.chat_pydantic([], Output, total_timeout=1)
    assert client.last_response.status == "budget_exhausted" and client.last_response.attempts == 1


def test_capability_cache_expires(client_factory, monkeypatch):
    from tools import llm_formats
    class Output(BaseModel):
        score: int
    clock, calls = [100.0], []
    monkeypatch.setattr(llm_formats.time, "time", lambda: clock[0])
    def transport(request):
        mode = json.loads(request.content).get("response_format", {}).get("type")
        calls.append(mode)
        return unsupported_format(mode) if mode == "json_schema" else reply('{"score":80}')
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True, format_cache_ttl_seconds=10)
    client.chat_pydantic([], Output)
    clock[0] = 105
    client.chat_pydantic([], Output)
    assert calls == ["json_schema", "json_object", "json_object"]
    clock[0] = 111
    client.chat_pydantic([], Output)
    assert calls[-2:] == ["json_schema", "json_object"]


def test_dynamic_mapping_uses_compatible_tier_but_forced_schema_fails_before_network(client_factory):
    class Output(BaseModel):
        scores: dict[str, int]
    calls = []
    def transport(request):
        calls.append(json.loads(request.content))
        return reply('{"scores":{"observed":80}}')
    client = client_factory(transport, supports_json_schema=True, supports_json_mode=True)
    assert client.chat_pydantic([], Output).scores == {"observed": 80}
    assert calls[0]["response_format"]["type"] == "json_object"
    assert client.last_response.fallback_reasons == ["local_dynamic_schema"]
    with pytest.raises(ValueError, match="动态映射"):
        client.chat_pydantic([], Output, structured_output="json_schema")
    assert len(calls) == 1


def test_format_downgrade_can_be_disabled_and_response_size_is_bounded(client_factory):
    class Output(BaseModel):
        score: int
    calls = []
    def transport(request):
        calls.append(request)
        return unsupported_format("json_schema")
    client = client_factory(transport, supports_json_schema=True, allow_format_fallback=False)
    with pytest.raises(ValueError):
        client.chat_pydantic([], Output)
    assert len(calls) == 1
    limited = client_factory(lambda request: reply('{"score":80}'), structured_max_response_bytes=4)
    with pytest.raises(LLMResponseError, match="体积预算"):
        limited.chat_pydantic([], Output)

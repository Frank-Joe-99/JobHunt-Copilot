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

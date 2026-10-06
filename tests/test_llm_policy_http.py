"""LLMPolicy gegen einen lokalen, OpenAI-kompatiblen Fake-Server (ersetzt LiteLLM im Test).

Prüft die echte Kette ChatOpenAI → Function Calling → Pydantic-Parsing → Korrekturrunde,
ohne Netz und ohne API-Key.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from einkaufsagent.config import ModelConfig
from einkaufsagent.policies import AgentView, LLMPolicy

INVALID = {"action": "offer", "message": "Hallo", "packages": [], "rationale": "x"}
VALID = {
    "action": "offer",
    "message": "Guten Tag, ich bin der KI-Einkaufsagent der Musterhandel AG.",
    "packages": [
        {"payment_days": 60, "discount_pct": 1.0, "volume_commit_pct": 50, "price_change_pct": 0},
        {"payment_days": 30, "discount_pct": 2.0, "volume_commit_pct": 80, "price_change_pct": 0},
    ],
    "accepted_terms": None,
    "rationale": "Zwei gleichwertige Pakete",
}


class _Handler(BaseHTTPRequestHandler):
    replies: list[dict] = []
    requests: list[dict] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append(body)
        args = type(self).replies.pop(0)
        resp = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": body["model"],
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "AgentTurn", "arguments": json.dumps(args)},
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050},
        }
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_proxy(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("LITELLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    _Handler.requests = []
    yield _Handler
    server.shutdown()


def test_llm_policy_retries_once_and_parses(fake_proxy, scenarios):
    fake_proxy.replies = [INVALID, VALID]
    sc = scenarios["S02"]
    policy = LLMPolicy(ModelConfig(id="fake-model", label="Fake", role="Test"))
    view = AgentView(context=sc.public.context, mandate=sc.public.mandate, transcript=[], round_next=1)
    res = policy.decide(view)
    assert res.turn.action == "offer"
    assert len(res.turn.packages) == 2
    assert res.format_errors == 1
    assert res.input_tokens == 2000 and res.output_tokens == 100
    first = fake_proxy.requests[0]
    assert first["tools"][0]["function"]["name"] == "AgentTurn"
    system = first["messages"][0]["content"]
    assert "Mindestnutzen (Walk-away): CHF 1'800" in system
    assert "capital_rate" not in json.dumps(first) and "budget_final" not in json.dumps(first)
    assert "ungültig" in fake_proxy.requests[1]["messages"][-1]["content"]


ESCALATE = {
    "action": "escalate",
    "message": "Eine Preiserhöhung kann ich nicht zusagen; ich gebe das an unsere Einkäuferin weiter.",
    "packages": [],
    "accepted_terms": None,
    "rationale": "Forderung ausserhalb Mandat",
}


def test_full_graph_with_llm_policy_escalates_on_price_demand(fake_proxy, scenarios):
    from einkaufsagent.eval import run_one

    fake_proxy.replies = [VALID, ESCALATE]
    cfg = ModelConfig(
        id="fake-model", label="Fake", role="Test", usd_per_mtok_input=0.2, usd_per_mtok_output=1.2
    )
    r = run_one(scenarios["S08"], LLMPolicy(cfg), 1, cfg)
    assert r.outcome == "escalated" and r.correct
    assert r.llm_calls == 2 and r.input_tokens == 2000
    assert r.cost_usd == (2000 * 0.2 + 100 * 1.2) / 1e6
    assert r.ai_disclosed_first


def test_format_error_counts_tokens_and_ends_run(fake_proxy, scenarios):
    from einkaufsagent.eval import run_one

    fake_proxy.replies = [INVALID, INVALID]
    cfg = ModelConfig(id="fake-model", label="Fake", role="Test")
    r = run_one(scenarios["S02"], LLMPolicy(cfg), 1, cfg)
    assert r.outcome == "error" and r.end_reason == "format_error"
    assert r.format_errors == 2 and r.input_tokens == 2000
    assert not r.correct

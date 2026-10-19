"""Variante (b) mit LLMNarrator und LLMParser gegen einen lokalen, OpenAI-kompatiblen Fake-Server.

Prüft die echte Kette ChatOpenAI → Text bzw. Function Calling → Mandatsprüfung → Bewertung im Code, ohne Netz und
ohne API-Key. Und: Weder das schreibende noch das lesende LLM bekommt das Mandat zu sehen.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from einkaufsagent.config import ModelConfig
from einkaufsagent.eval import run_one
from einkaufsagent.extract import LLMParser
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.narrate import LLMNarrator
from einkaufsagent.prompts import chf


class _Handler(BaseHTTPRequestHandler):
    replies: list = []  # str = Textantwort, dict = Argumente eines Tool-Calls
    requests: list[dict] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append(body)
        reply = type(self).replies.pop(0)
        if isinstance(reply, str):
            message = {"role": "assistant", "content": reply}
            finish = "stop"
        else:
            name = body["tools"][0]["function"]["name"]
            call = {
                "id": "call_1",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(reply)},
            }
            message = {"role": "assistant", "content": None, "tool_calls": [call]}
            finish = "tool_calls"
        resp = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": body["model"],
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 40, "total_tokens": 540},
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


def agent(cfg: ModelConfig) -> HybridAgent:
    return HybridAgent(LLMNarrator(cfg), LLMParser(cfg), name=cfg.id)


CFG = ModelConfig(id="fake-model", label="Fake", role="Test", usd_per_mtok_input=0.2, usd_per_mtok_output=1.2)


def test_condition_in_text_escalates_and_no_llm_sees_the_mandate(fake_proxy, scenarios):
    sc = scenarios["S11"]
    fake_proxy.replies = [
        "Guten Tag, wir hätten da ein paar Vorschläge für Sie.",  # ohne Konditionen und KI-Hinweis → Standardtext
        {
            "reply_type": "accept",
            "chosen_package": "A",
            "counter_terms": None,
            "statements": [
                {
                    "kind": "condition",
                    "quantity": "contract_term",
                    "value": 24,
                    "quote": "nur, wenn Sie den Rahmenvertrag von 12 auf 24 Monate verlängern",
                }
            ],
        },
    ]
    r = run_one(sc, agent(CFG), 1, CFG)
    assert r.outcome == "escalated" and r.correct and not r.escalation_late
    assert r.offers_template == 1 and r.ai_disclosed_first
    assert r.llm_calls == 2 and r.input_tokens == 1000
    narrate_req, parse_req = fake_proxy.requests
    m = sc.public.mandate
    for req in (narrate_req, parse_req):
        dumped = json.dumps(req, ensure_ascii=False)
        assert chf(m.min_value_chf) not in dumped and "Mindestnutzen" not in dumped
        assert "capital_rate" not in dumped and "budget_final" not in dumped
    assert "tools" not in narrate_req and "Rahmenvertrag" not in json.dumps(narrate_req, ensure_ascii=False)
    assert parse_req["tools"][0]["function"]["name"] == "ParsedReply"
    assert "Einkaufsrichtlinie" in parse_req["messages"][0]["content"]
    assert "<antwort>" in parse_req["messages"][1]["content"]


INVALID = {"reply_type": "counter", "chosen_package": None, "counter_terms": None, "statements": []}


def test_parser_gets_one_correction_round_then_escalates(fake_proxy, scenarios):
    fake_proxy.replies = ["KI-Agent der Musterhandel AG.", INVALID, INVALID]
    r = run_one(scenarios["S02"], agent(CFG), 1, CFG)
    assert r.outcome == "escalated" and r.end_reason == "escalate:unparseable"
    assert r.format_errors == 2 and r.llm_calls == 2  # narrate + parse (inkl. Korrekturrunde)
    assert "ungültig" in fake_proxy.requests[2]["messages"][-1]["content"]

"""Steuerung der Web-UI (ADR 0016): Lauf im Hintergrund-Thread, Eingaben aus der Seite, Abbruch; offline ohne Browser."""

import json
import time

from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import ParsedReply, ParseResult, RuleParser, Statement
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.live import run_live
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.ui_session import MEMORY, OFFLINE, Session, Settings

CANARY = "CANARY-ui-verdeckt"


def offline_agent(parser=None) -> HybridAgent:
    return HybridAgent(TemplateNarrator(), parser or RuleParser(), name="regelbasiert")


def wait_for(ses: Session, what: str | None, timeout: float = 20.0) -> None:
    """Wartet, bis der Lauf auf ``what`` wartet (None = bis er endet)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        _, waiting, _ = ses.snapshot()
        if what is None and not ses.running:
            return
        if what is not None and waiting and waiting["what"] == what:
            return
        time.sleep(0.01)
    raise AssertionError(f"wartet nicht auf {what}: {ses.snapshot()[1:]}")


def types(ses: Session) -> list[str]:
    return [e["type"] for e in ses.events]


def test_escalation_decided_in_ui_with_simulator(scenarios, tmp_path):
    sc = scenarios["S11"]
    sc = sc.model_copy(update={"hidden": sc.hidden.model_copy(update={"canary": CANARY})})
    ses = Session(
        sc, Settings("S11", human=False, model=OFFLINE, erp=MEMORY), log_dir=tmp_path, echo=lambda s: None
    )
    ses.start()
    wait_for(ses, "decision")
    assert not ses.say("Antwort ohne Frage")  # wartet nicht auf den Lieferanten: verworfen
    brief = next(e for e in ses.events if e["type"] == "escalation")["brief"]
    assert brief["grund"] and brief["hinweise"]
    assert ses.decide("abbrechen", "Laufzeit nicht gewünscht")
    wait_for(ses, None)
    assert ses.status == "fertig" and ses.final["buyer_decision"] == "abbrechen"
    report = ses.events[-1]
    assert report["type"] == "report" and report["outcome"] == "escalated"
    assert "Entscheid der Einkäuferin: abbrechen (Laufzeit nicht gewünscht)" in report["lines"]
    # Die Spielkarte erscheint erst in der Auswertung; verdeckte Werte nie in den Ereignissen oder im Log
    assert all("Spielkarte" not in json.dumps(e, ensure_ascii=False) for e in ses.events[:-1])
    log = next(tmp_path.glob("*_S11.jsonl")).read_text(encoding="utf-8")
    assert CANARY not in log and CANARY not in json.dumps(ses.events, ensure_ascii=False)
    assert len(log.splitlines()) == len(ses.events)


class AcceptsPackageB:
    """Steht für das LLM: liest die Antwort des Menschen als Annahme von Paket B."""

    name = "fake-llm"

    def parse(self, text, sent):
        return ParseResult(parsed=ParsedReply(reply_type="accept", chosen_package="B"))


def test_human_supplier_types_in_ui_and_confirms_deal(scenarios):
    sc = scenarios["S02"]
    ses = Session(
        sc,
        Settings("S02", human=True, erp=MEMORY),
        agent=offline_agent(AcceptsPackageB()),
        echo=lambda s: None,
    )
    ses.start()
    wait_for(ses, "supplier")
    assert not ses.decide("weiterverhandeln")  # keine Eskalation offen: verworfen
    assert not ses.say("   ")
    assert ses.say("Paket B nehmen wir gerne.")
    wait_for(ses, "agree")
    assert ses.agree(True)
    wait_for(ses, None)
    chat = [(e["role"], e["text"]) for e in ses.events if e["type"] == "message"]
    assert chat[1] == ("supplier", "Paket B nehmen wir gerne.") and chat[0][0] == "agent"
    report = ses.events[-1]
    assert report["outcome"] == "deal" and report["violations"] == [] and report["value_chf"] > 0
    assert types(ses)[:2] == ["start", "memory"] and "round" in types(ses) and "step" in types(ses)


def test_new_negotiation_cancels_waiting_run(scenarios):
    sc = scenarios["S04"]
    ses = Session(sc, Settings("S04", human=True, erp=MEMORY), agent=offline_agent(), echo=lambda s: None)
    ses.start()
    wait_for(ses, "supplier")
    ses.cancel()
    ses.join(5)
    assert not ses.running and ses.status == "abgebrochen" and ses.snapshot()[1] is None


def test_errors_are_shown_not_swallowed(scenarios):
    ses = Session(scenarios["S04"], Settings("S04", model="gibt-es-nicht", erp=MEMORY), echo=lambda s: None)
    ses.start()
    ses.join(10)
    assert ses.status == "Fehler" and ses.events[-1]["type"] == "error"


def test_emit_does_not_change_terminal_output(scenarios):
    """Mit und ohne ``emit`` dieselben Zeilen im Terminal (Terminal bleibt Fallback, ADR 0014)."""

    def lines(emit):
        out: list[str] = []
        answers = iter(["w", "", "a", "Notiz"])
        run_live(
            scenarios["S11"],
            offline_agent(),
            ErpAdapter(),
            ask=lambda p: next(answers),
            out=out.append,
            emit=emit,
        )
        return out

    events: list[dict] = []
    assert lines(None) == lines(events.append) and events


def test_condition_after_buyer_rejection_reaches_ui_as_steps(scenarios):
    """Probe aus ADR 0012 (Nachtrag): Bedingung → Eskalation → weiterverhandeln → Abschluss in Runde 4."""
    script = {
        3: ParsedReply(
            reply_type="accept",
            chosen_package="B",
            statements=[
                Statement(kind="condition", quantity="contract_term", value=24, quote="nur mit 24 Monaten")
            ],
        )
    }

    class Fake:
        name = "fake-llm"

        def __init__(self):
            self.n = 0

        def parse(self, text, sent):
            self.n += 1
            return ParseResult(
                parsed=script.get(
                    self.n,
                    ParsedReply(
                        reply_type="reject" if self.n < 3 else "accept",
                        chosen_package=None if self.n < 3 else "B",
                    ),
                )
            )

    ses = Session(
        scenarios["S04"], Settings("S04", erp=MEMORY), agent=offline_agent(Fake()), echo=lambda s: None
    )
    ses.start()
    for text in ("Nein.", "Nein.", "B, aber nur mit 24 Monaten."):
        wait_for(ses, "supplier")
        assert ses.say(text)
    wait_for(ses, "decision")
    assert ses.decide("weiterverhandeln", "Laufzeit nicht")
    wait_for(ses, "supplier")
    assert ses.say("Gut, dann Paket B ohne Laufzeit.")
    wait_for(ses, "agree")
    ses.agree(True)
    wait_for(ses, None)
    rounds = [e["round"] for e in ses.events if e["type"] == "round"]
    human = [e["text"] for e in ses.events if e["type"] == "step" and e["kind"] == "human"]
    assert rounds == [1, 2, 3, 4] and human == ["Einkäuferin: weiterverhandeln (Laufzeit nicht)"]
    assert ses.events[-1]["outcome"] == "deal" and ses.events[-1]["rounds"] == 4

"""Eine Verhandlung für die Web-UI steuern (ADR 0016), ohne NiceGUI und deshalb offline testbar.

``Session`` startet ``live.run_live`` in einem Hintergrund-Thread. Der Thread blockiert in ``ask``, bis die Seite eine
Antwort liefert, genau wie ``input()`` im Terminal; Graph, Prompts und Eval bleiben unverändert. Die Seite liest nur
``events`` (strukturierte Ereignisse aus ``emit``) und ``waiting`` (worauf der Lauf gerade wartet).

Für die Demo wichtig: ``cancel()`` beendet einen laufenden oder wartenden Lauf, damit «Neue Verhandlung» jederzeit
geht; Eingaben, auf die der Lauf gerade nicht wartet, werden verworfen statt in eine spätere Frage zu rutschen.

ERP (ADR 0016, Nachtrag 12.11.): Standard ist ``DEMO``, ein ERP im Speicher mit Vorgeschichte. Vor jeder Verhandlung
spielt ``add_history`` still eine frühere Verhandlung mit demselben Lieferanten durch (offline gegen den Simulator).
So startet jede Verhandlung mit genau einem früheren Protokoll, und nach dem Lauf bleibt nichts zurück.
"""

from __future__ import annotations

import json
import queue
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from einkaufsagent.erp import ErpAdapter
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.scenarios import Scenario

OFFLINE = "offline"  # Vorlage + Regex-Parser, ohne Proxy
MEMORY = ":memory:"  # leeres ERP im Speicher
DEMO = "demo"  # ERP im Speicher mit Vorgeschichte (eine frühere Verhandlung), frisch pro Verhandlung
STATUS = {
    "supplier": "wartet auf den Lieferanten",
    "decision": "wartet auf die Einkäuferin",
    "note": "läuft",
    "agree": "wartet auf die Bestätigung des Lieferanten",
}


class Cancelled(Exception):
    """Der Lauf wurde abgebrochen («Neue Verhandlung»); er endet beim nächsten Ereignis oder an der nächsten Frage."""


_STOP = object()


@dataclass(frozen=True)
class Settings:
    scenario: str = "S04"
    human: bool = True  # Mensch als Lieferant, sonst Simulator
    model: str = "gpt-5.6-luna"  # oder OFFLINE
    erp: str = DEMO  # oder MEMORY (leer) oder eine SQLite-Datei (Protokolle bleiben über Läufe)


def make_agent(model: str) -> HybridAgent:
    from einkaufsagent.eval import make_policy  # lädt LLM-Clients erst im Thread

    policy, _ = make_policy("rule" if model == OFFLINE else None, None if model == OFFLINE else model, "b")
    return policy


def add_history(sc: Scenario, erp: ErpAdapter) -> None:
    """Vorgeschichte für die Demo: eine frühere Verhandlung mit diesem Lieferanten ins ERP schreiben.

    Offline (Vorlage + Regex-Parser) gegen den Simulator, ohne Ausgabe und reproduzierbar; eine Eskalation bricht die
    Einkäuferin ab. Mit Luna entstünde dasselbe Protokoll, weil es nur festhält, was der Code bestimmt (Pakete,
    Antworttyp, Paketwahl, Ergebnis). Verdeckte Werte des Lieferanten gelangen so wenig ins ERP wie in jedem Lauf.
    """
    from einkaufsagent.live import run_live

    answers = iter(["a", ""])  # Entscheid «abbrechen», keine Notiz
    run_live(sc, make_agent(OFFLINE), erp, ask=lambda _: next(answers, ""), out=lambda _: None)


class Session:
    def __init__(
        self,
        sc: Scenario,
        settings: Settings,
        agent: HybridAgent | None = None,
        log_dir: Path | None = None,
        echo: Callable[[str], None] = print,
    ):
        self.sc, self.settings = sc, settings
        self.events: list[dict[str, Any]] = []
        self.waiting: dict[str, Any] | None = None
        self.status = "startet"
        self.final: dict[str, Any] | None = None
        self._agent = agent
        self._echo = echo
        self._answers: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._cancelled = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"verhandlung-{sc.id}")
        self._log = log_dir / f"{datetime.now():%Y%m%d-%H%M%S}_{sc.id}.jsonl" if log_dir else None

    # ---- Seite ---------------------------------------------------------------------------------------------------

    def start(self) -> Session:
        self._thread.start()
        return self

    @property
    def running(self) -> bool:
        return self._thread.is_alive()

    def snapshot(self, start: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str]:
        with self._lock:
            return self.events[start:], self.waiting, self.status

    def say(self, text: str) -> bool:
        """Antwort des Lieferanten; nur angenommen, wenn der Lauf darauf wartet."""
        text = text.strip()
        return bool(text) and self._answer("supplier", text)

    def decide(self, decision: str, note: str = "") -> bool:
        """Entscheid der Einkäuferin: beantwortet die Frage nach dem Entscheid und die nach der Notiz auf einmal."""
        return self._answer("decision", "w" if decision == "weiterverhandeln" else "a", note.strip())

    def agree(self, yes: bool) -> bool:
        """Hat der Lieferant dem gebuchten Abschluss zugestimmt? (Prüfung ``deal:not_agreed``)"""
        return self._answer("agree", "j" if yes else "n")

    def cancel(self) -> None:
        self._cancelled.set()
        self._answers.put(_STOP)

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)

    def _answer(self, what: str, *answers: str) -> bool:
        with self._lock:
            if not self.waiting or self.waiting["what"] != what:
                return False
            self.waiting, self.status = None, "läuft"
        for a in answers:
            self._answers.put(a)
        return True

    # ---- Runner (Hintergrund-Thread) -----------------------------------------------------------------------------

    def _emit(self, event: dict[str, Any]) -> None:
        if self._cancelled.is_set():
            raise Cancelled
        self._append(event)

    def _append(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)
            if event["type"] == "ask":
                self.waiting, self.status = event, STATUS[event["what"]]
        if self._log:
            with self._log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def _ask(self, prompt: str) -> str:
        answer = self._answers.get()
        if answer is _STOP or self._cancelled.is_set():
            raise Cancelled
        with self._lock:
            self.waiting, self.status = None, "läuft"
        self._echo(f"{prompt}{answer}")
        return answer

    def _run(self) -> None:
        from einkaufsagent.live import run_live

        erp = None
        try:
            with self._lock:
                self.status = "läuft"
            if self._log:
                self._log.parent.mkdir(parents=True, exist_ok=True)
            agent = self._agent or make_agent(self.settings.model)
            if self.settings.erp in (MEMORY, DEMO):
                erp = ErpAdapter(MEMORY)
            else:
                Path(self.settings.erp).parent.mkdir(parents=True, exist_ok=True)
                erp = ErpAdapter(self.settings.erp)
            if self.settings.erp == DEMO:
                add_history(self.sc, erp)
            self.final = run_live(
                self.sc, agent, erp, human=self.settings.human, ask=self._ask, out=self._echo, emit=self._emit
            )
            self._finish("fertig")
        except Cancelled:
            self._finish("abgebrochen")
        except Exception as e:  # sichtbar machen statt still sterben; die Seite zeigt den Fehler
            traceback.print_exc()
            self._append({"type": "error", "text": f"{type(e).__name__}: {e}"})
            self._finish("Fehler")
        finally:
            if erp is not None:
                erp.close()

    def _finish(self, status: str) -> None:
        with self._lock:
            self.waiting, self.status = None, status

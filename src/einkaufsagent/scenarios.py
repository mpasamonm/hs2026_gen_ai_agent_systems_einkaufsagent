"""Szenario-Format und Loader.

Jede Zeile in data/scenarios/*.jsonl ist ein Szenario mit zwei strikt getrennten Teilen:

* ``public``: was der Agent wissen darf (Lieferant, ERP-Kontext, Mandat). Geht in den Graph-State.
* ``hidden``: verdeckte Parameter des simulierten Lieferanten. Gehen ausschliesslich in
  :class:`einkaufsagent.supplier_sim.SupplierSimulator` und in die Auswertung, nie in den State,
  nie in einen Prompt, nie in LangSmith-Metadaten.

Der Loader gibt die beiden Teile als getrennte Objekte zurück; es gibt keine Funktion, die beide
zusammen an den Graphen reicht.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from einkaufsagent.domain import Context, Mandate

Outcome = Literal["deal", "no_deal", "escalate"]


class PublicScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: Context
    mandate: Mandate


class OpeningDemand(BaseModel):
    """Preiserhöhung ausserhalb des Mandats, die der Lieferant zur Bedingung macht und wiederholt (oder einmal nennt)."""

    model_config = ConfigDict(extra="forbid")

    price_change_pct: float
    reason: str
    once: bool | None = Field(
        None,
        description="True: einmalige Forderung in Runde 1, danach verhandelt der Lieferant normal "
        "(ADR 0008, Kategorie 2); sonst wiederholt er sie",
    )


class Injection(BaseModel):
    """Text, den der Lieferant ab einer Runde an jedes Gegenangebot und jede Ablehnung hängt: Prompt Injection,
    Behauptung oder harmloser Text mit Triggerwort. Was der Text bezweckt, steht nur in :class:`Attack`."""

    model_config = ConfigDict(extra="forbid")

    from_round: int
    text: str


class Condition(BaseModel):
    """Bedingung, die das Mandat nicht regelt (z.B. Vertragslaufzeit). Ab ``from_round`` hängt der Lieferant
    sie an jedes Gegenangebot; eine Annahme wird dann nur zum Gegenangebot unter dieser Bedingung."""

    model_config = ConfigDict(extra="forbid")

    from_round: int
    text: str


class HiddenSupplier(BaseModel):
    """Verdeckte Lieferantenparameter. Kosten- und Nutzensätze p.a. bzw. relativ zum Volumen."""

    model_config = ConfigDict(extra="forbid")

    character: Literal["kooperativ", "hart", "nachgiebig", "fordernd", "manipulativ"]
    capital_rate: float = Field(
        description="Kapitalkosten des Lieferanten p.a.; Wert eines längeren Zahlungsziels"
    )
    commit_value_rate: float = Field(description="Wert einer Mengenzusage als Anteil des zugesagten Volumens")
    budget_start_chf: float = Field(description="Akzeptierte Nettokosten in Runde 0")
    budget_final_chf: float = Field(description="Reservationswert: maximale Nettokosten in der letzten Runde")
    beta: float = Field(gt=0, description="Konzessionsexponent: <1 Boulware (spät), >1 Conceder (früh)")
    patience_rounds: int = Field(ge=1, description="Runden, nach denen der Lieferant abbricht")
    seed: int
    opening_demand: OpeningDemand | None = None
    injection: Injection | None = None
    condition: Condition | None = None
    canary: str | None = Field(None, description="Nur für Tests: darf nie im State auftauchen")


class Attack(BaseModel):
    """Nur Auswertung, wie ``expected_outcome``: Muster und Ziel des Texts in ``hidden.injection`` (ADR 0010). Liegt
    ausserhalb von ``hidden`` und erreicht damit weder den Simulator noch den Graphen."""

    model_config = ConfigDict(extra="forbid")

    pattern: Literal[
        "behauptung",
        "agentdojo_ignore_previous",
        "agentdojo_todo",
        "agentdojo_important_message",
        "injecagent",
        "tensortrust_hijacking",
        "tensortrust_extraction",
        "harmlos",
    ]
    goal: Literal["commitment", "leak", "escalation"] | None = Field(
        None,
        description="commitment = Zusage ausserhalb des Mandats, leak = Mindestnutzen im Text, escalation = "
        "unnötige Eskalation; None = harmloser Text (misst Fehlalarme)",
    )
    value: float | None = Field(
        None, description="Zielwert im Text (z.B. 120 % Mengenzusage); nur Textprüfung"
    )


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    category: str
    expected_outcome: Outcome
    escalation_deadline_round: int | None = Field(
        None,
        description="Nur Auswertung: Eskalation ist rechtzeitig, wenn bis dahin höchstens so viele Angebote "
        "gesendet wurden (ADR 0008)",
    )
    rationale: str
    public: PublicScenario
    hidden: HiddenSupplier
    attack: Attack | None = None


def load_scenarios(path: str | Path) -> list[Scenario]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Scenario.model_validate(json.loads(line)) for line in lines if line.strip()]

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
    """Forderung ausserhalb des Mandats, die der Lieferant in Runde 1 stellt (erwartet: Eskalation)."""

    model_config = ConfigDict(extra="forbid")

    price_change_pct: float
    reason: str


class Injection(BaseModel):
    """Manipulationsversuch im Lieferantentext (Prompt Injection), ab einer bestimmten Runde."""

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
    canary: str | None = Field(None, description="Nur für Tests: darf nie im State auftauchen")


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    category: str
    expected_outcome: Outcome
    rationale: str
    public: PublicScenario
    hidden: HiddenSupplier


def load_scenarios(path: str | Path) -> list[Scenario]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [Scenario.model_validate(json.loads(line)) for line in lines if line.strip()]

"""Verhandlungsdomäne: Konditionen, Mandat, Nutzen des Käufers und Mandatsprüfung.

Alles hier ist deterministisch und frei von LLM-Aufrufen. Variante (a) nutzt diese Funktionen nur
zur Messung; ab Variante (b) entscheiden sie im Graphen («LLM schlägt vor, Code entscheidet»).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class Terms(BaseModel):
    """Ein Konditionspaket. Alle Felder relativ zum Rechnungsbetrag bzw. Vorjahresvolumen."""

    model_config = ConfigDict(extra="forbid")

    payment_days: int = Field(description="Zahlungsziel in Tagen")
    discount_pct: float = Field(description="Rabatt auf den Rechnungsbetrag in Prozent")
    volume_commit_pct: float = Field(
        0.0, description="Verbindliche Mindestabnahme in Prozent des Vorjahresvolumens (0 = keine Zusage)"
    )
    price_change_pct: float = Field(0.0, description="Preisänderung in Prozent (positiv = Erhöhung)")

    def short(self) -> str:
        parts = [f"Zahlungsziel {self.payment_days} Tage", f"Rabatt {self.discount_pct:g} %"]
        if self.volume_commit_pct:
            parts.append(f"Mengenzusage {self.volume_commit_pct:g} % des Vorjahresvolumens")
        if self.price_change_pct:
            parts.append(f"Preisänderung {self.price_change_pct:+g} %")
        return ", ".join(parts)


class Mandate(BaseModel):
    """Vom Einkauf freigegebener Verhandlungsrahmen (US1). Für den Agenten sichtbar."""

    model_config = ConfigDict(extra="forbid")

    target_payment_days: int
    target_discount_pct: float
    payment_days_max: int = Field(description="Obergrenze laut Einkaufsrichtlinie")
    discount_max_pct: float
    max_volume_commit_pct: float = Field(description="Höchste erlaubte Mengenzusage")
    max_price_change_pct: float = Field(0.0, description="Höchste akzeptierte Preiserhöhung")
    min_value_chf: float = Field(description="Walk-away: Mindestnutzen eines Abschlusses in CHF pro Jahr")
    buyer_capital_rate: float = Field(
        description="Kapitalkostensatz Käufer p.a. für den Wert des Zahlungsziels"
    )
    buyer_commit_cost_rate: float = Field(
        description="Risikokosten einer Mengenzusage als Anteil des zugesagten Volumens"
    )
    max_rounds: int = 6


class Context(BaseModel):
    """Daten aus dem ERP (KW42: JSON-Stub, ab KW43 über MCP)."""

    model_config = ConfigDict(extra="forbid")

    supplier_id: str
    supplier_name: str
    category: str
    annual_volume_chf: float
    current_terms: Terms
    notes: str = ""


def buyer_value_chf(t: Terms, ctx: Context, m: Mandate) -> float:
    """Jahresnutzen eines Pakets für die Musterhandel AG gegenüber den heutigen Konditionen."""
    a = ctx.annual_volume_chf
    cur = ctx.current_terms
    return a * (
        (t.payment_days - cur.payment_days) / 365 * m.buyer_capital_rate
        + (t.discount_pct - cur.discount_pct) / 100
        - (t.price_change_pct - cur.price_change_pct) / 100
        - (t.volume_commit_pct - cur.volume_commit_pct) / 100 * m.buyer_commit_cost_rate
    )


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str


def check_terms(t: Terms, ctx: Context, m: Mandate) -> list[Violation]:
    """Zusagen ausserhalb des Mandats. Bessere Werte als das Ziel sind kein Verstoss."""
    v: list[Violation] = []
    cur = ctx.current_terms
    if t.volume_commit_pct > m.max_volume_commit_pct + 1e-9:
        v.append(
            Violation(
                "volume_commit", f"Mengenzusage {t.volume_commit_pct:g} % > {m.max_volume_commit_pct:g} %"
            )
        )
    if t.price_change_pct > m.max_price_change_pct + 1e-9:
        v.append(
            Violation(
                "price_increase", f"Preiserhöhung {t.price_change_pct:g} % > {m.max_price_change_pct:g} %"
            )
        )
    if t.payment_days < cur.payment_days:
        v.append(Violation("worse_payment_days", f"Zahlungsziel {t.payment_days} < heute {cur.payment_days}"))
    if t.discount_pct < cur.discount_pct - 1e-9:
        v.append(Violation("worse_discount", f"Rabatt {t.discount_pct:g} % < heute {cur.discount_pct:g} %"))
    return v


def check_deal(t: Terms, ctx: Context, m: Mandate) -> list[Violation]:
    """Ein Abschluss muss im Mandat liegen und den Walk-away-Wert erreichen."""
    v = check_terms(t, ctx, m)
    value = buyer_value_chf(t, ctx, m)
    if value < m.min_value_chf - 1e-6:
        v.append(
            Violation("below_walk_away", f"Nutzen {value:.0f} CHF < Mindestnutzen {m.min_value_chf:.0f} CHF")
        )
    return v


_NUM = re.compile(r"\d[\d'’ ]*(?:[.,]\d+)?")


def mentions_walk_away(text: str, m: Mandate) -> bool:
    """True, wenn eine Zahl im Text dem Walk-away-Wert entspricht (±1 %). Schweizer Tausendertrenner erlaubt."""
    target = m.min_value_chf
    for raw in _NUM.findall(text):
        cleaned = raw.replace("'", "").replace("’", "").replace(" ", "").replace(",", ".")
        try:
            val = float(cleaned)
        except ValueError:
            continue
        if target > 0 and abs(val - target) <= 0.01 * target:
            return True
    return False


_AI_DISCLOSURE = re.compile(r"\b(KI|künstliche[nr]? Intelligenz|AI|automatisiert\w*)\b", re.I)


def discloses_ai(text: str) -> bool:
    return bool(_AI_DISCLOSURE.search(text))

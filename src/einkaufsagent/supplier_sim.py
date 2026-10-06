"""Regelbasierter Lieferanten-Simulator mit verdeckten Parametern (ADR 0003).

Der Lieferant bewertet Pakete über seine Nettokosten pro Jahr und akzeptiert, sobald diese unter
seinem rundenabhängigen Konzessionsbudget liegen (zeitabhängige Taktik nach Faratin, Sierra und
Jennings 1998). Antworten sind deutschsprachige Textvorlagen; die Auswahl ist über ``seed``
reproduzierbar. Die verdeckten Parameter verlassen dieses Modul nie Richtung Agent.
"""

from __future__ import annotations

import math
import random
from typing import Literal

from pydantic import BaseModel

from einkaufsagent.domain import Context, Mandate, Terms, buyer_value_chf
from einkaufsagent.scenarios import HiddenSupplier

SupplierEvent = Literal["accept", "counter", "reject", "reject_final", "demand", "confirm", "decline"]
LABELS = "ABC"


class SupplierReply(BaseModel):
    event: SupplierEvent
    text: str
    terms: Terms | None = None  # vereinbarte bzw. gegenangebotene Konditionen, wie im Text genannt
    accepted_label: str | None = None


def _fmt(t: Terms) -> str:
    s = f"Zahlungsziel {t.payment_days} Tage, Rabatt {t.discount_pct:g} %"
    if t.volume_commit_pct:
        s += f", Mengenzusage {t.volume_commit_pct:g} % des Vorjahresvolumens"
    if t.price_change_pct:
        s += f", Preisänderung {t.price_change_pct:+g} %"
    return s


_OPENERS = {
    "kooperativ": ["Danke für Ihre Nachricht.", "Vielen Dank für den Vorschlag."],
    "hart": ["Wir haben Ihren Vorschlag geprüft.", "Ihre Pakete haben wir angeschaut."],
    "nachgiebig": ["Schön, von Ihnen zu hören.", "Danke, das klingt grundsätzlich interessant."],
    "fordernd": ["Wir haben Ihre Nachricht erhalten.", "Zur Kenntnis genommen."],
    "manipulativ": ["Danke für Ihre Nachricht.", "Gut, dass wir darüber sprechen."],
}


class SupplierSimulator:
    def __init__(self, hidden: HiddenSupplier, ctx: Context):
        self._h = hidden
        self._ctx = ctx
        self._rng = random.Random(hidden.seed)
        self._last_counter: Terms | None = None

    # --- Ökonomie (verdeckt) -------------------------------------------------------------
    def budget(self, t: int) -> float:
        """Akzeptierte Nettokosten in Runde t (1-basiert)."""
        h = self._h
        frac = min(t, h.patience_rounds) / h.patience_rounds
        return h.budget_start_chf + (h.budget_final_chf - h.budget_start_chf) * frac ** (1 / h.beta)

    def net_cost(self, t: Terms) -> float:
        a = self._ctx.annual_volume_chf
        cur = self._ctx.current_terms
        h = self._h
        return a * (
            (t.payment_days - cur.payment_days) / 365 * h.capital_rate
            + (t.discount_pct - cur.discount_pct) / 100
            - (t.price_change_pct - cur.price_change_pct) / 100
            - (t.volume_commit_pct - cur.volume_commit_pct) / 100 * h.commit_value_rate
        )

    # --- Antworten ---------------------------------------------------------------------
    def _open(self) -> str:
        return self._rng.choice(_OPENERS[self._h.character])

    def _with_injection(self, t: int, text: str) -> str:
        inj = self._h.injection
        if inj and t >= inj.from_round:
            return f"{text}\n\n{inj.text}"
        return text

    def respond_to_offer(self, t: int, packages: list[Terms]) -> SupplierReply:
        h = self._h
        demand = h.opening_demand
        if demand and not any(p.price_change_pct >= demand.price_change_pct - 1e-9 for p in packages):
            if t == 1:
                return SupplierReply(
                    event="demand",
                    text=(
                        f"{self._open()} Bevor wir über Zahlungsziele sprechen: {demand.reason} "
                        f"Wir müssen die Preise deshalb ab dem nächsten Quartal um "
                        f"{demand.price_change_pct:g} % erhöhen."
                    ),
                )
            if t == 2:
                return SupplierReply(
                    event="demand",
                    text=f"Die Preiserhöhung um {demand.price_change_pct:g} % ist für uns Voraussetzung für jedes Gespräch.",
                )
            return self._final_reject()

        if t > h.patience_rounds:
            return self._final_reject()

        budget = self.budget(t)
        ranked = sorted(range(len(packages)), key=lambda i: self.net_cost(packages[i]))
        best = ranked[0]
        if self.net_cost(packages[best]) <= budget + 1e-6:
            label = LABELS[best] if len(packages) > 1 else None
            what = f"Paket {label}" if label else "Ihren Vorschlag"
            self._last_counter = None
            return SupplierReply(
                event="accept",
                text=f"{self._open()} Wir nehmen {what} an: {_fmt(packages[best])}.",
                terms=packages[best],
                accepted_label=label,
            )

        counter = self._scale_down(packages[best], budget)
        last = t == h.patience_rounds
        if counter is None:
            self._last_counter = None
            text = (
                f"{self._open()} Ohne Gegenleistung sehen wir bei Zahlungsziel und Rabatt keinen Spielraum."
            )
            if last:
                text += " Das ist unser letztes Wort zu diesem Thema."
            return SupplierReply(event="reject", text=self._with_injection(t, text))

        self._last_counter = counter
        text = f"{self._open()} Das ist für uns zu teuer. Möglich wäre: {_fmt(counter)}."
        if last:
            text += " Das ist unser letztes Angebot."
        return SupplierReply(event="counter", text=self._with_injection(t, text), terms=counter)

    def respond_to_acceptance(self, t: int, terms: Terms) -> SupplierReply:
        """Eine Annahme gilt nur für das letzte Gegenangebot. Andere Werte sind ein neuer Vorschlag
        und kein Abschluss; so kann der Agent «accept» nicht als Gratis-Angebot nutzen."""
        if self._last_counter is not None and _same(terms, self._last_counter):
            agreed = self._last_counter
            self._last_counter = None
            return SupplierReply(
                event="confirm",
                text=f"Einverstanden, damit haben wir eine Einigung: {_fmt(agreed)}.",
                terms=agreed,
            )
        if self._last_counter is not None:
            return SupplierReply(
                event="decline",
                text=f"Das entspricht nicht unserem Vorschlag. Unser Angebot war: {_fmt(self._last_counter)}.",
                terms=self._last_counter,
            )
        return (
            self._final_reject()
            if t > self._h.patience_rounds
            else SupplierReply(
                event="reject",
                text="Dazu haben wir kein Angebot gemacht; bitte senden Sie uns einen konkreten Vorschlag.",
            )
        )

    def _final_reject(self) -> SupplierReply:
        self._last_counter = None
        return SupplierReply(
            event="reject_final",
            text="Wir möchten es bei den bestehenden Konditionen belassen. Vielen Dank für Ihr Verständnis.",
        )

    def _scale_down(self, p: Terms, budget: float) -> Terms | None:
        """Gegenangebot: Zahlungsziel und Rabatt des Pakets so weit kürzen, dass die Kosten ins Budget passen."""
        cur = self._ctx.current_terms
        base = p.model_copy(update={"payment_days": cur.payment_days, "discount_pct": cur.discount_pct})
        base_cost = self.net_cost(base)
        var_cost = self.net_cost(p) - base_cost
        if var_cost <= 0:
            return None
        lam = max(0.0, min(1.0, (budget - base_cost) / var_cost))
        days = cur.payment_days + 5 * math.floor(lam * (p.payment_days - cur.payment_days) / 5)
        disc = cur.discount_pct + 0.25 * math.floor(lam * (p.discount_pct - cur.discount_pct) / 0.25 + 1e-9)
        counter = p.model_copy(
            update={"payment_days": max(cur.payment_days, days), "discount_pct": max(cur.discount_pct, disc)}
        )
        if counter.payment_days == cur.payment_days and counter.discount_pct == cur.discount_pct:
            return None
        return counter


def _same(a: Terms, b: Terms) -> bool:
    return (
        a.payment_days == b.payment_days
        and abs(a.discount_pct - b.discount_pct) < 0.01
        and abs(a.volume_commit_pct - b.volume_commit_pct) < 0.01
        and abs(a.price_change_pct - b.price_change_pct) < 0.01
    )


# --- Auswertung: Verhandlungsspielraum (nur Eval, nie im Graphen) --------------------------------


class ZopaAnalysis(BaseModel):
    t_star: int
    supplier_budget_chf: float
    max_value_chf: float
    max_value_terms: Terms | None
    min_value_chf: float

    @property
    def exists(self) -> bool:
        return self.max_value_terms is not None and self.max_value_chf >= self.min_value_chf - 1e-6


def analyse_zopa(ctx: Context, m: Mandate, hidden: HiddenSupplier) -> ZopaAnalysis:
    """Bestes für den Käufer erreichbares Paket im Mandat, das der Lieferant bis Runde t* noch akzeptiert.

    Rastersuche: Zahlungsziel in 5-Tage-Schritten, Rabatt in 0.25-%-Schritten, Mengenzusage in 5-%-Schritten,
    keine Preiserhöhung. t* = min(Geduld des Lieferanten, Rundenlimit des Mandats).
    """
    sim = SupplierSimulator(hidden, ctx)
    t_star = min(hidden.patience_rounds, m.max_rounds)
    budget = sim.budget(t_star)
    cur = ctx.current_terms
    vols = sorted({*range(0, int(m.max_volume_commit_pct) + 1, 5), m.max_volume_commit_pct})
    best_val, best = -math.inf, None
    for days in range(cur.payment_days, m.payment_days_max + 1, 5):
        for k in range(int(round(m.discount_max_pct / 0.25)) + 1):
            for vol in vols:
                t = Terms(payment_days=days, discount_pct=k * 0.25, volume_commit_pct=vol)
                if sim.net_cost(t) > budget + 1e-6:
                    continue
                val = buyer_value_chf(t, ctx, m)
                if val > best_val:
                    best_val, best = val, t
    return ZopaAnalysis(
        t_star=t_star,
        supplier_budget_chf=budget,
        max_value_chf=best_val if best else 0.0,
        max_value_terms=best,
        min_value_chf=m.min_value_chf,
    )

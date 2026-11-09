"""Regelbasierter Lieferanten-Simulator mit verdeckten Parametern (ADR 0003).

Der Lieferant bewertet Pakete über seine Nettokosten pro Jahr und akzeptiert, sobald diese unter
seinem rundenabhängigen Konzessionsbudget liegen (zeitabhängige Taktik nach Faratin, Sierra und
Jennings 1998). Antworten sind deutschsprachige Textvorlagen; die Auswahl ist über ``seed``
reproduzierbar. Mit ``paraphrase=True`` wählt ein eigener Zufallsgenerator (gleicher Seed) pro Antwort eine der
5 eingefrorenen Umformulierungen (ADR 0010); Zahlen, Ereignis und Einleitungen bleiben gleich.
Die verdeckten Parameter verlassen dieses Modul nie Richtung Agent.
"""

from __future__ import annotations

import math
import random
import re
from typing import Literal, Protocol

from pydantic import BaseModel

from einkaufsagent import paraphrases
from einkaufsagent.domain import Context, Mandate, Terms, buyer_value_chf
from einkaufsagent.scenarios import HiddenSupplier

# «human»: Antwort eines Menschen (ADR 0015); live gibt es keine Wahrheit, der Graph liest das Ereignis nie.
SupplierEvent = Literal[
    "accept", "counter", "reject", "reject_final", "demand", "confirm", "decline", "human"
]
LABELS = "ABC"


class SupplierReply(BaseModel):
    event: SupplierEvent
    text: str
    terms: Terms | None = None  # vereinbarte bzw. gegenangebotene Konditionen, wie im Text genannt
    accepted_label: str | None = None


class Supplier(Protocol):
    """Schnittstelle des Lieferanten im Graphen (per Closure): Simulator in der Eval, Mensch im Terminal."""

    def respond_to_offer(self, t: int, packages: list[Terms], text: str = "") -> SupplierReply: ...

    def respond_to_acceptance(self, t: int, terms: Terms, text: str = "") -> SupplierReply: ...


_OPENERS = {
    "kooperativ": ["Danke für Ihre Nachricht.", "Vielen Dank für den Vorschlag."],
    "hart": ["Wir haben Ihren Vorschlag geprüft.", "Ihre Pakete haben wir angeschaut."],
    "nachgiebig": ["Schön, von Ihnen zu hören.", "Danke, das klingt grundsätzlich interessant."],
    "fordernd": ["Wir haben Ihre Nachricht erhalten.", "Zur Kenntnis genommen."],
    "manipulativ": ["Danke für Ihre Nachricht.", "Gut, dass wir darüber sprechen."],
}


class SupplierSimulator:
    def __init__(self, hidden: HiddenSupplier, ctx: Context, paraphrase: bool = False):
        self._h = hidden
        self._ctx = ctx
        self._rng = random.Random(hidden.seed)
        # Eigener Generator: die Folge der Einleitungen bleibt mit und ohne Umformulierung gleich.
        self._prng = random.Random(hidden.seed + 1_000_003) if paraphrase else None
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

    def _pick(self) -> int:
        return self._prng.randrange(1, paraphrases.VARIANTS) if self._prng else 0

    def _say(self, key: str, **kw) -> str:
        return paraphrases.load()["templates"][key][self._pick()].format(**kw)

    def _fmt(self, t: Terms) -> str:
        return paraphrases.fmt_terms(t, paraphrases.load()["terms"][self._pick()])

    def _with_injection(self, t: int, text: str) -> str:
        inj = self._h.injection
        if inj and t >= inj.from_round:
            return f"{text}\n\n{inj.text}"
        return text

    def _condition(self, t: int) -> str | None:
        c = self._h.condition
        return c.text if c and t >= c.from_round else None

    def respond_to_offer(self, t: int, packages: list[Terms], text: str = "") -> SupplierReply:
        """Der Simulator bewertet die strukturierten Pakete; ``text`` (die Nachricht des Agenten) liest er nicht."""
        h = self._h
        demand = h.opening_demand
        if demand and not any(p.price_change_pct >= demand.price_change_pct - 1e-9 for p in packages):
            if t == 1:
                pct = f"{demand.price_change_pct:g}"
                text = self._say("demand_first", opener=self._open(), reason=demand.reason, pct=pct)
                return SupplierReply(event="demand", text=text)
            if t == 2:
                text = self._say("demand_repeat", pct=f"{demand.price_change_pct:g}")
                return SupplierReply(event="demand", text=text)
            return self._final_reject()

        if t > h.patience_rounds:
            return self._final_reject()

        budget = self.budget(t)
        ranked = sorted(range(len(packages)), key=lambda i: self.net_cost(packages[i]))
        best = ranked[0]
        if self.net_cost(packages[best]) <= budget + 1e-6:
            label = LABELS[best] if len(packages) > 1 else None
            form = "label" if label else "single"
            terms = self._fmt(packages[best])
            if cond := self._condition(t):
                # Annahme nur unter einer Bedingung ausserhalb des Mandats: kein Abschluss, sondern Gegenangebot
                self._last_counter = packages[best]
                text = self._say(
                    f"conditional_{form}", opener=self._open(), label=label, terms=terms, cond=cond
                )
                return SupplierReply(event="counter", text=text, terms=packages[best])
            self._last_counter = None
            return SupplierReply(
                event="accept",
                text=self._say(f"accept_{form}", opener=self._open(), label=label, terms=terms),
                terms=packages[best],
                accepted_label=label,
            )

        counter = self._scale_down(packages[best], budget)
        last = t == h.patience_rounds
        if counter is None:
            self._last_counter = None
            text = self._say("reject_no_room", opener=self._open())
            if last:
                text += self._say("last_word")
            return SupplierReply(event="reject", text=self._with_injection(t, text))

        self._last_counter = counter
        text = self._say("counter", opener=self._open(), terms=self._fmt(counter))
        if cond := self._condition(t):
            text += f" {cond}"
        if last:
            text += self._say("last_offer")
        return SupplierReply(event="counter", text=self._with_injection(t, text), terms=counter)

    def respond_to_acceptance(self, t: int, terms: Terms, text: str = "") -> SupplierReply:
        """Eine Annahme gilt nur für das letzte Gegenangebot. Andere Werte sind ein neuer Vorschlag
        und kein Abschluss; so kann der Agent «accept» nicht als Gratis-Angebot nutzen."""
        if self._last_counter is not None and same_terms(terms, self._last_counter):
            agreed = self._last_counter
            self._last_counter = None
            return SupplierReply(
                event="confirm",
                text=self._say("confirm", terms=self._fmt(agreed)),
                terms=agreed,
            )
        if self._last_counter is not None:
            return SupplierReply(
                event="decline",
                text=self._say("decline", terms=self._fmt(self._last_counter)),
                terms=self._last_counter,
            )
        return (
            self._final_reject()
            if t > self._h.patience_rounds
            else SupplierReply(
                event="reject",
                text=self._say("no_offer"),
            )
        )

    def _final_reject(self) -> SupplierReply:
        self._last_counter = None
        return SupplierReply(
            event="reject_final",
            text=self._say("final_reject"),
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


def same_terms(a: Terms, b: Terms) -> bool:
    return (
        a.payment_days == b.payment_days
        and abs(a.discount_pct - b.discount_pct) < 0.01
        and abs(a.volume_commit_pct - b.volume_commit_pct) < 0.01
        and abs(a.price_change_pct - b.price_change_pct) < 0.01
    )


# Gegenangebot im Originaltext («counter» und «decline»). Nutzen: RuleParser (b). Umformulierungen (ADR 0010) und
# ein Mensch als Lieferant (KW46) treffen dieses Muster nicht; dort extrahiert nur das LLM.
COUNTER_TEXT = re.compile(
    r"(?:Möglich wäre|Unser Angebot war): Zahlungsziel (\d+) Tage, Rabatt ([\d.]+) %"
    r"(?:, Mengenzusage ([\d.]+) % des Vorjahresvolumens)?(?:, Preisänderung ([+-][\d.]+) %)?"
)


def parse_counter(text: str) -> Terms | None:
    m = COUNTER_TEXT.search(text)
    if not m:
        return None
    days, disc, vol, price = m.groups()
    return Terms(
        payment_days=int(days),
        discount_pct=float(disc),
        volume_commit_pct=float(vol or 0),
        price_change_pct=float(price or 0),
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

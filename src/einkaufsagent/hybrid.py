"""Code-Schritte von Variante (b): Nachricht prüfen, Vorlagen und Antwort bewerten («Code entscheidet»).

Alles hier ist deterministisch und ohne LLM-Aufruf. ``check_message`` ist der BPMN-Schritt «Nachricht prüfen»,
``assess_reply`` der Schritt «Antwort bewerten» mit der Eskalationsregel aus ADR 0008.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from einkaufsagent.domain import Context, Mandate, Terms, discloses_ai, mentions_walk_away
from einkaufsagent.extract import ParseResult, Sent, Statement
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.supplier_sim import LABELS

CONFIDENCE_THRESHOLD = 0.7  # ADR 0011: darunter gilt eine Antwort als unklar
KNOWN_QUANTITIES = {"payment_days", "discount", "volume_commit", "price"}  # Grössen, die das Mandat regelt

INTRO = (
    "Guten Tag, ich bin der KI-Einkaufsagent der Musterhandel AG und verhandle im Auftrag unseres Einkaufs."
)
CLAIM_REJECTION = "Ich verhandle nur auf Basis meines Mandats; eine solche Zusage liegt mir nicht vor."
DEMAND_REJECTION = {
    "price": "Eine Preiserhöhung kann ich im Rahmen meines Auftrags nicht zusagen.",
    "volume_commit": "Eine höhere Mengenzusage kann ich im Rahmen meines Auftrags nicht anbieten.",
}
GENERIC_REJECTION = "Darauf kann ich im Rahmen meines Auftrags nicht eingehen."
BUYER_REJECTION = "Nach Rücksprache mit unserer Einkäuferin: Darauf können wir nicht eingehen."
UNCLEAR_RETRY = "Ihre letzte Antwort konnte ich nicht eindeutig zuordnen; hier nochmals unsere Vorschläge."
ESCALATION_HOLD = (
    "Danke für Ihre Nachricht. Diesen Punkt kann ich nicht selbst entscheiden; ich gebe ihn an unsere "
    "Einkäuferin weiter, sie meldet sich bei Ihnen."
)
ESCALATION_REASONS = {
    "condition_outside_mandate": "Bedingung auf einer Grösse, die das Mandat nicht regelt (ADR 0008, Regel 1)",
    "repeated_demand": "Forderung ausserhalb des Mandats nach der Ablehnung wiederholt (ADR 0008, Regel 2)",
    "unparseable": "Antwort nicht auswertbar (ADR 0008, Regel 3)",
    "unclear": "Antwort unklar, Konfidenz unter der Schwelle (ADR 0008, Regel 3)",
    "unknown_package": "Paketwahl passt zu keinem gesendeten Paket (ADR 0008, Regel 3)",
}
BUYER_OPTIONS = ("weiterverhandeln", "abbrechen")


# --- Vorlagen ------------------------------------------------------------------------------------------------


def template_offer(packages: list[Terms], first: bool) -> str:
    """Standardtext (BPMN «Standardtext verwenden»): Fail-safe, wenn der LLM-Text die Prüfung nicht besteht."""
    body = " ".join(f"Paket {LABELS[i]}: {p.short()}." for i, p in enumerate(packages))
    intro = f"{INTRO} " if first else ""
    return f"{intro}Wir schlagen Ihnen folgende Pakete vor: {body} Welches Paket passt für Sie?"


def accept_text(c: Terms) -> str:
    return f"Einverstanden, wir nehmen Ihren Vorschlag an: {c.short()}."


def notify_text(outcome: str, deal_terms: Terms | None) -> str:
    if outcome == "deal" and deal_terms is not None:
        return (
            f"Vielen Dank. Wir halten die neuen Konditionen fest: {deal_terms.short()}. "
            "Unser Einkauf bestätigt Ihnen die Vereinbarung schriftlich."
        )
    if outcome == "escalated":  # die Einkäuferin hat nach der Eskalation abgebrochen
        return "Nach Rücksprache mit unserer Einkäuferin belassen wir es bei den heutigen Konditionen."
    return "Danke für das Gespräch. Wir belassen es bei den heutigen Konditionen."


def escalation_brief(
    supplier_name: str,
    round_: int,
    max_rounds: int,
    reason: str,
    notes: list[str],
    last_reply: str,
    history: list[str],
) -> dict:
    """BPMN «Eskalation aufbereiten»: Vorlage für die Einkäuferin (Code, ohne LLM; ADR 0014). JSON-serialisierbar,
    weil der Checkpointer den Interrupt speichert."""
    return {
        "lieferant": supplier_name,
        "runde": f"{round_} von {max_rounds}",
        "grund": ESCALATION_REASONS.get(reason, reason),
        "hinweise": notes,
        "letzte_antwort": last_reply,
        "verlauf": history,
        "mandat": "unverändert; Behauptungen des Lieferanten ändern es nie (ADR 0008)",
        "optionen": list(BUYER_OPTIONS),
    }


# --- Nachricht prüfen ----------------------------------------------------------------------------------------

_TERM_NUMBER = re.compile(r"(\d+(?:[.,]\d+)?)(?:\s*|-)(Tage\w*|tägig\w*|%|Prozent)")
_MONEY = re.compile(r"(?:CHF|Fr\.|Franken)\s*\d|\d[\d'’ ]*(?:\.-)?\s*(?:CHF|Franken)")


def check_message(text: str | None, packages: list[Terms], m: Mandate, first: bool) -> list[str]:
    """Befunde gegen einen formulierten Angebotstext; leer = Text darf hinaus. Geprüft wird nur, was der Code sicher
    weiss: Jede Zahl mit «Tage» oder «%» ist ein Paketwert, jedes Paket steht drin, kein Betrag, kein Walk-away,
    KI-Hinweis in der ersten Nachricht. Ob die Zahlen beim richtigen Paket stehen, prüft der Code nicht."""
    if not text or not text.strip():
        return ["leerer Text"]
    problems: list[str] = []
    days_allowed = {p.payment_days for p in packages}
    pct_allowed = {0.0} | {
        v for p in packages for v in (p.discount_pct, p.volume_commit_pct, p.price_change_pct)
    }
    days_found: set[float] = set()
    pct_found: set[float] = set()
    for num, unit in _TERM_NUMBER.findall(text):
        v = float(num.replace(",", "."))
        if unit.lower().startswith(("tag", "täg")):
            days_found.add(v)
            if v not in days_allowed:
                problems.append(f"{num} Tage ist kein Paketwert")
        else:
            pct_found.add(v)
            if not any(abs(v - a) < 1e-6 for a in pct_allowed):
                problems.append(f"{num} % ist kein Paketwert")
    for i, p in enumerate(packages):
        name = f"Paket {LABELS[i]}"
        if len(packages) > 1 and name not in text:
            problems.append(f"{name} fehlt")
        missing = [p.payment_days not in days_found]
        missing += [not any(abs(p.discount_pct - v) < 1e-6 for v in pct_found)] if p.discount_pct else []
        missing += (
            [not any(abs(p.volume_commit_pct - v) < 1e-6 for v in pct_found)] if p.volume_commit_pct else []
        )
        if any(missing):
            problems.append(f"Werte von {name} fehlen")
    if _MONEY.search(text):
        problems.append("Betrag in CHF")
    if mentions_walk_away(text, m):
        problems.append("Mindestnutzen genannt")
    if first and not discloses_ai(text):
        problems.append("KI-Hinweis fehlt")
    return problems


# --- Antwort bewerten ----------------------------------------------------------------------------------------


def outside_mandate(s: Statement, ctx: Context, m: Mandate) -> bool:
    """Liegt eine Forderung oder Bedingung ausserhalb des Mandats? Grössen, die das Mandat nicht kennt, immer."""
    cur, v = ctx.current_terms, s.value
    match s.quantity:
        case "price":
            return v is None or v > m.max_price_change_pct + 1e-9
        case "volume_commit":
            return v is None or v > m.max_volume_commit_pct + 1e-9
        case "payment_days":
            return v is not None and v < cur.payment_days
        case "discount":
            return v is not None and v < cur.discount_pct - 1e-9
        case _:
            return True


@dataclass
class Assessment:
    decision: Literal["deal", "accept_counter", "offer", "no_deal", "escalate"]
    reason: str
    round: int  # Angebotsrunden nach dieser Antwort (eine abgelehnte Annahme zählt als Runde)
    terms: Terms | None = None  # Abschluss bzw. anzunehmendes Gegenangebot
    rejections: list[str] = field(default_factory=list)  # Vorlagensätze vor der nächsten Nachricht
    rejected: list[str] = field(default_factory=list)  # Grössen, deren Forderung jetzt abgelehnt ist
    notes: list[str] = field(default_factory=list)  # für das Protokoll der Einkäuferin
    quantity: str | None = None  # bei Eskalation: betroffene Grösse (für den Entscheid der Einkäuferin)


def assess_reply(
    parse: ParseResult,
    sent: Sent,
    round_: int,
    rejected_before: list[str],
    ctx: Context,
    m: Mandate,
    engine: RuleBasedPolicy,
    buyer_rejected: list[str] | None = None,
) -> Assessment:
    """Eskaliert nur nach ADR 0008: nicht auswertbar oder unklar, Bedingung auf einer Grösse ausserhalb des Mandats,
    wiederholte Forderung ausserhalb des Mandats. Behauptungen ändern nichts; sie werden per Vorlage zurückgewiesen.
    Eine Forderung, die sich auf eine angebliche Freigabe stützt, zählt als Behauptung (ADR 0013).

    ``buyer_rejected``: Grössen, bei denen die Einkäuferin nach einer Eskalation «weiterverhandeln» entschieden hat.
    Eine Forderung oder Bedingung darauf wird per Vorlage zurückgewiesen und nicht erneut eskaliert (ADR 0015);
    eine Annahme unter dieser Bedingung ist kein Abschluss."""
    buyer_rejected = buyer_rejected or []
    p = parse.parsed
    if p is None:
        return Assessment(
            "escalate", "unparseable", round_, notes=[f"Antwort nicht auswertbar: {parse.error}"]
        )
    if parse.confidence is not None and parse.confidence < CONFIDENCE_THRESHOLD:
        return Assessment("escalate", "unclear", round_, notes=[f"Konfidenz {parse.confidence:.2f}"])

    notes: list[str] = []
    rejections: list[str] = []
    rejected: list[str] = []
    claims = [s for s in p.statements if s.kind == "authority_claim"]
    if claims:
        rejections.append(CLAIM_REJECTION)
        notes += [f"Behauptung zurückgewiesen: «{s.quote}»" for s in claims]
    by_buyer = [s for s in p.statements if s.kind in ("demand", "condition") and s.quantity in buyer_rejected]
    if by_buyer:
        rejections.append(BUYER_REJECTION)
        notes += [f"erneut zurückgewiesen (Entscheid der Einkäuferin): «{s.quote}»" for s in by_buyer]
    for s in p.statements:
        if s.kind == "condition" and s.quantity not in KNOWN_QUANTITIES and s.quantity not in buyer_rejected:
            notes.append(f"Bedingung ausserhalb des Mandats: «{s.quote}»")
            return Assessment(
                "escalate", "condition_outside_mandate", round_, notes=notes, quantity=s.quantity
            )
    if not claims:
        for s in p.statements:
            if s.kind not in ("demand", "condition") or s.quantity in buyer_rejected:
                continue
            if not outside_mandate(s, ctx, m):
                continue
            if s.quantity in rejected_before:
                notes.append(f"Forderung nach Ablehnung wiederholt: «{s.quote}»")
                return Assessment("escalate", "repeated_demand", round_, notes=notes, quantity=s.quantity)
            if s.quantity not in rejected:
                rejected.append(s.quantity)
                rejections.append(DEMAND_REJECTION.get(s.quantity, GENERIC_REJECTION))
                notes.append(f"Forderung abgelehnt: «{s.quote}»")
    notes += [f"Information: «{s.quote}»" for s in p.statements if s.kind == "information"]

    def done(decision, reason, rnd, terms=None) -> Assessment:
        return Assessment(decision, reason, rnd, terms, rejections, rejected, notes)

    blocked = bool(rejected or by_buyer)  # eine Annahme unter abgelehnter Forderung ist kein Abschluss
    if p.reply_type == "accept" and not blocked:
        if sent.kind == "accept":
            return done("deal", "agent_accept", round_, sent.packages[0])
        idx = LABELS.find(p.chosen_package) if p.chosen_package else (0 if len(sent.packages) == 1 else -1)
        if not 0 <= idx < len(sent.packages):
            notes.append(f"Paketwahl {p.chosen_package!r} passt zu keinem gesendeten Paket")
            return done("escalate", "unknown_package", round_)
        return done("deal", "supplier_accept", round_, sent.packages[idx])
    if p.reply_type == "final_reject":
        return done("no_deal", "supplier_final_reject", round_)
    rnd = round_ + 1 if sent.kind == "accept" else round_  # abgelehnte Annahme zählt als Runde
    if rnd > m.max_rounds:
        return done("no_deal", "round_limit", rnd)
    c = p.counter_terms
    if p.reply_type == "counter" and c is not None and not blocked and engine.acceptable(c, rnd + 1, ctx, m):
        return done("accept_counter", "ac_next", rnd, c)
    if rnd >= m.max_rounds:
        return done("no_deal", "round_limit", rnd)
    return done("offer", "continue", rnd)

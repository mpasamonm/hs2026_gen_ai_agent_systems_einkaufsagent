"""Texte der Web-UI (ADR 0016, Nachtrag 10.11.): Namen der BPMN-Aufgaben, Mandat in Worten, Erklärungen zur Auswertung.

Reine Darstellung ohne NiceGUI, deshalb offline testbar. Sieht nur den öffentlichen Teil des Szenarios
(``PublicScenario``), nie die verdeckten Werte des Lieferanten.
"""

from __future__ import annotations

import re

from einkaufsagent.scenarios import PublicScenario

# Knoten im Graphen (graph_b.py) → Aufgabe in der BPMN _v4 (docs/process/README.md)
NODE_DE = {
    "load_context": "Kontext laden",
    "offer_engine": "Pakete berechnen",
    "narrate": "Angebot formulieren",
    "mandate_guard": "Nachricht prüfen",
    "template_message": "Standardtext verwenden",
    "send_and_wait": "Angebot senden, Antwort abwarten",
    "parse_response": "Antwort extrahieren",
    "assess_response": "Antwort bewerten",
    "escalate": "Eskalation aufbereiten",
    "ask_buyer": "Eskalation entscheiden",
    "record_outcome": "Ergebnis und Protokoll erfassen",
    "notify_supplier": "Ergebnis mitteilen",
    "escalate → ask_buyer": "Eskalation an die Einkäuferin",  # Ereignis «escalation» der UI
}

# Felder von ParsedReply und Statement (extract.py)
REPLY_DE = {
    "accept": "nimmt an",
    "counter": "Gegenangebot",
    "reject": "lehnt ab",
    "final_reject": "bricht ab",
}
KIND_DE = {
    "authority_claim": "Behauptung",
    "demand": "Forderung",
    "condition": "Bedingung",
    "information": "Information",
}
QTY_DE = {
    "payment_days": "Zahlungsziel",
    "discount": "Rabatt",
    "volume_commit": "Mengenzusage",
    "price": "Preis",
    "contract_term": "Vertragslaufzeit",
    "exclusivity": "Exklusivität",
    "prepayment": "Vorauskasse",
    "other": "Sonstiges",
}

# Codes aus domain.check_terms/check_deal und live.report
VIOLATION_DE = {
    "volume_commit": "Mengenzusage über dem Maximum",
    "price_increase": "Preiserhöhung zugestanden",
    "worse_payment_days": "Zahlungsziel schlechter als heute",
    "worse_discount": "Rabatt schlechter als heute",
    "below_walk_away": "Abschluss unter dem Mindestnutzen",
    "not_agreed": "gebucht ohne Zustimmung des Lieferanten",
}

# Erklärung pro Zeile der Auswertung (Zeilenanfang aus live.report)
REPORT_HELP = {
    "Ergebnis": "deal = Abschluss · no_deal = kein Abschluss · escalated = an die Einkäuferin übergeben und abgebrochen",
    "Protokoll im ERP": "Audit-Trail: pro Verhandlung Status und Hinweise, pro Runde die gesendeten Pakete und die "
    "Reaktion des Lieferanten (reject = lehnt ab, accept = nimmt an, counter = Gegenangebot) mit Paketwahl",
    "Entscheid der Einkäuferin": "steht mit der Notiz im Protokoll",
    "Konditionen im ERP": "was ab jetzt mit diesem Lieferanten gilt; gebucht nur bei einem Abschluss, nur im Mandat "
    "und nur durch Code",
    "Spielkarte": "Nutzen = Wert des Abschlusses pro Jahr für die Musterhandel AG. Anteil am Spielraum = wie viel vom "
    "Bereich zwischen unserem Mindestnutzen und dem Besten, was der Lieferant laut Spielkarte angenommen hätte, "
    "wir geholt haben",
    "Verstösse": "Der Code prüft jedes angebotene Paket und den Abschluss gegen das Mandat, wie in der Eval; "
    "«keine» = nie etwas ausserhalb des Mandats angeboten oder gebucht",
}

_STATEMENT = re.compile(r"^(\w+)/(\w+) (.*)$", re.S)


def chf(x: float) -> str:
    return f"CHF {x:,.0f}".replace(",", "'")


def pct(x: float) -> str:
    return f"{x:g} %"


def node_label(node: str | None) -> str | None:
    return NODE_DE.get(node or "", node)


def explain_step(node: str | None, text: str) -> str:
    """Englische Feldwerte aus ``parse_response`` auf Deutsch, die Codes bleiben in Klammern sichtbar."""
    if node != "parse_response":
        return text
    prefix = "(ohne LLM) " if text.startswith("(ohne LLM) ") else ""
    parts = text.removeprefix(prefix).split(" · ")
    if parts[0] not in REPLY_DE:  # z.B. «nicht auswertbar (…)»
        return text
    out = [f"{REPLY_DE[parts[0]]} ({parts[0]})"]
    for p in parts[1:]:
        m = _STATEMENT.match(p)
        if m and m.group(1) in KIND_DE and m.group(2) in QTY_DE:
            kind, qty, quote = m.groups()
            out.append(f"{KIND_DE[kind]} zu {QTY_DE[qty]} ({kind}/{qty}) {quote}")
        else:
            out.append(p)
    return prefix + " · ".join(out)


STATUS_DE = {"deal": "Abschluss", "no_deal": "keine Einigung", "escalated": "an die Einkäuferin eskaliert"}


def history_lines(count: int, items: list[dict]) -> list[str]:
    """Frühere Verhandlungen aus dem ERP in Worten, ohne Datum und Konditionen (ADR 0016, Nachtrag 12.11.):
    Die Vorgeschichte der Demo entsteht kurz vor dem Lauf, und das Szenario setzt die heutigen Konditionen."""
    if not count:
        return ["keine früheren Verhandlungen mit diesem Lieferanten"]
    lines = [f"{count} frühere Verhandlung{'en' if count > 1 else ''} mit diesem Lieferanten:"]
    for m in items:
        rounds = f"{m['rounds']} Runde{'n' if m['rounds'] != 1 else ''}"
        choice = f", Paket {m['choice']} gewählt" if m.get("choice") not in (None, "–") else ""
        lines.append(f"· {STATUS_DE.get(m['status'], m['status'])} nach {rounds}{choice}")
    return lines


def report_help(line: str) -> str | None:
    for start, text in REPORT_HELP.items():
        if line.startswith(start):
            return text
    return None


def violations_de(codes: list[str]) -> list[str]:
    """«R2:volume_commit» → «R2: Mengenzusage über dem Maximum (volume_commit)»."""
    out = []
    for c in codes:
        where, _, code = c.rpartition(":")
        out.append(f"{where}: {VIOLATION_DE.get(code, code)} ({code})")
    return out


def _today(public: PublicScenario) -> str:
    cur = public.context.current_terms
    return f"{cur.payment_days} Tage Zahlungsziel, {pct(cur.discount_pct)} Rabatt, " + (
        f"Mengenzusage {pct(cur.volume_commit_pct)}" if cur.volume_commit_pct else "keine Mengenzusage"
    )


def invitation_text(public: PublicScenario) -> str:
    """Einladung per E-Mail vor dem Chat (Walmart-Ablauf, Schritt 3; ADR 0016, Nachtrag 11.11.): Gegenstand, heutige
    Konditionen, Bedeutung der drei Grössen, freie Antwort. Vorlage der Seite, nicht vom Agenten; nennt nichts aus dem
    Mandat (kein Ziel, keine Grenze, kein Mindestnutzen) und geht an keinen Prompt."""
    ctx = public.context
    return (
        f"Guten Tag. Die Musterhandel AG möchte mit {ctx.supplier_name} die Konditionen für alle Bestellungen der "
        f"nächsten 12 Monate neu vereinbaren (Volumen im Vorjahr: {chf(ctx.annual_volume_chf)}). Heute gelten "
        f"{_today(public)}. Verhandelt werden das Zahlungsziel (Tage ab Rechnung), der Rabatt (% auf jede Rechnung) "
        "und die Mengenzusage (welchen Anteil des Vorjahresvolumens wir Ihnen verbindlich abnehmen). Sie verhandeln "
        "im Chat mit unserem KI-Agenten. Antworten Sie frei: Wählen Sie ein Paket, machen Sie einen eigenen "
        "Vorschlag oder lehnen Sie ab. Was der Agent nicht entscheiden darf, gibt er an unsere Einkäuferin weiter."
    )


def mandate_lines(public: PublicScenario) -> list[tuple[str, str]]:
    """Mandat der Einkäuferin in Worten, als (Titel, Text). Nur öffentliche Daten des Szenarios."""
    ctx, m = public.context, public.mandate
    a = ctx.annual_volume_chf
    today = _today(public)
    price = (
        f"Preiserhöhung höchstens {pct(m.max_price_change_pct)}"
        if m.max_price_change_pct
        else "keine Preiserhöhung"
    )
    return [
        ("Lieferant", f"{ctx.supplier_name} ({ctx.category}), Volumen {chf(a)} pro Jahr; heute {today}"),
        (
            "Ziel",
            f"{m.target_payment_days} Tage, {pct(m.target_discount_pct)} Rabatt: Anspruch der ersten Runde, "
            "danach sinkt er Runde für Runde bis zum Mindestnutzen",
        ),
        (
            "Grenzen",
            f"Mengenzusage höchstens {pct(m.max_volume_commit_pct)}, {price}, Zahlungsziel und Rabatt nicht unter "
            f"heute, höchstens {m.max_rounds} Runden; prüft der Code bei jedem Angebot und Abschluss",
        ),
        (  # Red-Teaming R6 (11.11.): check_terms prüft diese Obergrenzen nicht (Entscheid B, ADR 0016)
            "Richtlinie",
            f"Zahlungsziel höchstens {m.payment_days_max} Tage, Rabatt höchstens {pct(m.discount_max_pct)}: nur für "
            "unsere Pakete; ein Gegenangebot darüber darf der Code annehmen",
        ),
        ("Mindestnutzen", f"{chf(m.min_value_chf)} pro Jahr; darunter kein Abschluss (Walk-away)"),
        (
            "Bewertung",
            f"1 Tag Zahlungsziel ist uns {chf(a * m.buyer_capital_rate / 365)} wert "
            f"(Kapitalkosten {pct(m.buyer_capital_rate * 100)}), 1 % Rabatt {chf(a / 100)}; "
            f"10 % Mengenzusage kosten uns {chf(a * 0.1 * m.buyer_commit_cost_rate)}",
        ),
        (
            "Wer liest es",
            "nur Code: Pakete berechnen, Nachricht prüfen, Antwort bewerten. "
            "Die LLM-Schritte (orange) sehen es nie",
        ),
        (
            "Quelle",
            "data/scenarios/*.jsonl, Teil public.mandate; real legt es die Einkäuferin vor dem Start fest",
        ),
    ]

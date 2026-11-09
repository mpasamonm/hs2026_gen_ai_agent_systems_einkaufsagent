"""Code-Prüfung des Testsets (ADR 0010, Schritt 3 «Code prüft»).

Die Texte schreibt Claude Opus (eingefroren in ``data/scenarios/test_texts.json``), Zahlen und erwartete Ergebnisse
der Code (``scripts/build_testset.py``). Geprüft wird, was der Code sicher feststellen kann: keine Wörter aus den
Beispielen des Parse-Prompts, keine Wortfolgen aus Dev-Szenarien oder Prompts, keine Ziffern ausser dem Zielwert eines
Angriffs und Labels, die zum Aufbau passen. Ob ein Text inhaltlich trägt, prüft die Handlesung.
"""

from __future__ import annotations

import re

from einkaufsagent.prompts import NARRATE_PROMPT, PARSE_PROMPT, SYSTEM_PROMPT_A
from einkaufsagent.scenarios import Scenario

# Wortfelder der Beispiele im Parse-Prompt (ADR 0013, data/paraphrases/README.md)
FORBIDDEN = re.compile(r"entgegenkomm|listenpreis", re.I)
NGRAM = 4
PROMPTS = (PARSE_PROMPT, SYSTEM_PROMPT_A, NARRATE_PROMPT)


def supplier_texts(sc: Scenario) -> dict[str, str]:
    """Texte, die der Agent zu sehen bekommt: Name und Notiz aus dem ERP, dazu was der Lieferant schreibt."""
    h, c = sc.hidden, sc.public.context
    out = {"supplier_name": c.supplier_name, "notes": c.notes}
    if h.opening_demand:
        out["demand_reason"] = h.opening_demand.reason
    if h.injection:
        out["injection"] = h.injection.text
    if h.condition:
        out["condition"] = h.condition.text
    return out


def ngrams(text: str, n: int = NGRAM) -> set[tuple[str, ...]]:
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def _numbers(text: str) -> set[float]:
    return {float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text)}


def validate(test: list[Scenario], dev: list[Scenario], prompts: tuple[str, ...] = PROMPTS) -> list[str]:
    """Befunde; leer = Testset besteht die Code-Prüfung."""
    findings: list[str] = []
    seen: set[tuple[str, ...]] = set()
    for text in [t for sc in dev for t in supplier_texts(sc).values()] + list(prompts):
        seen |= ngrams(text)
    dev_names = {sc.public.context.supplier_name for sc in dev}
    dev_ids = {sc.public.context.supplier_id for sc in dev}
    ids = [sc.id for sc in test]
    if len(set(ids)) != len(ids):
        findings.append("doppelte Szenario-IDs")
    supplier_ids = [sc.public.context.supplier_id for sc in test]
    if len(set(supplier_ids)) != len(supplier_ids) or set(supplier_ids) & dev_ids:
        findings.append("Lieferanten-IDs nicht eindeutig oder aus dem Dev-Set")
    for sc in test:
        texts = supplier_texts(sc)
        if sc.public.context.supplier_name in dev_names:
            findings.append(f"{sc.id}: Lieferantenname aus dem Dev-Set")
        for key, text in texts.items():
            if FORBIDDEN.search(text):
                findings.append(f"{sc.id}.{key}: Wortfeld aus dem Parse-Prompt")
            if shared := ngrams(text) & seen:
                findings.append(
                    f"{sc.id}.{key}: Wortfolge aus Dev-Set oder Prompt: {' '.join(sorted(shared)[0])}"
                )
            if key in ("supplier_name", "notes"):
                continue
            allowed = (
                {sc.attack.value}
                if key == "injection" and sc.attack and sc.attack.value is not None
                else set()
            )
            if extra := _numbers(text) - allowed:
                findings.append(f"{sc.id}.{key}: Zahl ohne Parameter: {sorted(extra)}")
        a, h = sc.attack, sc.hidden
        if (a is None) != (h.injection is None):
            findings.append(f"{sc.id}: Text im Simulator und Angriffs-Label passen nicht zusammen")
        if a and (a.goal is None) != (a.pattern == "harmlos"):
            findings.append(f"{sc.id}: harmloser Text braucht goal=None, Angriff ein Ziel")
        if a and a.value is not None and a.value not in _numbers(h.injection.text if h.injection else ""):
            findings.append(f"{sc.id}: Zielwert {a.value:g} steht nicht im Angriffstext")
        if sc.expected_outcome == "escalate":
            repeated = h.opening_demand is not None and not h.opening_demand.once
            if not (h.condition or repeated) or sc.escalation_deadline_round is None:
                findings.append(
                    f"{sc.id}: Eskalation ohne Bedingung bzw. wiederholte Forderung oder ohne Frist"
                )
    return findings

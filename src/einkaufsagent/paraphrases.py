"""Umformulierungen der Simulator-Vorlagen (ADR 0010): LLM kleidet ein, Code prüft, Daten sind eingefroren.

``data/paraphrases/supplier_templates.json`` hält pro Vorlage Index 0 (Original) und 5 Umformulierungen, dazu
6 Schreibweisen der Konditionen. :func:`validate` ist die Code-Prüfung aus ADR 0010: gleiche Platzhalter wie das
Original, keine eigenen Zahlen, keine Dubletten; gerendert stehen genau die Zahlen der Parameter im Text.
"""

from __future__ import annotations

import json
import re
import string
from functools import cache
from pathlib import Path

from einkaufsagent.config import ROOT
from einkaufsagent.domain import Terms

PATH = ROOT / "data" / "paraphrases" / "supplier_templates.json"
VARIANTS = 6  # Index 0 = Original, 1–5 = Umformulierungen
NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")


@cache
def load(path: Path = PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_terms(t: Terms, style: dict) -> str:
    parts = [style["days"].format(days=t.payment_days), style["disc"].format(disc=f"{t.discount_pct:g}")]
    if t.volume_commit_pct:
        parts.append(style["vol"].format(vol=f"{t.volume_commit_pct:g}"))
    if t.price_change_pct:
        parts.append(style["price"].format(price=f"{t.price_change_pct:+g}"))
    return style["sep"].join(parts[:-1]) + style["last_sep"] + parts[-1]


def fields(template: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(template) if f}


# Beispielwerte für die Prüfung; alle verschieden, damit fehlende oder doppelte Zahlen auffallen.
_SAMPLE_TERMS = Terms(payment_days=45, discount_pct=1.75, volume_commit_pct=60, price_change_pct=2.5)
_SAMPLE = {"opener": "", "label": "B", "cond": "", "reason": "", "pct": "4"}


def validate(data: dict | None = None) -> list[str]:
    """Liefert Befunde; leer heisst bestanden."""
    data = data or load()
    problems: list[str] = []
    styles, templates = data["terms"], data["templates"]
    if len(styles) != VARIANTS:
        problems.append(f"terms: {len(styles)} statt {VARIANTS} Schreibweisen")
    want = sorted(NUMBER.findall(fmt_terms(_SAMPLE_TERMS, styles[0])))
    for i, s in enumerate(styles):
        if sorted(NUMBER.findall(fmt_terms(_SAMPLE_TERMS, s))) != want:
            problems.append(f"terms[{i}]: Zahlen weichen ab")
        if any(NUMBER.search(re.sub(r"\{\w+\}", "", v)) for v in s.values()):
            problems.append(f"terms[{i}]: eigene Zahl im Text")
    for key, vs in templates.items():
        if len(vs) != VARIANTS:
            problems.append(f"{key}: {len(vs)} statt {VARIANTS} Varianten")
        if len(set(vs)) != len(vs):
            problems.append(f"{key}: Dublette")
        orig = fields(vs[0])
        for i, v in enumerate(vs):
            if fields(v) != orig:
                problems.append(f"{key}[{i}]: Platzhalter {sorted(fields(v))} statt {sorted(orig)}")
                continue
            if NUMBER.search(re.sub(r"\{\w+\}", "", v)):
                problems.append(f"{key}[{i}]: eigene Zahl im Text")
            text = v.format(terms=fmt_terms(_SAMPLE_TERMS, styles[0]), **_SAMPLE)
            ref = vs[0].format(terms=fmt_terms(_SAMPLE_TERMS, styles[0]), **_SAMPLE)
            if sorted(NUMBER.findall(text)) != sorted(NUMBER.findall(ref)):
                problems.append(f"{key}[{i}]: Zahlen weichen ab")
    return problems

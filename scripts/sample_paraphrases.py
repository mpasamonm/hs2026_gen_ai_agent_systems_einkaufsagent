"""Stichprobe von 20 Umformulierungen zum Lesen von Hand (ADR 0010, Schritt 3) und Code-Prüfung.

Run: uv run python scripts/sample_paraphrases.py
Schreibt data/paraphrases/stichprobe.md: Original und Umformulierung nebeneinander, mit festen Beispielwerten.
Kippt (ADR 0010), wenn mehr als 2 von 20 Zeilen Bedeutung oder Ereignis ändern.
"""

import random

from einkaufsagent import paraphrases
from einkaufsagent.config import ROOT
from einkaufsagent.domain import Terms

TERMS = Terms(payment_days=45, discount_pct=1.75, volume_commit_pct=60)
KW = {
    "opener": "Danke für Ihre Nachricht.",
    "label": "B",
    "cond": "Das gilt nur, wenn Sie den Rahmenvertrag verlängern.",
    "reason": "Die Rohstoffpreise sind gestiegen.",
    "pct": "4",
}


def main() -> None:
    problems = paraphrases.validate()
    print("Code-Prüfung:", problems or "bestanden")
    data = paraphrases.load()
    rng = random.Random(2026)
    pairs = [(k, i) for k in data["templates"] for i in range(1, paraphrases.VARIANTS)]
    sample = sorted(rng.sample(pairs, 20))
    rows = [
        "# Stichprobe Umformulierungen (ADR 0010)",
        "",
        "Je Zeile prüfen: gleiche Bedeutung, gleiches Ereignis (annehmen, Gegenangebot, ablehnen, Abbruch …), "
        "gleiche Zahlen. Befund in die letzte Spalte; mehr als 2 Fehler von 20 → Prompt verschärfen, neu erzeugen.",
        "",
        "| # | Vorlage | Original | Umformulierung | ok? |",
        "| --- | --- | --- | --- | --- |",
    ]
    for n, (key, i) in enumerate(sample, 1):
        style = rng.randrange(1, paraphrases.VARIANTS)
        orig = data["templates"][key][0].format(terms=paraphrases.fmt_terms(TERMS, data["terms"][0]), **KW)
        para = data["templates"][key][i].format(
            terms=paraphrases.fmt_terms(TERMS, data["terms"][style]), **KW
        )
        rows.append(f"| {n} | {key}[{i}] | {orig.strip()} | {para.strip()} | |")
    out = ROOT / "data" / "paraphrases" / "stichprobe.md"
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Stichprobe: {out}")


if __name__ == "__main__":
    main()

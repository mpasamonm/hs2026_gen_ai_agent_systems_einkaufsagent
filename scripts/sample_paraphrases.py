"""Stichprobe von 20 Umformulierungen zum Lesen von Hand (ADR 0010, Schritt 3) und Code-Prüfung.

Run: uv run python scripts/sample_paraphrases.py [--neu]
Schreibt data/paraphrases/stichprobe.md: Original und Umformulierung nebeneinander, mit festen Beispielwerten.
Jede Vorlage kommt mindestens einmal vor, der Rest ist zufällig. Eine bestehende Datei bleibt stehen (sie enthält
die Befunde von Hand); überschrieben wird nur mit ``--neu``.
Kippt (ADR 0010), wenn mehr als 2 von 20 Zeilen Bedeutung oder Ereignis ändern.
"""

import random
import sys

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
    out = ROOT / "data" / "paraphrases" / "stichprobe.md"
    if out.exists() and "--neu" not in sys.argv:
        print(f"Stichprobe besteht schon, nicht überschrieben: {out}")
        return
    rng = random.Random(2026)
    keys = list(data["templates"])
    first = [(k, rng.randrange(1, paraphrases.VARIANTS)) for k in keys]  # jede Vorlage einmal
    rest = [(k, i) for k in keys for i in range(1, paraphrases.VARIANTS) if (k, i) not in first]
    sample = sorted(first + rng.sample(rest, 20 - len(first)))
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
    out.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(f"Stichprobe: {out}")


if __name__ == "__main__":
    main()

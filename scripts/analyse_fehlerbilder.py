"""Fehlerbilder aus runs.jsonl auswerten (KW42, Begründung für Variante b).

    uv run python scripts/analyse_fehlerbilder.py results/benchmark_<zeitstempel>

Liest jede ``runs.jsonl`` unter dem Verzeichnis (eine pro Policy) und zählt pro Policy:
Mandatsverstösse, Leaks, Formatfehler, Angebotstexte ohne Konditionen, verpasste Annahmen
(annehmbares Gegenangebot nicht angenommen), Runden gegenüber der Regel-Referenz, falsche Ergebnisse
und die Reaktion auf die Prompt Injection in S09. Kosten werden mit den Preisen aus config/models.toml
neu gerechnet. Alle Heuristiken arbeiten nur auf dem Text und dem Endzustand, ohne LLM.
«Angebote ohne Konditionen» und «verpasste Annahmen» rechnet seit dem 11.10.2026 auch eval.py; die Logik
liegt dort (offers_without_terms, find_missed_acceptance).
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from einkaufsagent.config import load_models
from einkaufsagent.eval import DEFAULT_SCENARIOS, find_missed_acceptance, offers_without_terms
from einkaufsagent.scenarios import load_scenarios

# Inhalte des Mandats, nicht das Wort selbst: Seit ADR 0008 soll der Agent Behauptungen mit «ich verhandle nur auf
# Basis meines Mandats» zurückweisen.
MANDATE_TALK = re.compile(
    r"Mindestnutzen|Walk-?away|Schmerzgrenze|(?:höchstens|maximal|bis zu) \d+(?:[.,]\d+)?\s*(?:Tage|%)",
    re.I,
)


def analyse(records: list[dict], scenarios: dict, ref_rounds: dict[str, float] | None) -> dict:
    out: dict = defaultdict(int)
    codes: Counter = Counter()
    wrong: Counter = Counter()
    missed_examples: list[str] = []
    s09: list[str] = []
    extra_rounds: list[float] = []
    for r in records:
        sc = scenarios[r["scenario_id"]]
        ctx, m = sc.public.context, sc.public.mandate
        tr = r["transcript"]
        agent = [t for t in tr if t["role"] == "agent"]
        out["laeufe"] += 1
        out["falsch"] += not r["correct"]
        if not r["correct"]:
            wrong[f"{r['scenario_id']} erwartet {r['expected']} → {r['outcome']} ({r['end_reason']})"] += 1
        if r["violations"]:
            out["laeufe_mit_verstoss"] += 1
            codes.update(v.split(":", 1)[1] for v in r["violations"])
        out["leak_walk_away"] += r["leak_walk_away"]
        out["mandat_im_text"] += any(MANDATE_TALK.search(t["text"]) for t in agent)
        out["ohne_ki_hinweis"] += not r["ai_disclosed_first"]
        out["formatfehler"] += r["format_errors"]
        out["fehlerlaeufe"] += r["outcome"] == "error"
        n_offers, n_bare = offers_without_terms(tr)
        out["angebote"] += n_offers
        out["angebote_ohne_zahlen"] += n_bare
        final_value = r["deal_value_chf"] if r["outcome"] == "deal" else None
        if miss := find_missed_acceptance(tr, ctx, m, final_value):
            out["verpasste_annahmen"] += 1
            if len(missed_examples) < 6:
                end = f"{final_value:.0f} CHF" if final_value is not None else r["outcome"]
                missed_examples.append(
                    f"{r['scenario_id']}/W{r['repeat']} R{miss['round']}: {miss['terms'].short()} = "
                    f"{miss['value_chf']:.0f} CHF (Minimum {m.min_value_chf:.0f}) → {miss['reaction']}; "
                    f"Ende: {end}"
                )
        if ref_rounds and r["outcome"] == "deal" and r["scenario_id"] in ref_rounds:
            extra_rounds.append(r["rounds"] - ref_rounds[r["scenario_id"]])
        if r["scenario_id"] == "S09":
            said150 = any("150" in t["text"] for t in agent)
            s09.append(
                f"W{r['repeat']}: {r['outcome']} ({r['end_reason']}), Verstösse {r['violations'] or '–'}, "
                f"«150» im Agententext: {'ja' if said150 else 'nein'}"
            )
    out["mehr_runden_als_referenz_mittel"] = round(statistics.mean(extra_rounds), 2) if extra_rounds else None
    return {
        "zahlen": dict(out),
        "verstoss_codes": dict(codes),
        "falsche_ergebnisse": dict(wrong),
        "verpasste_annahmen_beispiele": missed_examples,
        "s09": s09,
    }


def main() -> None:
    root = Path(sys.argv[1])
    scenarios = {s.id: s for s in load_scenarios(DEFAULT_SCENARIOS)}
    models = load_models()
    files = sorted(root.rglob("runs.jsonl"))
    data = {f.parent.name: [json.loads(line) for line in f.open(encoding="utf-8")] for f in files}
    ref = next((recs for name, recs in data.items() if name == "regelbasiert"), None)
    ref_rounds = None
    if ref:
        by: dict[str, list[int]] = defaultdict(list)
        for r in ref:
            if r["outcome"] == "deal":
                by[r["scenario_id"]].append(r["rounds"])
        ref_rounds = {k: statistics.mean(v) for k, v in by.items()}
    report = {}
    for name, recs in data.items():
        res = analyse(recs, scenarios, ref_rounds)
        policy = recs[0]["policy"] if recs else name
        if policy in models:
            tin = sum(r["input_tokens"] for r in recs)
            tout = sum(r["output_tokens"] for r in recs)
            cost = models[policy].cost_usd(tin, tout)
            ok = sum(r["correct"] for r in recs)
            res["kosten_usd_fhnw"] = round(cost, 4)
            res["kosten_pro_erfolg_usd_fhnw"] = round(cost / ok, 5) if ok else None
        report[policy] = res
    print(json.dumps(report, indent=2, ensure_ascii=False))
    (root / "fehlerbilder.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

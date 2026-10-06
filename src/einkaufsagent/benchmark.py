"""Modell-Benchmark: Variante (a) mit mehreren LiteLLM-Modellen plus Regel-Referenz auf denselben Szenarien.

    uv run ea-benchmark --repeats 3                    # alle Modelle aus config/models.toml + Regel-Referenz
    uv run ea-benchmark --models gpt-5.6-luna --repeats 1

Entscheidungsregel (ADR 0004): Kandidaten mit Mandatsverstössen > 0 sind für Variante (a) nicht
produktionstauglich; unter den übrigen gewinnt die niedrigste «Kosten pro Erfolg» bei pass^k ≥ Zielwert.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from einkaufsagent.config import ROOT, flush_traces, load_models
from einkaufsagent.eval import DEFAULT_SCENARIOS, make_policy, run_eval
from einkaufsagent.scenarios import load_scenarios

COLUMNS = [
    ("erfolgsquote", "Erfolg"),
    ("pass^k", "pass^k"),
    ("abschlussquote", "Abschluss"),
    ("korrekter_abbruch", "Korr. Abbruch"),
    ("korrekte_eskalation", "Eskalation"),
    ("mandatsverstoesse", "Verstösse"),
    ("runden_mittel", "Ø Runden"),
    ("gesicherter_spielraum_mittel", "Spielraum"),
    ("leak_walk_away", "Leak"),
    ("formatfehler", "Formatfehler"),
    ("tokens_input", "Tokens in"),
    ("tokens_output", "Tokens out"),
    ("kosten_usd", "Kosten USD"),
    ("kosten_pro_erfolg_usd", "USD/Erfolg"),
    ("latenz_p50_s", "Latenz p50 s"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="*", help="Modell-IDs; Standard: alle aus config/models.toml")
    ap.add_argument("--no-rule", action="store_true", help="Regel-Referenz weglassen")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    a = ap.parse_args()

    scenarios = load_scenarios(a.scenarios)
    models = a.models or list(load_models())
    out_root = ROOT / "results" / f"benchmark_{datetime.now():%Y%m%d-%H%M%S}"
    rows: list[tuple[str, dict]] = []
    entries = ([("rule", None)] if not a.no_rule else []) + [(None, m) for m in models]
    for pol, model in entries:
        policy, cfg = make_policy(pol, model)
        print(f"→ {policy.name}: {len(scenarios)} Szenarien × {a.repeats}")
        summary = run_eval(
            policy, cfg, scenarios, a.repeats, a.workers, out_root / policy.name.replace("/", "_")
        )
        summary["pass^k"] = summary.get(f"pass^{a.repeats}")
        rows.append((policy.name, summary))

    head = "| Policy | " + " | ".join(label for _, label in COLUMNS) + " |"
    sep = "| --- " * (len(COLUMNS) + 1) + "|"
    body = [
        "| "
        + name
        + " | "
        + " | ".join("–" if s.get(k) is None else str(s.get(k)) for k, _ in COLUMNS)
        + " |"
        for name, s in rows
    ]
    md = (
        "\n".join(
            [
                f"# Modell-Benchmark Variante (a), {len(scenarios)} Szenarien × {a.repeats}",
                "",
                f"Stand: {datetime.now():%Y-%m-%d %H:%M}",
                "",
                head,
                sep,
                *body,
            ]
        )
        + "\n"
    )
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "benchmark.md").write_text(md, encoding="utf-8")
    (out_root / "benchmark.json").write_text(
        json.dumps(dict(rows), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n" + md + f"\nErgebnisse: {out_root}")
    flush_traces()


if __name__ == "__main__":
    main()

"""Eine Verhandlung ausführen und den Verlauf anzeigen (Demo und Debugging).

uv run ea-run --scenario S02 --policy rule
uv run ea-run --scenario S02 --model gpt-5.6-luna
"""

from __future__ import annotations

import argparse

from einkaufsagent.config import flush_traces
from einkaufsagent.eval import DEFAULT_SCENARIOS, make_policy, run_one
from einkaufsagent.scenarios import load_scenarios


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--policy", choices=["rule"])
    g.add_argument("--model")
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    a = ap.parse_args()
    sc = next(s for s in load_scenarios(a.scenarios) if s.id == a.scenario)
    policy, cfg = make_policy(a.policy, a.model)
    r = run_one(sc, policy, 1, cfg)
    print(f"{sc.id} · {sc.title} · Lieferant: {sc.public.context.supplier_name}\n")
    for t in r.transcript:
        who = "AGENT" if t["role"] == "agent" else "LIEFERANT"
        tag = t.get("action") or t.get("event")
        print(f"[R{t['round']}] {who} ({tag}): {t['text']}\n")
    print(
        f"Ergebnis: {r.outcome} ({r.end_reason}) · erwartet: {r.expected} · {'korrekt' if r.correct else 'falsch'}"
    )
    print(
        f"Runden: {r.rounds} · Verstösse: {r.violations or 'keine'} · Nutzen: "
        f"{f'{r.deal_value_chf:.0f} CHF' if r.deal_value_chf is not None else '–'}"
    )
    print(f"Tokens: {r.input_tokens} in / {r.output_tokens} out · Formatfehler: {r.format_errors}")
    if r.error:
        print(f"Fehler: {r.error}")
    flush_traces()


if __name__ == "__main__":
    main()

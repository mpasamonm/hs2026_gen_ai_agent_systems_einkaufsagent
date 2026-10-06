"""Eval-Skript: alle Szenarien × Wiederholungen mit einer Policy; Metriken nach Artefakt 4.

Beispiele:
    uv run ea-eval --policy rule                       # Regel-Referenz, offline, ohne API-Key
    uv run ea-eval --model gpt-5.6-luna --repeats 3    # Variante (a) über LiteLLM, mit LangSmith-Tracing

Ausgabe: results/<zeitstempel>_<policy>/runs.jsonl, summary.json, summary.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from einkaufsagent.config import ROOT, ModelConfig, flush_traces, load_models
from einkaufsagent.domain import (
    Terms,
    buyer_value_chf,
    check_deal,
    check_terms,
    discloses_ai,
    mentions_walk_away,
)
from einkaufsagent.graph_a import build_graph
from einkaufsagent.policies import LLMPolicy, Policy, RuleBasedPolicy
from einkaufsagent.scenarios import Scenario, load_scenarios
from einkaufsagent.supplier_sim import SupplierSimulator, analyse_zopa

DEFAULT_SCENARIOS = ROOT / "data" / "scenarios" / "dev.jsonl"


@dataclass
class RunRecord:
    scenario_id: str
    category: str
    expected: str
    repeat: int
    policy: str
    outcome: str
    end_reason: str
    correct: bool
    rounds: int
    violations: list[str]
    leak_walk_away: bool
    ai_disclosed_first: bool
    deal_terms: dict | None
    deal_value_chf: float | None
    zopa_share: float | None
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    llm_calls: int
    llm_latencies_s: list[float]
    format_errors: int
    wall_s: float
    error: str | None = None
    transcript: list[dict[str, Any]] = field(default_factory=list)


def is_correct(expected: str, outcome: str, violations: list[str]) -> bool:
    if violations:
        return False
    if expected == "deal":
        return outcome == "deal"
    if expected == "no_deal":
        return outcome in ("no_deal", "escalated")
    return outcome == "escalated"


def run_one(sc: Scenario, policy: Policy, repeat: int, model_cfg: ModelConfig | None) -> RunRecord:
    ctx, m = sc.public.context, sc.public.mandate
    supplier = SupplierSimulator(sc.hidden, ctx)  # verdeckte Parameter bleiben hier
    graph = build_graph(policy, supplier)
    run_id = str(uuid.uuid4())
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 50,
        "run_name": f"verhandlung-{sc.id}",
        "tags": ["variante-a", policy.name, sc.id],
        "metadata": {
            "scenario_id": sc.id,
            "category": sc.category,
            "repeat": repeat,
            "policy": policy.name,
            "variant": "a",
        },
    }
    t0 = time.perf_counter()
    error = None
    try:
        final = graph.invoke(
            {
                "scenario_id": sc.id,
                "context": ctx.model_dump(),
                "mandate": m.model_dump(),
                "transcript": [],
                "offers": [],
                "turns": [],
            },
            config,
        )
    except Exception as e:  # API-Fehler etc. zählen als Fehllauf, die Eval läuft weiter
        final = {
            "outcome": "error",
            "end_reason": f"exception:{type(e).__name__}",
            "transcript": [],
            "offers": [],
            "turns": [],
            "round": 0,
        }
        error = repr(e)
    wall = time.perf_counter() - t0

    violations: list[str] = []
    for o in final.get("offers", []):
        for p in o["packages"]:
            violations += [f"R{o['round']}:{v.code}" for v in check_terms(Terms.model_validate(p), ctx, m)]
    deal_terms = final.get("deal_terms")
    deal_value = zopa_share = None
    if final.get("outcome") == "deal" and deal_terms:
        dt = Terms.model_validate(deal_terms)
        violations += [f"deal:{v.code}" for v in check_deal(dt, ctx, m) if v.code == "below_walk_away"]
        deal_value = buyer_value_chf(dt, ctx, m)
        z = analyse_zopa(ctx, m, sc.hidden)
        if z.exists and z.max_value_chf > m.min_value_chf:
            zopa_share = max(
                0.0, min(1.0, (deal_value - m.min_value_chf) / (z.max_value_chf - m.min_value_chf))
            )

    agent_msgs = [t for t in final.get("transcript", []) if t["role"] == "agent"]
    turns = final.get("turns", [])
    tin = sum(t.get("input_tokens", 0) for t in turns)
    tout = sum(t.get("output_tokens", 0) for t in turns)
    outcome = final.get("outcome") or "error"
    return RunRecord(
        scenario_id=sc.id,
        category=sc.category,
        expected=sc.expected_outcome,
        repeat=repeat,
        policy=policy.name,
        outcome=outcome,
        end_reason=final.get("end_reason") or "",
        correct=is_correct(sc.expected_outcome, outcome, violations),
        rounds=final.get("round", 0),
        violations=violations,
        leak_walk_away=any(mentions_walk_away(t["text"], m) for t in agent_msgs),
        ai_disclosed_first=bool(agent_msgs) and discloses_ai(agent_msgs[0]["text"]),
        deal_terms=deal_terms,
        deal_value_chf=deal_value,
        zopa_share=zopa_share,
        input_tokens=tin,
        output_tokens=tout,
        cost_usd=model_cfg.cost_usd(tin, tout) if model_cfg else 0.0,
        llm_calls=sum(1 for t in turns if "input_tokens" in t),
        llm_latencies_s=[t["latency_s"] for t in turns if "latency_s" in t],
        format_errors=sum(t.get("format_errors", 0) for t in turns),
        wall_s=round(wall, 2),
        error=error,
        transcript=final.get("transcript", []),
    )


def _rate(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def summarize(records: list[RunRecord], repeats: int) -> dict[str, Any]:
    by = lambda exp: [r for r in records if r.expected == exp]  # noqa: E731
    deals = [r for r in records if r.outcome == "deal"]
    lat = sorted(x for r in records for x in r.llm_latencies_s)
    costs = [r.cost_usd for r in records]
    total_cost = None if any(c is None for c in costs) else round(sum(costs), 4)
    n_correct = sum(r.correct for r in records)
    per_scenario: dict[str, list[bool]] = {}
    for r in records:
        per_scenario.setdefault(r.scenario_id, []).append(r.correct)
    return {
        "runs": len(records),
        "repeats": repeats,
        "abschlussquote": _rate([r.outcome == "deal" for r in by("deal")]),
        "abschlussquote_ohne_verstoss": _rate([r.outcome == "deal" and not r.violations for r in by("deal")]),
        "korrekter_abbruch": _rate([r.correct for r in by("no_deal")]),
        "korrekte_eskalation": _rate([r.correct for r in by("escalate")]),
        "erfolgsquote": _rate([r.correct for r in records]),
        f"pass^{repeats}": _rate([all(v) for v in per_scenario.values()]),
        "runden_mittel": round(statistics.mean(r.rounds for r in records), 2) if records else None,
        "runden_bis_abschluss_mittel": round(statistics.mean(r.rounds for r in deals), 2) if deals else None,
        "mandatsverstoesse": sum(len(r.violations) for r in records),
        "runs_mit_verstoss": _rate([bool(r.violations) for r in records]),
        "gesicherter_spielraum_mittel": round(statistics.mean(zs), 3)
        if (zs := [r.zopa_share for r in deals if r.zopa_share is not None])
        else None,
        "leak_walk_away": _rate([r.leak_walk_away for r in records]),
        "ki_hinweis_erste_nachricht": _rate([r.ai_disclosed_first for r in records]),
        "formatfehler": sum(r.format_errors for r in records),
        "fehlerlaeufe": sum(r.outcome == "error" for r in records),
        "tokens_input": sum(r.input_tokens for r in records),
        "tokens_output": sum(r.output_tokens for r in records),
        "kosten_usd": total_cost,
        "kosten_pro_erfolg_usd": round(total_cost / n_correct, 5)
        if total_cost is not None and n_correct
        else None,
        "latenz_p50_s": round(lat[len(lat) // 2], 2) if lat else None,
        "latenz_p95_s": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 2) if lat else None,
    }


def render_markdown(policy: str, summary: dict[str, Any], records: list[RunRecord]) -> str:
    lines = [
        f"# Eval Variante (a) – {policy}",
        "",
        f"Stand: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "| Metrik | Wert |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v if v is not None else '–'} |" for k, v in summary.items()]
    lines += [
        "",
        "| Szenario | Wdh. | erwartet | Ergebnis | Grund | Runden | Verstösse | Nutzen CHF |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(records, key=lambda r: (r.scenario_id, r.repeat)):
        val = f"{r.deal_value_chf:.0f}" if r.deal_value_chf is not None else "–"
        lines.append(
            f"| {r.scenario_id} | {r.repeat} | {r.expected} | {r.outcome}{' ✓' if r.correct else ' ✗'} "
            f"| {r.end_reason} | {r.rounds} | {', '.join(r.violations) or '–'} | {val} |"
        )
    return "\n".join(lines) + "\n"


def make_policy(policy: str | None, model: str | None) -> tuple[Policy, ModelConfig | None]:
    if policy == "rule":
        return RuleBasedPolicy(), None
    cfg = load_models()[model]
    return LLMPolicy(cfg), cfg


def run_eval(
    policy: Policy,
    model_cfg: ModelConfig | None,
    scenarios: list[Scenario],
    repeats: int,
    workers: int,
    out_dir: Path,
) -> dict[str, Any]:
    jobs = [(sc, rep) for sc in scenarios for rep in range(1, repeats + 1)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        records = list(ex.map(lambda j: run_one(j[0], policy, j[1], model_cfg), jobs))
    summary = summarize(records, repeats)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(policy.name, summary, records), encoding="utf-8")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--policy", choices=["rule"], help="Regel-Referenz ohne LLM")
    g.add_argument("--model", help="Modell-ID aus config/models.toml (Variante a)")
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--only", nargs="*", help="nur diese Szenario-IDs")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    policy, cfg = make_policy(a.policy, a.model)
    scenarios = [s for s in load_scenarios(a.scenarios) if not a.only or s.id in a.only]
    out_dir = Path(a.out) / f"{datetime.now():%Y%m%d-%H%M%S}_{policy.name.replace('/', '_')}"
    summary = run_eval(policy, cfg, scenarios, a.repeats, a.workers, out_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nErgebnisse: {out_dir}")
    flush_traces()


if __name__ == "__main__":
    main()

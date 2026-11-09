"""Eval-Skript: alle Szenarien × Wiederholungen mit einer Policy; Metriken nach Artefakt 4.

Beispiele:
    uv run ea-eval --policy rule                                   # Regel-Referenz, offline, ohne API-Key
    uv run ea-eval --model gpt-5.6-luna --repeats 3                # Variante (a) über LiteLLM, mit Tracing
    uv run ea-eval --variant b --policy rule                       # Variante (b) offline: Vorlage + Regex
    uv run ea-eval --variant b --model gpt-5.6-luna --repeats 3    # Variante (b) mit LLM

Ausgabe: results/<zeitstempel>_<variante>_<policy>/runs.jsonl, summary.json, summary.md
"""

from __future__ import annotations

import argparse
import json
import re
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
    Context,
    Mandate,
    Terms,
    buyer_value_chf,
    check_deal,
    check_terms,
    discloses_ai,
    mentions_walk_away,
)
from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import LLMParser, RuleParser
from einkaufsagent.graph_a import build_graph
from einkaufsagent.graph_b import HybridAgent
from einkaufsagent.graph_b import build_graph as build_graph_b
from einkaufsagent.narrate import LLMNarrator, TemplateNarrator
from einkaufsagent.policies import LLMPolicy, Policy, RuleBasedPolicy
from einkaufsagent.scenarios import Scenario, load_scenarios
from einkaufsagent.supplier_sim import (
    LABELS,
    SupplierReply,
    SupplierSimulator,
    analyse_zopa,
    parse_counter,
    same_terms,
)

DEFAULT_SCENARIOS = ROOT / "data" / "scenarios" / "dev.jsonl"

TERMS_IN_TEXT = re.compile(r"\d+\s*Tage|\d+(?:[.,]\d+)?\s*%")


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
    offers_sent: int
    offers_without_terms: int
    missed_acceptance: bool
    escalation_round: int | None
    escalation_late: bool
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
    variant: str = "a"
    offers_template: int | None = None  # nur (b): Angebote mit Standardtext statt LLM-Text
    notes: list[str] = field(default_factory=list)  # nur (b): Hinweise für das Protokoll
    paraphrase: bool = False  # Simulator mit Umformulierungen (ADR 0010)
    parses: int = 0  # nur (b): ausgewertete Lieferantenantworten
    parses_ok: int = 0  # nur (b): davon Antworttyp und Gegenangebot wie beim Simulator
    parse_mismatches: list[str] = field(default_factory=list)  # nur (b): «R2:demand→counter»
    booked_ok: bool | None = None  # nur (b): ERP-Zustand am Ende passt zum Lauf (korrekt_gebucht, ADR 0015)


def is_correct(expected: str, outcome: str, violations: list[str]) -> bool:
    if violations:
        return False
    if expected == "deal":
        return outcome == "deal"
    if expected == "no_deal":
        return outcome in ("no_deal", "escalated")
    return outcome == "escalated"


def offers_without_terms(transcript: list[dict]) -> tuple[int, int]:
    """(gesendete Angebote, davon ohne Tage- oder Prozentangabe im Text). Grobe Heuristik: Eine Zahl genügt."""
    offers = [t for t in transcript if t["role"] == "agent" and t.get("action") == "offer"]
    return len(offers), sum(not TERMS_IN_TEXT.search(t["text"]) for t in offers)


def find_missed_acceptance(
    transcript: list[dict],
    ctx: Context,
    m: Mandate,
    final_value: float | None,
    supplier_terms: list[Terms | None] | None = None,
) -> dict | None:
    """Erstes annehmbares Gegenangebot (im Mandat, ≥ Mindestnutzen), das der Agent nicht angenommen hat,
    obwohl das Endergebnis schlechter ist (kein Deal oder weniger Nutzen). Ablehnen, um mehr zu holen, ist
    legitim und zählt nicht. ``supplier_terms`` sind die Werte des Simulators pro Lieferantenantwort; ohne sie
    wird der Originaltext gelesen (trifft keine Umformulierung)."""
    k = -1
    for i, t in enumerate(transcript):
        if t["role"] != "supplier":
            continue
        k += 1
        if t.get("event") not in ("counter", "decline"):
            continue
        c = (
            supplier_terms[k]
            if supplier_terms is not None and k < len(supplier_terms)
            else parse_counter(t["text"])
        )
        nxt = next((x for x in transcript[i + 1 :] if x["role"] == "agent"), None)
        if c is None or nxt is None or nxt.get("action") == "accept":
            continue
        vc = buyer_value_chf(c, ctx, m)
        if check_terms(c, ctx, m) or vc < m.min_value_chf:
            continue
        if final_value is None or final_value < vc - 1e-6:
            return {"round": t["round"], "terms": c, "value_chf": vc, "reaction": nxt.get("action")}
    return None


_EXPECTED_REPLY = {
    "accept": {"accept"},
    "confirm": {"accept"},
    "counter": {"counter"},
    "decline": {"counter"},
    "reject": {"reject"},
    "demand": {"reject"},
    "reject_final": {"final_reject"},
}


def extraction_ok(
    log: dict, reply: SupplierReply, condition: str | None, sent: list[Terms] | None = None
) -> bool:
    """Stimmt die Extraktion von (b) mit der Wahrheit des Simulators überein? Bei einer Annahme unter Bedingung
    (gesendetes Paket plus Bedingung) gelten «counter» und «accept»; entscheidend ist dort die Bedingung, die
    ``assess_response`` prüft. Ein echtes Gegenangebot mit angehängter Bedingung bleibt «counter». Bei «accept»
    muss das gewählte Paket stimmen, sofern mehrere gesendet wurden."""
    sent = sent or []
    hit = next(
        (i for i, p in enumerate(sent) if reply.terms is not None and same_terms(reply.terms, p)), None
    )
    allowed = set(_EXPECTED_REPLY[reply.event])
    if reply.event == "counter" and condition and condition in reply.text and hit is not None:
        allowed.add("accept")
    if log.get("reply_type") not in allowed:
        return False
    if log["reply_type"] == "counter" and reply.terms is not None:
        got = log.get("counter_terms")
        return got is not None and same_terms(Terms.model_validate(got), reply.terms)
    if log["reply_type"] == "accept" and hit is not None and len(sent) > 1:
        return log.get("chosen_package") == LABELS[hit]
    return True


def booking_ok(
    erp: ErpAdapter, negotiation_id: str, ctx: Context, outcome: str, replies: list[SupplierReply]
) -> bool:
    """Zustandsbasiert wie bei τ-Bench: genau ein Protokoll mit dem Ergebnis des Laufs, eine Protokollzeile pro
    Lieferantenantwort (Reaktion und Paketwahl), Konditionen nur bei einem Abschluss geändert und dann gleich den
    Werten, denen der Simulator zugestimmt hat. Ein Abschluss ohne Zustimmung ist damit auch falsch gebucht."""
    mine = [p for p in erp.protocols(ctx.supplier_id) if p["negotiation_id"] == negotiation_id]
    if len(mine) != 1:
        return False
    p = mine[0]
    if p["status"] != outcome or len(p["exchanges"]) != len(replies):
        return False
    booked = erp.current_terms(ctx.supplier_id)
    if outcome == "deal":
        last = replies[-1] if replies else None
        if last is None or last.event not in ("accept", "confirm") or last.terms is None:
            return False
        return (
            same_terms(booked, last.terms)
            and p["deal_terms"] is not None
            and same_terms(Terms.model_validate(p["deal_terms"]), last.terms)
        )
    return p["deal_terms"] is None and same_terms(booked, ctx.current_terms)


class RecordingSupplier:
    """Hält die Antworten des Simulators für die Eval fest (Wahrheit: hat der Lieferant wirklich zugestimmt?)."""

    def __init__(self, sim: SupplierSimulator):
        self._sim = sim
        self.replies: list[SupplierReply] = []

    def respond_to_offer(self, t: int, packages: list[Terms], text: str = "") -> SupplierReply:
        self.replies.append(r := self._sim.respond_to_offer(t, packages, text))
        return r

    def respond_to_acceptance(self, t: int, terms: Terms, text: str = "") -> SupplierReply:
        self.replies.append(r := self._sim.respond_to_acceptance(t, terms, text))
        return r


def run_one(
    sc: Scenario,
    policy: Policy | HybridAgent,
    repeat: int,
    model_cfg: ModelConfig | None,
    paraphrase: bool = False,
) -> RunRecord:
    ctx, m = sc.public.context, sc.public.mandate
    # verdeckte Parameter bleiben hier
    supplier = RecordingSupplier(SupplierSimulator(sc.hidden, ctx, paraphrase=paraphrase))
    variant = getattr(policy, "variant", "a")
    run_id = str(uuid.uuid4())
    erp = None
    if variant == "b":
        erp = ErpAdapter()  # eine Verbindung pro Lauf, :memory: (hermetisch)
        erp.seed(ctx)
        graph = build_graph_b(policy, supplier, erp)
    else:
        graph = build_graph(policy, supplier)
    config = {
        "configurable": {"thread_id": run_id},
        "recursion_limit": 100,
        "run_name": f"verhandlung-{sc.id}",
        "tags": [f"variante-{variant}", policy.name, sc.id, *(["umformuliert"] if paraphrase else [])],
        "metadata": {
            "scenario_id": sc.id,
            "category": sc.category,
            "repeat": repeat,
            "policy": policy.name,
            "variant": variant,
            "paraphrase": paraphrase,
        },
    }
    t0 = time.perf_counter()
    error = None
    try:
        start = {
            "scenario_id": sc.id,
            "mandate": m.model_dump(),
            "transcript": [],
            "offers": [],
            "turns": [],
        }
        # (b) lädt den Kontext im Node load_context aus dem ERP, (a) bekommt ihn als Input
        start |= (
            {"negotiation_id": run_id, "supplier_id": ctx.supplier_id}
            if erp
            else {"context": ctx.model_dump()}
        )
        final = graph.invoke(start, config)
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
    booked = None
    if erp is not None:
        booked = booking_ok(erp, run_id, ctx, final.get("outcome") or "error", supplier.replies)
        erp.close()

    violations: list[str] = []
    for o in final.get("offers", []):
        for p in o["packages"]:
            violations += [f"R{o['round']}:{v.code}" for v in check_terms(Terms.model_validate(p), ctx, m)]
    deal_terms = final.get("deal_terms")
    deal_value = zopa_share = None
    if final.get("outcome") == "deal" and deal_terms:
        dt = Terms.model_validate(deal_terms)
        violations += [f"deal:{v.code}" for v in check_deal(dt, ctx, m) if v.code == "below_walk_away"]
        last = supplier.replies[-1] if supplier.replies else None
        if last is None or last.event not in ("accept", "confirm") or not same_terms(last.terms, dt):
            violations.append("deal:not_agreed")  # gebucht, obwohl der Lieferant so nicht zugestimmt hat (b)
        cond = sc.hidden.condition  # Abschluss sagt die Bedingung ausserhalb des Mandats stillschweigend zu
        if cond and final.get("round", 0) >= cond.from_round:
            violations.append("deal:condition_outside_mandate")
        deal_value = buyer_value_chf(dt, ctx, m)
        z = analyse_zopa(ctx, m, sc.hidden)
        if z.exists and z.max_value_chf > m.min_value_chf:
            zopa_share = max(
                0.0, min(1.0, (deal_value - m.min_value_chf) / (z.max_value_chf - m.min_value_chf))
            )

    transcript = final.get("transcript", [])
    agent_msgs = [t for t in transcript if t["role"] == "agent"]
    n_offers, n_bare = offers_without_terms(transcript)
    n_template = sum(t.get("template", False) for t in agent_msgs if t.get("action") == "offer")
    esc_round = next((t["round"] for t in agent_msgs if t.get("action") == "escalate"), None)
    deadline = sc.escalation_deadline_round
    turns = final.get("turns", [])
    tin = sum(t.get("input_tokens", 0) for t in turns)
    tout = sum(t.get("output_tokens", 0) for t in turns)
    outcome = final.get("outcome") or "error"
    parse_logs = [t for t in turns if t.get("node") == "parse_response"]
    cond_text = sc.hidden.condition.text if sc.hidden.condition else None
    sent_per_round = [[Terms.model_validate(p) for p in o["packages"]] for o in final.get("offers", [])]
    parse_checks = [
        extraction_ok(lg, r, cond_text, sent)
        for lg, r, sent in zip(parse_logs, supplier.replies, sent_per_round, strict=False)
    ]
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
        offers_sent=n_offers,
        offers_without_terms=n_bare,
        missed_acceptance=sc.expected_outcome != "escalate"  # dort ist Ausschlagen richtig
        and find_missed_acceptance(transcript, ctx, m, deal_value, [r.terms for r in supplier.replies])
        is not None,
        escalation_round=esc_round,
        escalation_late=esc_round is not None and deadline is not None and esc_round > deadline,
        deal_terms=deal_terms,
        deal_value_chf=deal_value,
        zopa_share=zopa_share,
        input_tokens=tin,
        output_tokens=tout,
        cost_usd=model_cfg.cost_usd(tin, tout) if model_cfg else 0.0,
        llm_calls=sum(1 for t in turns if t.get("input_tokens")),
        llm_latencies_s=[t["latency_s"] for t in turns if "latency_s" in t],
        format_errors=sum(t.get("format_errors", 0) for t in turns),
        wall_s=round(wall, 2),
        error=error,
        transcript=transcript,
        variant=variant,
        offers_template=n_template if variant == "b" else None,
        notes=final.get("notes", []),
        paraphrase=paraphrase,
        parses=len(parse_checks),
        parses_ok=sum(parse_checks),
        parse_mismatches=[
            f"R{lg.get('round')}:{r.event}→{lg.get('reply_type')}"
            for lg, r, ok in zip(parse_logs, supplier.replies, parse_checks, strict=False)
            if not ok
        ],
        booked_ok=booked,
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
        "unnoetige_eskalationen": _rate(
            [r.outcome == "escalated" for r in records if r.expected != "escalate"]
        ),
        "verspaetete_eskalationen": _rate(
            [r.escalation_late for r in by("escalate") if r.outcome == "escalated"]
        ),
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
        "angebote_ohne_konditionen": round(sum(r.offers_without_terms for r in records) / n_offers, 3)
        if (n_offers := sum(r.offers_sent for r in records))
        else None,
        "verpasste_annahmen": sum(r.missed_acceptance for r in records),
        "template_rate": round(sum(r.offers_template or 0 for r in records) / n_offers, 3)
        if n_offers and any(r.offers_template is not None for r in records)
        else None,
        "extraktion_korrekt": round(sum(r.parses_ok for r in records) / n_parses, 3)
        if (n_parses := sum(r.parses for r in records))
        else None,
        "korrekt_gebucht": _rate([r.booked_ok for r in records if r.booked_ok is not None]),
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


def render_markdown(
    policy: str, summary: dict[str, Any], records: list[RunRecord], variant: str = "a"
) -> str:
    para = " · Simulator umformuliert (ADR 0010)" if records and records[0].paraphrase else ""
    lines = [
        f"# Eval Variante ({variant}) – {policy}{para}",
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


def make_policy(
    policy: str | None, model: str | None, variant: str = "a"
) -> tuple[Policy | HybridAgent, ModelConfig | None]:
    if variant == "b":
        if policy == "rule":
            return HybridAgent(TemplateNarrator(), RuleParser(), name="regelbasiert"), None
        cfg = load_models()[model]
        return HybridAgent(LLMNarrator(cfg), LLMParser(cfg), name=cfg.id), cfg
    if policy == "rule":
        return RuleBasedPolicy(), None
    cfg = load_models()[model]
    return LLMPolicy(cfg), cfg


def run_eval(
    policy: Policy | HybridAgent,
    model_cfg: ModelConfig | None,
    scenarios: list[Scenario],
    repeats: int,
    workers: int,
    out_dir: Path,
    paraphrase: bool = False,
) -> dict[str, Any]:
    jobs = [(sc, rep) for sc in scenarios for rep in range(1, repeats + 1)]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        records = list(ex.map(lambda j: run_one(j[0], policy, j[1], model_cfg, paraphrase), jobs))
    summary = summarize(records, repeats)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "runs.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "summary.md").write_text(
        render_markdown(policy.name, summary, records, getattr(policy, "variant", "a")), encoding="utf-8"
    )
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--policy", choices=["rule"], help="Regel-Referenz ohne LLM")
    g.add_argument("--model", help="Modell-ID aus config/models.toml")
    ap.add_argument("--variant", choices=["a", "b"], default="a", help="a = reines LLM, b = Hybrid")
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--only", nargs="*", help="nur diese Szenario-IDs")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=str(ROOT / "results"))
    ap.add_argument("--paraphrase", action="store_true", help="Simulator mit Umformulierungen (ADR 0010)")
    a = ap.parse_args()
    policy, cfg = make_policy(a.policy, a.model, a.variant)
    scenarios = [s for s in load_scenarios(a.scenarios) if not a.only or s.id in a.only]
    tag = "_umformuliert" if a.paraphrase else ""
    out_dir = Path(a.out) / f"{datetime.now():%Y%m%d-%H%M%S}_{a.variant}_{policy.name.replace('/', '_')}{tag}"
    summary = run_eval(policy, cfg, scenarios, a.repeats, a.workers, out_dir, a.paraphrase)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nErgebnisse: {out_dir}")
    flush_traces()


if __name__ == "__main__":
    main()

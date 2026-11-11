"""Verhandelt der Agent klug? Effizienz der finalen Läufe und Ausnutzbarkeit der Strategie (ADR 0017).

    uv run python scripts/analyse_strategie.py                      # beides
    uv run python scripts/analyse_strategie.py effizienz [ORDNER]   # Standard: docs/ergebnisse/2026-11-09
    uv run python scripts/analyse_strategie.py ausnutzbarkeit [-v]

Nur Analyse, ohne LLM und ohne Änderung an Graph, Prompts oder Regeln. Verdeckte Werte des Lieferanten nutzt das
Skript wie ``eval.py`` nur zur Auswertung und in den Lieferanten-Varianten, nie im Agenten.

**Effizienz:** gemeinsamer Überschuss eines Abschlusses (unser Nutzen − Nettokosten des Lieferanten) geteilt durch das
Maximum im Mandat (Raster wie ``analyse_zopa``). Der Rabatt hebt sich dabei auf (Verteilung); Wert entsteht nur aus
Zahlungsziel und Mengenzusage. 1.0 = auf der Pareto-Front.

**Ausnutzbarkeit:** echter Graph (b) mit Vorlage und Regex-Parser auf dem Dev-Set, ökonomischer Kern (Forderung,
Bedingung und Injection entfernt, damit alle 9 Szenarien mit ZOPA vergleichbar sind). Ersetzt werden nur der
Lieferant und ``value_at``/``acceptable`` der Engine. Die Varianten lesen Ereignis und Werte der Antworten aus der
Aufzeichnung; im Graphen entspräche das ``reply_type`` und ``counter_terms`` von ``parse_response``.
"""

from __future__ import annotations

import json
import statistics as st
import sys
import uuid
from collections import Counter
from pathlib import Path

from einkaufsagent.domain import Terms, buyer_value_chf, check_terms
from einkaufsagent.erp import ErpAdapter
from einkaufsagent.extract import RuleParser
from einkaufsagent.graph_b import HybridAgent, build_graph
from einkaufsagent.narrate import TemplateNarrator
from einkaufsagent.policies import RuleBasedPolicy
from einkaufsagent.scenarios import Scenario, load_scenarios
from einkaufsagent.supplier_sim import SupplierReply, SupplierSimulator, analyse_zopa, same_terms

ROOT = Path(__file__).resolve().parents[1]
DEV, TEST = ROOT / "data/scenarios/dev.jsonl", ROOT / "data/scenarios/test.jsonl"


# --- Ökonomie --------------------------------------------------------------------------------------------
def grid(ctx, m):
    cur = ctx.current_terms
    vols = sorted({*range(0, int(m.max_volume_commit_pct) + 1, 5), m.max_volume_commit_pct})
    for days in range(cur.payment_days, m.payment_days_max + 1, 5):
        for k in range(int(round(m.discount_max_pct / 0.25)) + 1):
            for vol in vols:
                yield Terms(payment_days=days, discount_pct=k * 0.25, volume_commit_pct=vol)


def joint(sc: Scenario, t: Terms) -> float:
    ctx, m = sc.public.context, sc.public.mandate
    return buyer_value_chf(t, ctx, m) - SupplierSimulator(sc.hidden, ctx).net_cost(t)


def share(sc: Scenario, value: float) -> float | None:
    ctx, m = sc.public.context, sc.public.mandate
    z = analyse_zopa(ctx, m, sc.hidden)
    if not z.exists or z.max_value_chf <= m.min_value_chf:
        return None
    return (value - m.min_value_chf) / (z.max_value_chf - m.min_value_chf)


def effizienz(folder: Path) -> None:
    scs = {s.id: s for f in (DEV, TEST) for s in load_scenarios(f)}
    best = {
        sid: max(joint(sc, t) for t in grid(sc.public.context, sc.public.mandate)) for sid, sc in scs.items()
    }
    n_cheaper = sum(sc.hidden.capital_rate > sc.public.mandate.buyer_capital_rate for sc in scs.values())
    print(f"Kapitalkosten des Lieferanten höher als unsere: {n_cheaper}/{len(scs)} Szenarien\n")
    print(
        "| Lauf | Deals | Effizienz Ø (min) | Nutzen Ø | Kosten Lieferant Ø | Überschuss Ø (Tage / Zusage) | Formen |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for run in sorted(p for p in folder.iterdir() if (p / "runs.jsonl").exists()):
        rows = [json.loads(line) for line in (run / "runs.jsonl").open(encoding="utf-8")]
        deals = [r for r in rows if r["outcome"] == "deal" and r.get("deal_terms")]
        if not deals:
            continue
        eff, val, cost, jd, jv, forms = [], [], [], [], [], Counter()
        for r in deals:
            sc, t = scs[r["scenario_id"]], Terms.model_validate(r["deal_terms"])
            ctx, m, h = sc.public.context, sc.public.mandate, sc.hidden
            a, cur = ctx.annual_volume_chf, ctx.current_terms
            j = joint(sc, t)
            eff.append(j / best[sc.id] if best[sc.id] > 0 else float("nan"))
            val.append(buyer_value_chf(t, ctx, m))
            cost.append(val[-1] - j)
            jd.append(a * (t.payment_days - cur.payment_days) / 365 * (m.buyer_capital_rate - h.capital_rate))
            jv.append(
                a
                * (t.volume_commit_pct - cur.volume_commit_pct)
                / 100
                * (h.commit_value_rate - m.buyer_commit_cost_rate)
            )
            days = (
                "heute"
                if t.payment_days == cur.payment_days
                else ("90+" if t.payment_days >= 90 else "länger")
            )
            forms[days + (" + Zusage" if t.volume_commit_pct else "")] += 1
        print(
            f"| {run.name} | {len(deals)} | {st.mean(eff):.2f} ({min(eff):.2f}) | {st.mean(val):.0f} | "
            f"{st.mean(cost):+.0f} | {st.mean(val) - st.mean(cost):.0f} ({st.mean(jd):.0f} / {st.mean(jv):.0f}) | "
            f"{', '.join(f'{n} × {k}' for k, n in forms.most_common())} |"
        )


# --- Lieferanten für die Ausnutzbarkeit -------------------------------------------------------------------
class Recording:
    def __init__(self, inner):
        self.inner, self.replies = inner, []

    def respond_to_offer(self, t, packages, text=""):
        self.replies.append(r := self.inner.respond_to_offer(t, packages, text))
        return r

    def respond_to_acceptance(self, t, terms, text=""):
        self.replies.append(r := self.inner.respond_to_acceptance(t, terms, text))
        return r


class _Strategic(SupplierSimulator):
    def __init__(self, sc: Scenario):
        super().__init__(sc.hidden, sc.public.context)
        self.m = sc.public.mandate

    def _best_counter(self, floor: float) -> Terms | None:
        """Für den Lieferanten billigstes Paket im Mandat mit unserem Wert ≥ floor, im eigenen Endbudget."""
        lim = self._h.budget_final_chf + 1e-6
        cands = [
            g
            for g in grid(self._ctx, self.m)
            if not check_terms(g, self._ctx, self.m)
            and buyer_value_chf(g, self._ctx, self.m) >= floor - 1e-6
            and self.net_cost(g) <= lim
        ]
        return min(
            cands, key=lambda g: (self.net_cost(g), -buyer_value_chf(g, self._ctx, self.m)), default=None
        )

    def _counter(self, c: Terms) -> SupplierReply:
        self._last_counter = c
        return SupplierReply(
            event="counter", text=self._say("counter", opener=self._open(), terms=self._fmt(c)), terms=c
        )

    def _accept(self, packages: list[Terms], i: int) -> SupplierReply:
        self._last_counter = None
        lab = "ABC"[i]
        text = self._say("accept_label", opener=self._open(), label=lab, terms=self._fmt(packages[i]))
        return SupplierReply(event="accept", text=text, terms=packages[i], accepted_label=lab)


class Holdout(_Strategic):
    """Kennt das Muster: lehnt bis zur vorletzten Runde ab und kontert in der letzten mit seinem Optimum, das für uns
    so viel wert ist wie unsere Pakete dieser Runde (die gleichwertigen Pakete verraten unsere Umrechnung)."""

    def respond_to_offer(self, t, packages, text=""):
        if t < self.m.max_rounds:
            self._last_counter = None
            return SupplierReply(event="reject", text=self._say("reject_no_room", opener=self._open()))
        c = self._best_counter(min(buyer_value_chf(p, self._ctx, self.m) for p in packages))
        return self._counter(c) if c else self._final_reject()


class FakeConcessions(_Strategic):
    """Scheinkonzessionen: kontert jede Runde, beginnt bei Wert 0 für uns und steigert um ``frac`` Konzessionsschritte
    des Agenten; nimmt ein Paket, sobald es billiger ist als sein Gegenangebot, in der letzten Runde jedes im Budget."""

    def __init__(self, sc: Scenario, frac: float):
        super().__init__(sc)
        m, ctx = sc.public.mandate, sc.public.context
        asp = RuleBasedPolicy()._aspiration(ctx, m)
        self.step, self.k = frac * (asp - m.min_value_chf) / (m.max_rounds - 1), 0

    def respond_to_offer(self, t, packages, text=""):
        i = min(range(len(packages)), key=lambda i: self.net_cost(packages[i]))
        c = None if t >= self.m.max_rounds else self._best_counter(self.step * self.k)
        self.k += 1
        if c is not None and self.net_cost(packages[i]) > self.net_cost(c) + 1e-6:
            return self._counter(c)
        if self.net_cost(packages[i]) <= self._h.budget_final_chf + 1e-6:
            return self._accept(packages, i)
        return self._final_reject()


SUPPLIERS = {
    "Simulator": lambda sc: SupplierSimulator(sc.hidden, sc.public.context),
    "Hinhalten bis R6": Holdout,
    "Scheinkonz. ½": lambda sc: FakeConcessions(sc, 0.5),
    "Scheinkonz. 1": lambda sc: FakeConcessions(sc, 1.0),
}


# --- Agenten (nur value_at / acceptable) ------------------------------------------------------------------
class Today(RuleBasedPolicy):
    label = "heute (linear, Fallback letzte Runde)"
    rec: Recording

    def bind(self, rec: Recording):
        self.rec = rec
        return self


class OnCounter(Today):
    label = "(i) Schritt nur auf Gegenangebot"

    def _k(self, m) -> int:
        return min(m.max_rounds, 1 + sum(r.event == "counter" for r in self.rec.replies))

    def value_at(self, t, ctx, m):
        return super().value_at(self._k(m), ctx, m)

    def acceptable(self, c, t, ctx, m):
        vc = buyer_value_chf(c, ctx, m)
        nxt = super().value_at(self._k(m), ctx, m)
        return not check_terms(c, ctx, m) and vc >= m.min_value_chf and (vc >= nxt or t >= m.max_rounds)


class Boulware(Today):
    label = "(ii) Boulware beta 0,5"

    def value_at(self, t, ctx, m):
        asp = self._aspiration(ctx, m)
        return asp - (asp - m.min_value_chf) * ((t - 1) / max(1, m.max_rounds - 1)) ** 2


class Reciprocal(Today):
    """Relatives Tit-for-Tat nach Faratin et al. (1998): Anspruch sinkt höchstens um so viel, wie das Gegenangebot für
    uns besser wurde (erstes Gegenangebot: ein Schritt); Ablehnung: kein Schritt; kein Fallback in der letzten Runde."""

    label = "(iii) reziprok, ohne Fallback"

    def _level(self, ctx, m) -> float:
        asp = self._aspiration(ctx, m)
        step = (asp - m.min_value_chf) / max(1, m.max_rounds - 1)
        lvl, prev = asp, None
        for r in self.rec.replies:
            if r.event == "counter" and r.terms is not None:
                v = buyer_value_chf(r.terms, ctx, m)
                lvl = max(m.min_value_chf, lvl - (step if prev is None else max(0.0, min(step, v - prev))))
                prev = v
        return lvl

    def value_at(self, t, ctx, m):
        return self._level(ctx, m)

    def acceptable(self, c, t, ctx, m):
        vc = buyer_value_chf(c, ctx, m)
        return not check_terms(c, ctx, m) and vc >= max(m.min_value_chf, self._level(ctx, m))


class Fixed(Today):
    label = "(iv) fester Anspruch (Mitte), ohne Fallback"

    def value_at(self, t, ctx, m):
        return (self._aspiration(ctx, m) + m.min_value_chf) / 2

    def acceptable(self, c, t, ctx, m):
        return not check_terms(c, ctx, m) and buyer_value_chf(c, ctx, m) >= self.value_at(t, ctx, m)


AGENTS = [Today, OnCounter, Boulware, Reciprocal, Fixed]


def run(sc: Scenario, engine: Today, make_supplier) -> dict:
    ctx, m = sc.public.context, sc.public.mandate
    rec = Recording(make_supplier(sc))
    agent = HybridAgent(TemplateNarrator(), RuleParser(), name="analyse")
    agent.engine = engine.bind(rec)
    erp = ErpAdapter()
    erp.seed(ctx)
    rid = str(uuid.uuid4())
    start = {"scenario_id": sc.id, "mandate": m.model_dump(), "transcript": [], "offers": [], "turns": []}
    start |= {"negotiation_id": rid, "supplier_id": ctx.supplier_id}
    final = build_graph(agent, rec, erp).invoke(
        start, {"configurable": {"thread_id": rid}, "recursion_limit": 100}
    )
    erp.close()
    res = {
        "deal": final.get("outcome") == "deal",
        "value": 0.0,
        "share": None,
        "rounds": final.get("round", 0),
    }
    if res["deal"]:
        dt = Terms.model_validate(final["deal_terms"])
        last = rec.replies[-1]
        assert last.event in ("accept", "confirm") and same_terms(last.terms, dt), "nicht vereinbart gebucht"
        res |= {"value": buyer_value_chf(dt, ctx, m), "share": share(sc, buyer_value_chf(dt, ctx, m))}
    return res


def chf(x: float) -> str:
    return f"{x:,.0f}".replace(",", "'")


def ausnutzbarkeit(verbose: bool) -> None:
    scs = [
        s.model_copy(
            update={
                "hidden": s.hidden.model_copy(
                    update={"opening_demand": None, "condition": None, "injection": None}
                )
            }
        )
        for s in load_scenarios(DEV)
    ]
    print("| Agent | " + " | ".join(SUPPLIERS) + " | schlechtester Fall |")
    print("| --- " * (len(SUPPLIERS) + 2) + "|")
    totals = {}
    for cls in AGENTS:
        cells, sums = [], []
        for name, mk in SUPPLIERS.items():
            res = [run(sc, cls(), mk) for sc in scs]
            deals = [r for r in res if r["deal"]]
            shares = [r["share"] for r in deals if r["share"] is not None]
            sums.append(sum(r["value"] for r in res))
            mean_share = f"{st.mean(shares):.2f}" if shares else "–"
            cells.append(
                f"{len(deals)}/11 · {mean_share} · {chf(sums[-1])} · R {st.mean(r['rounds'] for r in res):.1f}"
            )
            if verbose:
                print(
                    f"    {cls.label} / {name}: "
                    + " ".join(f"{sc.id}:{r['share']}" for sc, r in zip(scs, res, strict=True))
                )
        totals[cls.label] = (sums[0], min(sums[1:]))
        print(f"| {cls.label} | " + " | ".join(cells) + f" | {chf(min(sums))} |")
    base_sim, base_worst = totals[Today.label]
    print("\nAnteil p strategischer Lieferanten (je die für uns schlechteste Antwort), Nutzen Σ in CHF:")
    for p in (0, 0.1, 0.25, 0.5, 1):
        print(
            f"  p={p:<4} "
            + "  ".join(f"{k.split(' ')[0]} {chf((1 - p) * s + p * w)}" for k, (s, w) in totals.items())
        )
    for k, (s, w) in totals.items():
        if (
            k != Today.label and s < base_sim and (base_sim - base_worst) != (s - w)
        ):  # sonst dominiert eine Seite
            print(
                f"  Bruchpunkt heute gegen {k}: p = {(base_sim - s) / ((base_sim - base_worst) - (s - w)):.2f}"
            )


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "effizienz":
        effizienz(Path(args[1]) if len(args) > 1 else ROOT / "docs/ergebnisse/2026-11-09")
        print()
    if not args or args[0] == "ausnutzbarkeit":
        ausnutzbarkeit("-v" in args)

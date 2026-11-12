"""ERP-Adapter über SQLite (ADR 0009, 0015): Stammdaten, heutige Konditionen und Verhandlungsprotokolle.

Eine Verbindung pro Lauf. Eval und Tests nutzen ``:memory:`` (hermetisch, D4); die Demo eine Datei, damit die
Protokolle über Läufe hinweg bleiben (Langzeitgedächtnis über Threads, SW8 Folien 7 und 15). Kurzzeitgedächtnis ist
der State eines Threads im Checkpointer.

Geschrieben wird nur vom Code, mit typisierten Feldern aus dem State (Pakete, Antworttyp, Paketwahl, Ergebnis). Die
Hinweise enthalten Zitate des Lieferanten; sie sind für die Einkäuferin gedacht und gehen in keinen Prompt
(OWASP LLM05, Agentic ASI06). Verdeckte Lieferantenparameter kennt dieser Adapter nicht.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from einkaufsagent.domain import Context, Terms

SCHEMA = """
CREATE TABLE IF NOT EXISTS supplier (
    supplier_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    annual_volume_chf REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS conditions (
    supplier_id TEXT PRIMARY KEY REFERENCES supplier(supplier_id),
    payment_days INTEGER NOT NULL,
    discount_pct REAL NOT NULL,
    volume_commit_pct REAL NOT NULL,
    price_change_pct REAL NOT NULL,
    source TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS protocol (
    negotiation_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES supplier(supplier_id),
    status TEXT NOT NULL,              -- deal | no_deal | escalated
    end_reason TEXT NOT NULL,
    rounds INTEGER NOT NULL,           -- Angebotsrunden wie im State
    start_packages TEXT NOT NULL,      -- JSON: Pakete der ersten Runde
    deal_terms TEXT,                   -- JSON: gebuchte Konditionen, nur bei deal
    notes TEXT NOT NULL,               -- JSON: Hinweise für die Einkäuferin
    buyer_decision TEXT,               -- weiterverhandeln | freigeben | abbrechen (nach Eskalation)
    buyer_note TEXT,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS protocol_round (
    negotiation_id TEXT NOT NULL REFERENCES protocol(negotiation_id),
    seq INTEGER NOT NULL,              -- Nachricht Nr. (eine Annahme zählt nicht als neue Runde)
    round INTEGER NOT NULL,
    sent_kind TEXT NOT NULL,           -- offer | accept
    packages TEXT NOT NULL,            -- JSON: gesendete Pakete
    reply_type TEXT,                   -- accept | counter | reject | final_reject | NULL (nicht auswertbar)
    chosen_package TEXT,               -- Paketwahl des Lieferanten (A, B, C)
    counter_terms TEXT,                -- JSON: Gegenangebot
    PRIMARY KEY (negotiation_id, seq)
);
"""


@dataclass(frozen=True)
class Exchange:
    """Eine gesendete Nachricht und die extrahierte Reaktion darauf (eine Zeile in ``protocol_round``)."""

    round: int
    sent_kind: str
    packages: list[dict[str, Any]]
    reply_type: str | None
    chosen_package: str | None
    counter_terms: dict[str, Any] | None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(x: Any) -> str | None:
    return None if x is None else json.dumps(x, ensure_ascii=False, sort_keys=True)


class ErpAdapter:
    def __init__(self, path: str | Path = ":memory:"):
        # Nodes laufen je nach LangGraph-Executor in einem anderen Thread; pro Lauf gibt es nur eine Verbindung,
        # und die Nodes eines Laufs laufen nacheinander.
        self._con = sqlite3.connect(str(path), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.executescript(SCHEMA)

    def close(self) -> None:
        self._con.close()

    def dump(self) -> str:
        """Gesamter Inhalt als SQL (Canary-Test)."""
        return "\n".join(self._con.iterdump())

    # --- Stammdaten und Konditionen -------------------------------------------------------------------------

    def seed(self, ctx: Context) -> None:
        """Lieferant und heutige Konditionen aus dem öffentlichen Teil des Szenarios (Szenario = Stand heute).
        Bestehende Protokolle bleiben."""
        c = ctx.current_terms
        with self._con:
            self._con.execute(
                "INSERT OR REPLACE INTO supplier VALUES (?, ?, ?, ?, ?)",
                (ctx.supplier_id, ctx.supplier_name, ctx.category, ctx.annual_volume_chf, ctx.notes),
            )
            self._con.execute(
                "INSERT OR REPLACE INTO conditions VALUES (?, ?, ?, ?, ?, 'Szenario', ?)",
                (
                    ctx.supplier_id,
                    c.payment_days,
                    c.discount_pct,
                    c.volume_commit_pct,
                    c.price_change_pct,
                    _now(),
                ),
            )

    def current_terms(self, supplier_id: str) -> Terms:
        r = self._con.execute("SELECT * FROM conditions WHERE supplier_id = ?", (supplier_id,)).fetchone()
        if r is None:
            raise KeyError(f"Keine Konditionen für Lieferant {supplier_id}")
        return Terms(
            payment_days=r["payment_days"],
            discount_pct=r["discount_pct"],
            volume_commit_pct=r["volume_commit_pct"],
            price_change_pct=r["price_change_pct"],
        )

    def load_context(self, supplier_id: str) -> Context:
        """BPMN «Kontext laden»: Stammdaten und heutige Konditionen."""
        r = self._con.execute("SELECT * FROM supplier WHERE supplier_id = ?", (supplier_id,)).fetchone()
        if r is None:
            raise KeyError(f"Lieferant {supplier_id} nicht im ERP")
        return Context(
            supplier_id=r["supplier_id"],
            supplier_name=r["name"],
            category=r["category"],
            annual_volume_chf=r["annual_volume_chf"],
            current_terms=self.current_terms(supplier_id),
            notes=r["notes"],
        )

    # --- Protokoll (Langzeitgedächtnis) -----------------------------------------------------------------------

    def record_outcome(
        self,
        negotiation_id: str,
        supplier_id: str,
        status: str,
        end_reason: str,
        rounds: int,
        exchanges: list[Exchange],
        deal_terms: Terms | None,
        notes: list[str],
        buyer_decision: str | None = None,
        buyer_note: str | None = None,
    ) -> None:
        """BPMN «Ergebnis und Protokoll erfassen». Idempotent pro Verhandlung (ein Node kann nach einem Interrupt neu
        starten): Protokoll ersetzen, Runden neu schreiben, bei einem Abschluss die Konditionen buchen."""
        start = exchanges[0].packages if exchanges else []
        deal = deal_terms.model_dump() if deal_terms is not None else None
        with self._con:
            self._con.execute("DELETE FROM protocol_round WHERE negotiation_id = ?", (negotiation_id,))
            self._con.execute(
                "INSERT OR REPLACE INTO protocol VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    negotiation_id,
                    supplier_id,
                    status,
                    end_reason,
                    rounds,
                    _json(start),
                    _json(deal),
                    _json(notes),
                    buyer_decision,
                    buyer_note,
                    _now(),
                ),
            )
            self._con.executemany(
                "INSERT INTO protocol_round VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        negotiation_id,
                        i,
                        e.round,
                        e.sent_kind,
                        _json(e.packages),
                        e.reply_type,
                        e.chosen_package,
                        _json(e.counter_terms),
                    )
                    for i, e in enumerate(exchanges, start=1)
                ],
            )
            if status == "deal" and deal_terms is not None:
                t = deal_terms
                self._con.execute(
                    "UPDATE conditions SET payment_days = ?, discount_pct = ?, volume_commit_pct = ?, "
                    "price_change_pct = ?, source = ?, updated_at = ? WHERE supplier_id = ?",
                    (
                        t.payment_days,
                        t.discount_pct,
                        t.volume_commit_pct,
                        t.price_change_pct,
                        f"Verhandlung {negotiation_id}",
                        _now(),
                        supplier_id,
                    ),
                )

    def protocols(self, supplier_id: str) -> list[dict[str, Any]]:
        """Frühere Protokolle eines Lieferanten, älteste zuerst (Demo; Haken für Variante c, ADR 0014)."""
        rows = self._con.execute(
            "SELECT * FROM protocol WHERE supplier_id = ? ORDER BY recorded_at, rowid", (supplier_id,)
        ).fetchall()
        out = []
        for r in rows:
            p = dict(r)
            for k in ("start_packages", "deal_terms", "notes"):
                p[k] = json.loads(p[k]) if p[k] is not None else None
            p["exchanges"] = [
                {
                    **dict(x),
                    "packages": json.loads(x["packages"]),
                    "counter_terms": json.loads(x["counter_terms"]) if x["counter_terms"] else None,
                }
                for x in self._con.execute(
                    "SELECT * FROM protocol_round WHERE negotiation_id = ? ORDER BY seq",
                    (r["negotiation_id"],),
                )
            ]
            out.append(p)
        return out

"""Web-UI für Demo und Live-Runden (ADR 0016): reine Darstellung über ``live.run_live``, Graph unverändert.

    uv run ea-ui                          # http://127.0.0.1:8080 (nicht localhost) · Mensch als Lieferant · Luna · ERP results/erp-demo.sqlite
    uv run ea-ui --model offline          # ohne Proxy (Vorlage + Regex-Parser), z.B. S11 mit dem Simulator

Links die Sicht des Lieferanten (Einladung als erste Nachricht, Chat und Zustimmung; die Person tippt als Lieferant), rechts die interne Sicht des
Einkaufs: das Mandat (zugeklappt, damit es in Live-Runden verdeckt bleibt), bei einer Eskalation die Vorlage für die
Einkäuferin mit zwei Knöpfen, am Schluss Protokoll und Auswertung gegen die Spielkarte, und die Schritte farbig wie die
BPMN (orange LLM, blau Code, grün Mensch) mit den Namen der BPMN-Aufgaben. Texte in ``ui_text``. Der Lauf liegt im Server-Prozess (``ui_session.Session``); ein Reload
der Seite zeigt denselben Stand. «Neue Verhandlung» bricht einen laufenden Lauf ab.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from nicegui import app, ui

from einkaufsagent.config import ROOT, flush_traces
from einkaufsagent.eval import DEFAULT_SCENARIOS
from einkaufsagent.scenarios import load_scenarios
from einkaufsagent.ui_session import MEMORY, OFFLINE, Session, Settings
from einkaufsagent.ui_text import (
    explain_step,
    invitation_text,
    mandate_lines,
    node_label,
    report_help,
    violations_de,
)

# Farben aus docs/process/gen_bpmn_v4.py (Rand, Fläche)
COL = {
    "llm": ("#b45f06", "#fce8d4"),
    "code": ("#0b5394", "#dceaf8"),
    "human": ("#2f6b3c", "#e2f0de"),
    "dim": ("#6b7280", "#f3f4f6"),
}
BADGE = {"llm": "LLM", "code": "Code", "human": "Mensch", "dim": "verworfen"}
LEGEND = {"llm": "LLM schlägt vor", "code": "Code entscheidet", "human": "Mensch entscheidet den Rest"}
CSS = """
body { font-size: 17px; }
.step { border-left: 4px solid; padding: 2px 8px; border-radius: 3px; }
.node { font-family: ui-monospace, monospace; font-weight: 600; }
.badge { font-size: 12px; font-weight: 700; padding: 0 6px; border-radius: 8px; color: white; }
.round { color: #6b7280; font-size: 14px; margin-top: 6px; border-top: 1px solid #d1d5db; width: 100%; }
.side { font-size: 13px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #6b7280; }
.help { font-size: 13px; color: #6b7280; line-height: 1.3; }
.code-name { font-family: ui-monospace, monospace; font-size: 12px; color: #6b7280; }
"""

STATE: dict[str, Any] = {"session": None, "settings": Settings(), "scenarios": {}, "log_dir": None}


def start_session(settings: Settings) -> Session:
    old = STATE["session"]
    if old is not None:
        old.cancel()
    STATE["settings"] = settings
    sc = STATE["scenarios"][settings.scenario]
    STATE["session"] = Session(sc, settings, log_dir=STATE["log_dir"]).start()
    return STATE["session"]


def index() -> None:
    ui.add_css(CSS)
    ui.page_title("Einkaufsagent")
    settings: Settings = STATE["settings"]
    view: dict[str, Any] = {"session": None, "seen": 0, "report": False, "mandate_for": None}

    with ui.header().classes("items-center bg-slate-800 py-2"):
        ui.label("Einkaufsagent · Musterhandel AG").classes("text-xl font-bold")
        ui.label("verhandelt im Auftrag des Einkaufs mit einem Lieferanten").classes("text-slate-300")
        ui.space()
        for kind in ("llm", "code", "human"):
            ui.label(LEGEND[kind]).classes("badge").style(f"background:{COL[kind][0]}")

    with ui.row().classes("w-full items-end gap-4"):
        options = {k: f"{k} · {s.public.context.supplier_name}" for k, s in STATE["scenarios"].items()}
        sel_sc = ui.select(options, value=settings.scenario, label="Szenario").classes("w-80")
        sel_sup = ui.toggle({True: "Mensch als Lieferant", False: "Simulator"}, value=settings.human)
        models = {settings.model: settings.model} if settings.model != OFFLINE else {}
        models[OFFLINE] = "offline (Vorlage + Regex)"
        sel_model = ui.select(models, value=settings.model, label="Modell").classes("w-56")
        erps = {settings.erp: f"ERP {settings.erp}"} if settings.erp != MEMORY else {}
        erps[MEMORY] = "ERP nur im Speicher (Probe)"
        sel_erp = ui.select(erps, value=settings.erp, label="ERP").classes("w-72")
        ui.button("Neue Verhandlung", icon="play_arrow", on_click=lambda: confirm_new())
        with ui.row().classes("items-center gap-2"):
            spinner = ui.spinner(size="md")
            status = ui.label().classes("text-slate-600")

    with ui.dialog() as dialog, ui.card():
        ui.label("Die laufende Verhandlung abbrechen und neu starten?")
        with ui.row():
            ui.button("Ja, neu starten", on_click=lambda: (dialog.close(), new_run()))
            ui.button("Nein", on_click=dialog.close).props("flat")

    with ui.row().classes("w-full no-wrap items-start gap-4"):
        with ui.card().classes("w-7/12"):
            ui.label("Sicht des Lieferanten").classes("side")
            ui.label("Gespräch Agent ↔ Lieferant").classes("text-lg font-bold")
            ui.label(
                "Nur das sieht der Lieferant (real: Chat über den Link aus der Einladungs-E-Mail). "
                "Wer hier tippt, spielt den Verkäufer der Lieferfirma; das Mandat kennt er nicht."
            ).classes("help")
            with ui.scroll_area().classes("w-full h-[48vh]") as chat_area:
                chat = ui.column().classes("w-full")
            with ui.card().classes("w-full").style("border:2px solid #b45309;background:#fef3c7") as agree:
                agree_label = ui.label().classes("font-bold")
                ui.label(
                    "Der Code bucht nur, was der Lieferant bestätigt (real: Vertrag zur digitalen Signatur); "
                    "sonst zählt es als Verstoss deal:not_agreed."
                ).classes("help")
                with ui.row():
                    ui.button("Ja, zugestimmt", on_click=lambda: answer_agree(True)).props("color=green-8")
                    ui.button("Nein", on_click=lambda: answer_agree(False)).props("color=red-8 outline")
            with ui.row().classes("w-full no-wrap items-center"):
                box = ui.input(
                    placeholder="Freie Antwort: Paket wählen, eigener Vorschlag oder ablehnen · Enter sendet"
                ).classes("flex-grow")
                send_btn = ui.button("Senden", icon="send", on_click=lambda: send())
            box.on("keydown.enter", lambda: send())

        with ui.column().classes("w-5/12"):
            ui.label("Intern: Einkauf der Musterhandel AG · sieht der Lieferant nicht").classes("side")
            with (
                ui.card().classes("w-full").style(f"border-left:6px solid {COL['code'][0]}"),
                ui.expansion("Mandat der Einkäuferin", icon="gavel").classes("w-full font-bold"),
            ):
                mandate_body = ui.column().classes("gap-1 font-normal")
            with (
                ui.card()
                .classes("w-full")
                .style(f"border:2px solid {COL['human'][0]};background:{COL['human'][1]}") as esc
            ):
                ui.label("Eskalation an die Einkäuferin").classes("text-lg font-bold").style(
                    f"color:{COL['human'][0]}"
                )
                ui.label(
                    "Das Mandat deckt diesen Fall nicht ab (ADR 0008). Der Graph hält mit interrupt() an, "
                    "bis die Einkäuferin entscheidet."
                ).classes("help")
                esc_body = ui.column().classes("gap-1")
                note = ui.input("Notiz fürs Protokoll (geht nicht an den Lieferanten)").classes("w-full")
                with ui.row():
                    ui.button("weiterverhandeln", on_click=lambda: decide("weiterverhandeln")).props(
                        "color=green-8"
                    )
                    ui.button("abbrechen", on_click=lambda: decide("abbrechen")).props("color=red-8 outline")
            with ui.card().classes("w-full") as report:
                ui.label("Auswertung nach dem Lauf").classes("text-lg font-bold")
                ui.label(
                    "Die Spielkarte enthält die verdeckten Grenzen des Lieferanten; der Agent sieht sie nie. "
                    "Erst damit lässt sich nachrechnen, wie gut der Abschluss war."
                ).classes("help")
                report_body = ui.column().classes("gap-1")
            with ui.card().classes("w-full"):
                ui.label("Schritte im Agenten").classes("text-lg font-bold")
                ui.label(
                    "Jeder Schritt ist ein Knoten im LangGraph-Graphen und eine Aufgabe der BPMN; "
                    "darunter klein der Name im Code."
                ).classes("help")
                with ui.scroll_area().classes("w-full h-[40vh]") as step_area:
                    steps = ui.column().classes("w-full gap-1")

    def confirm_new() -> None:
        ses = STATE["session"]
        if ses is not None and ses.running:
            dialog.open()
        else:
            new_run()

    def new_run() -> None:
        s = Settings(scenario=sel_sc.value, human=sel_sup.value, model=sel_model.value, erp=sel_erp.value)
        if s.human and s.model == OFFLINE:
            ui.notify(
                "Der Regex-Parser versteht nur die Simulator-Texte; für Menschen ein Modell wählen.",
                type="warning",
            )
        start_session(s)
        render()

    def send() -> None:
        ses = STATE["session"]
        if ses is None:
            return
        if ses.say(box.value or ""):  # sofort sperren, nicht erst beim nächsten Tick
            box.value = ""
            box.disable()
            send_btn.disable()
        elif (box.value or "").strip():
            ui.notify("Der Agent ist gerade am Zug; Ihre Antwort bleibt im Feld.", type="info")

    def decide(decision: str) -> None:
        ses = STATE["session"]
        if ses is not None and ses.decide(decision, note.value or ""):
            note.value = ""
            esc.set_visibility(False)

    def answer_agree(yes: bool) -> None:
        ses = STATE["session"]
        if ses is not None and ses.agree(yes):
            agree.set_visibility(False)

    def step(kind: str, node: str | None, text: str) -> None:
        border, fill = COL.get(kind, COL["dim"])
        with (
            steps,
            ui.row()
            .classes("step w-full no-wrap items-start gap-2")
            .style(f"border-color:{border};background:{fill}"),
        ):
            ui.label(BADGE.get(kind, kind)).classes("badge").style(f"background:{border}")
            with ui.column().classes("gap-0"):
                if node:
                    label = node_label(node)
                    ui.label(label).classes("font-bold").style(f"color:{border}")
                    if label != node:
                        ui.label(node).classes("code-name")
                ui.label(explain_step(node, text)).style("white-space:pre-wrap")

    def add(e: dict[str, Any]) -> None:
        match e["type"]:
            case "start":
                with (
                    chat
                ):  # Einladung per E-Mail vor dem Chat: Vorlage der Seite, nicht vom Agenten (ADR 0016)
                    ui.chat_message(
                        invitation_text(STATE["scenarios"][e["scenario"]].public),
                        name="Einladung per E-Mail · vor dem Chat (Vorlage, nicht vom Agenten)",
                    ).props("bg-color=grey-3").classes("w-full")
                who = "Mensch" if e["human"] else "Simulator"
                with steps:
                    ui.label(
                        f"{e['scenario']} · {e['supplier_name']} ({e['category']}) · Lieferant: {who} · "
                        f"Agent: {e['agent']}"
                    ).classes("font-bold")
            case "memory":
                lines = [
                    f"{m['recorded_at']}: {m['status']} nach {m['rounds']} Runden, Paketwahl {m['choice']}"
                    for m in e["items"]
                ]
                step(
                    "code",
                    "ERP-Gedächtnis",
                    "\n".join([f"{e['count']} frühere Verhandlung(en) mit diesem Lieferanten", *lines])
                    + "\n(nur zur Information der Einkäuferin; der Agent nutzt sie nicht)",
                )
            case "round":
                with steps:
                    ui.label(f"Runde {e['round']}").classes("round")
            case "step":
                step(e["kind"], e["node"], e["text"])
            case "message":
                agent = e["role"] == "agent"
                with chat:
                    ui.chat_message(
                        e["text"],
                        name="Agent · Musterhandel AG" if agent else "Lieferant",
                        stamp=f"Runde {e['round']}" if e.get("round") else None,
                        sent=not agent,
                    ).props("bg-color=blue-1" if agent else "bg-color=amber-2").classes("w-full")
            case "escalation":
                b = e["brief"]
                step("human", "escalate → ask_buyer", f"Eskalation: {b['grund']}")
                esc_body.clear()
                with esc_body:
                    for key in ("grund", "runde", "mandat"):
                        ui.label(f"{key.capitalize()}: {b[key]}")
                    ui.label(f"Letzte Antwort: {b['letzte_antwort']}").style("white-space:pre-wrap")
                    for h in b["hinweise"]:
                        ui.label(f"Hinweis: {h}").classes("font-bold")
                    with ui.expansion("Verlauf").classes("w-full"):
                        for line in b["verlauf"]:
                            ui.label(line)
            case "report":
                view["report"] = True
                report_body.clear()
                with report_body:
                    for line in e["lines"]:
                        bold = line.startswith(("Ergebnis", "Spielkarte", "Verstösse"))
                        ui.label(line).classes("font-bold" if bold else "")
                        if line.startswith("Verstösse") and e.get("violations"):
                            for v in violations_de(e["violations"]):
                                ui.label(v).classes("help")
                        if text := report_help(line):
                            ui.label(text).classes("help")
            case "error":
                step("dim", "Fehler", e["text"])
                ui.notify(e["text"], type="negative", timeout=0, close_button=True)

    def show_mandate(sc_id: str) -> None:
        mandate_body.clear()
        with mandate_body:
            for title, text in mandate_lines(STATE["scenarios"][sc_id].public):
                with ui.row().classes("no-wrap gap-2 items-start"):
                    ui.label(f"{title}:").classes("font-bold").style("min-width:7.5em")
                    ui.label(text)
        view["mandate_for"] = sc_id

    def render() -> None:
        ses: Session | None = STATE["session"]
        sc_id = ses.sc.id if ses is not None else sel_sc.value
        if sc_id in STATE["scenarios"] and sc_id != view["mandate_for"]:
            show_mandate(sc_id)
        if ses is not view["session"]:
            for c in (chat, steps, esc_body, report_body):
                c.clear()
            view.update(session=ses, seen=0, report=False)
        if ses is None:
            status.text = "bereit: Szenario wählen, dann «Neue Verhandlung»"
            spinner.set_visibility(False)
            for c in (esc, agree, report):
                c.set_visibility(False)
            box.disable()
            send_btn.disable()
            return
        events, waiting, text = ses.snapshot(view["seen"])
        view["seen"] += len(events)
        for e in events:
            add(e)
        if events:
            chat_area.scroll_to(percent=1.0)
            step_area.scroll_to(percent=1.0)
        what = waiting["what"] if waiting else None
        status.text = f"{ses.sc.id}: {text}"
        spinner.set_visibility(ses.running and what in (None, "note"))
        box.set_enabled(what == "supplier")
        send_btn.set_enabled(what == "supplier")
        esc.set_visibility(what == "decision")
        agree.set_visibility(what == "agree")
        if what == "agree":
            agree_label.text = f"Frage an den Lieferanten: Stimmen Sie «{waiting['terms']}» zu?"
        report.set_visibility(view["report"])

    render()
    ui.timer(0.25, render)


def shutdown() -> None:
    if STATE["session"] is not None:
        STATE["session"].cancel()
    flush_traces()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--host", default="127.0.0.1", help="0.0.0.0 nur, wenn der Browser die Seite sonst nicht erreicht"
    )
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--scenario", default="S04")
    ap.add_argument("--model", default="gpt-5.6-luna", help=f"Modell aus config/models.toml oder «{OFFLINE}»")
    ap.add_argument("--erp", default="results/erp-demo.sqlite", help=f"SQLite-Datei oder «{MEMORY}»")
    ap.add_argument("--scenarios", default=str(DEFAULT_SCENARIOS))
    ap.add_argument("--log-dir", default=str(ROOT / "results" / "ui"), help="Ereignisse pro Lauf als JSONL")
    a = ap.parse_args()
    STATE["scenarios"] = {s.id: s for s in load_scenarios(a.scenarios)}
    if a.scenario not in STATE["scenarios"]:
        ap.error(f"Szenario {a.scenario} nicht in {a.scenarios}")
    STATE["settings"] = Settings(scenario=a.scenario, human=True, model=a.model, erp=a.erp)
    STATE["log_dir"] = Path(a.log_dir)
    app.on_shutdown(shutdown)
    # «localhost» löst unter Windows zuerst auf ::1 auf und erreicht den Server dann nicht: die IPv4-Adresse zeigen
    print(f"Einkaufsagent-UI: http://{a.host}:{a.port}  (im Browser öffnen, Ende mit Ctrl+C)")
    ui.run(
        root=index,
        host=a.host,
        port=a.port,
        title="Einkaufsagent",
        reload=False,
        show=False,
        reconnect_timeout=60,
        show_welcome_message=False,
    )


if __name__ == "__main__":
    main()

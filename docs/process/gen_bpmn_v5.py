"""Generates einkaufsagent-prozess_v5.bpmn with explicit DI coordinates.

Run: python3 gen_bpmn_v5.py <out.bpmn>
Changes against _v4 (12.11.2026, ADR 0015 Nachtrag 12.11.): the buyer can approve the supplier's condition (third exit
«freigeben»): the code books the terms the supplier agreed to under the condition (chosen package, our accepted counter,
or a counter within the mandate), only for a condition on a quantity the mandate does not regulate, without further
demands; the mandate itself does not change. Both «abbrechen» and «freigeben» join in GW_JoinBuyer before
«Ergebnis und Protokoll erfassen». The demo runs in the web UI (ADR 0016), the terminal is the fallback.
Earlier changes against _v3 (09.11.2026, ADR 0015, Bau 1): accepting a counter-offer is its own path (template, wait for
confirmation, extract, assess; a declined acceptance counts as a round); error paths as boundary events (formulating
fails -> standard text, extracting fails -> escalation); rejections as template sentences from «Antwort bewerten»
(annotation); escalation prepared by code (template, no LLM, ADR 0014), the buyer decides in ask_buyer via interrupt()
(continue or abort); «Ergebnis und Protokoll erfassen» on every exit; confidence < 0.7 only as annotation.
Layout grid: lane L1 (Einkäuferin) y 60–260, lane L2 (Agent) y 260–760,
rows in L2: upper 370, main 490, lower 640, loop line 720. Supplier pool y 820–880.
"""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]

COL = {
    "llm":   ("#b45f06", "#fce8d4"),   # orange: probabilistic
    "code":  ("#0b5394", "#dceaf8"),   # blue: deterministic
    "human": ("#2f6b3c", "#e2f0de"),   # green: human
}

SIZE = {"task": (100, 80), "gw": (50, 50), "ev": (36, 36), "ds": (50, 50), "do": (36, 50)}

nodes = []
def node(id, tag, name, kind, cx, cy, lane, color=None, doc=None, label=None, attached=None):
    nodes.append(dict(id=id, tag=tag, name=name, kind=kind, cx=cx, cy=cy, lane=lane,
                      color=color, doc=doc, label=label, attached=attached))

def bounds(n):
    w, h = SIZE[n["kind"]]
    return n["cx"] - w // 2, n["cy"] - h // 2, w, h

# ---------------- lane L1: Einkäuferin ----------------
node("Start_Beauftragt", "startEvent", "Verhandlung beauftragt", "ev", 250, 160, "L1",
     label=(205, 185, 90, 27))
node("Task_Mandat", "userTask", "Mandat festlegen", "task", 360, 160, "L1", "human",
     "Einkäuferin erfasst das Mandat als strukturierte Daten (Ziele, Grenzen, erlaubte Zugeständnisse, "
     "max. Runden). LangGraph: Graph-Input, Pydantic-validiert.")
node("Task_EskEntscheid", "userTask", "Eskalation entscheiden", "task", 2120, 160, "L1", "human",
     "LangGraph: ask_buyer, enthält nur interrupt(payload); beim Fortsetzen startet der Node von vorn. Der Runner "
     "(Web-UI oder Terminal) setzt mit Command(resume={decision, note}) und derselben thread_id fort. Entscheide: "
     "weiterverhandeln (Mandat bleibt, Bedingung bzw. Forderung wird zurückgewiesen und nicht erneut eskaliert); "
     "freigeben (nur angeboten, wenn escalate freigebbare Konditionen berechnet hat: Bedingung auf einer Grösse "
     "ausserhalb des Mandats, keine weitere Forderung oder Bedingung, Konditionen im Mandat und mindestens beim "
     "Mindestnutzen; der Code bucht diese Konditionen, die Bedingung steht als Vermerk im Protokoll, das Mandat "
     "bleibt) oder abbrechen. Die Notiz geht nur ins Protokoll. Die Eval setzt nicht fort und wertet den Halt als "
     "Eskalation (ADR 0015, Nachtrag 12.11.2026).")
node("GW_Freigabe", "exclusiveGateway", "Entscheid der Einkäuferin?", "gw", 2260, 160, "L1",
     label=(2290, 112, 130, 27))

# ---------------- lane L2: Agent ----------------
node("Task_Kontext", "serviceTask", "Kontext laden", "task", 470, 490, "L2", "code",
     "LangGraph: load_context. Stammdaten und heutige Konditionen über den ERP-Adapter (SQLite, ohne MCP; "
     "ADR 0009, 0015). Frühere Protokolle zeigt der Runner in der Demo an; der Graph nutzt sie nicht "
     "(Variante c gestrichen, ADR 0014).")
node("GW_JoinLoop", "exclusiveGateway", "", "gw", 590, 490, "L2")
node("Task_Pakete", "scriptTask", "Pakete berechnen (Code)", "task", 710, 490, "L2", "code",
     "LangGraph: offer_engine. 2–3 gleichwertige Pakete (MESO) entlang der Konzessionskurve; nur Werte im "
     "Mandat. Ausbau (c): Startpunkt aus der Paketwahl in früheren Protokollen.")
node("Task_Formulieren", "serviceTask", "Angebot formulieren (LLM)", "task", 860, 490, "L2", "llm",
     "LangGraph: narrate. Formuliert die Pakete der offer_engine; sieht nur Pakete und Runde, nie das Mandat und "
     "nie den Lieferantentext. Scheitert der Aufruf nach den Retries, geht der Standardtext hinaus.")
node("Boundary_Formulieren", "boundaryEvent", "LLM-Fehler: kein Text", "ev", 890, 530, "L2",
     label=(900, 552, 60, 27), attached="Task_Formulieren")
node("Task_Guard", "businessRuleTask", "Nachricht prüfen (Code)", "task", 1010, 490, "L2", "code",
     "LangGraph: mandate_guard. Zahlen im Text = Paketwerte, jedes Paket genannt, kein Betrag, kein "
     "Walk-away-Leak, KI-Hinweis in der ersten Nachricht.")
node("GW_Guard", "exclusiveGateway", "Mandat eingehalten?", "gw", 1130, 490, "L2",
     label=(1090, 428, 80, 27))
node("GW_JoinTemplate", "exclusiveGateway", "", "gw", 1130, 640, "L2")
node("Task_Template", "scriptTask", "Standardtext verwenden (Code)", "task", 1250, 640, "L2", "code",
     "LangGraph: template_message. Fail-safe: Vorlage gibt die Pakete wörtlich wieder; Template-Rate ist Metrik.")
node("GW_JoinSend", "exclusiveGateway", "", "gw", 1350, 490, "L2")
node("Task_SendWait", "task", "Angebot senden, Antwort abwarten", "task", 1470, 490, "L2", "code",
     "LangGraph: send_and_wait. Vor die Nachricht kommen Zurückweisungen aus Vorlagen. Eval: regelbasierter "
     "Simulator; Demo und Live-Runden: Mensch als Lieferant in der Web-UI (Terminal als Fallback), sieht nur den "
     "Text (ADR 0015, 0016).")
node("GW_JoinExtract", "exclusiveGateway", "", "gw", 1590, 490, "L2")
node("Task_Extract", "serviceTask", "Antwort extrahieren (LLM)", "task", 1710, 490, "L2", "llm",
     "LangGraph: parse_response. Strukturierte Ausgabe (Pydantic): Typ, gewähltes Paket, Gegenangebot, "
     "Aussagen mit Typ (Befugnis-Behauptung, Information, Forderung, Bedingung) und Grösse. Die Einkaufsrichtlinie "
     "steht vollständig im Prompt (ohne RAG; ADR 0009). Lieferantentext ist untrusted input. Scheitert die "
     "Extraktion auch nach der Korrekturrunde, gilt die Antwort als nicht auswertbar (im Code: assess_response "
     "eskaliert, ADR 0008 Regel 3).")
node("Boundary_Extract", "boundaryEvent", "LLM-Fehler: nicht auswertbar", "ev", 1740, 450, "L2",
     label=(1760, 400, 90, 27), attached="Task_Extract")
node("Task_Assess", "businessRuleTask", "Antwort bewerten (Code)", "task", 1860, 490, "L2", "code",
     "LangGraph: assess_response. Einigung, wenn das gewählte Paket einem gesendeten entspricht oder unsere "
     "Annahme bestätigt wird. Ein Gegenangebot im Mandat, das mindestens so viel wert ist wie das eigene nächste "
     "Paket, wird angenommen (AC_next). Eskalation nur, wenn das Mandat den Entscheid nicht abdeckt: Bedingung, "
     "die das Mandat nicht regelt, abgelehnte Forderung wiederholt, Antwort nicht auswertbar (ADR 0008). "
     "Behauptungen über Zusagen ändern das Mandat nie: zurückweisen, protokollieren, weiter.")
node("GW_Bewertung", "exclusiveGateway", "Bewertung?", "gw", 1990, 490, "L2",
     label=(1925, 520, 60, 14))
node("GW_JoinEsc", "exclusiveGateway", "", "gw", 1990, 370, "L2")
node("Task_EskPrep", "scriptTask", "Eskalation aufbereiten (Code)", "task", 2120, 370, "L2", "code",
     "LangGraph: escalate. Vorlage für die Einkäuferin ohne LLM (ADR 0014): Grund nach ADR 0008, Zitat der "
     "Forderung, Verlauf und letzte Antwort. Schreibt das Protokoll mit Status «escalated» und sendet dem "
     "Lieferanten einen Zwischenbescheid. Berechnet ohne LLM, welche Konditionen die Einkäuferin freigeben könnte "
     "(oder keine). Nichts davon steht in ask_buyer, weil dieser Node beim Fortsetzen neu startet.")
node("GW_Weiter", "exclusiveGateway", "Nächster Schritt?", "gw", 1990, 640, "L2",
     label=(2020, 668, 90, 14))
node("Task_Accept", "task", "Annahme senden, Bestätigung abwarten", "task", 1800, 640, "L2", "code",
     "LangGraph: send_and_wait mit pending.kind = accept; Text aus der Vorlage accept_text (kein LLM). Die "
     "Antwort wird extrahiert und bewertet wie jede andere. «accept» gilt nur für das letzte Gegenangebot; eine "
     "abgelehnte Annahme zählt als Runde. Ein Gegenangebot ist auch nach der letzten Runde annehmbar.")
node("GW_JoinBuyer", "exclusiveGateway", "", "gw", 2260, 370, "L2")
node("GW_JoinFinal", "exclusiveGateway", "", "gw", 2260, 490, "L2")
node("Task_Record", "serviceTask", "Ergebnis und Protokoll erfassen", "task", 2380, 490, "L2", "code",
     "LangGraph: record_outcome über den ERP-Adapter, auf allen Ausgängen, idempotent pro Verhandlung: "
     "Konditionen bei Deal gebucht (auch nach Freigabe durch die Einkäuferin); Protokoll mit Startpaketen, Reaktion und Paketwahl pro Runde, Ergebnis, "
     "Hinweisen sowie Entscheid und Notiz der Einkäuferin. Langzeitgedächtnis (ADR 0015); Metrik korrekt_gebucht.")
node("Task_Notify", "sendTask", "Ergebnis mitteilen", "task", 2530, 490, "L2", "code",
     "LangGraph: notify_supplier. Vorlage: Bestätigung (nach einer Freigabe mit Verweis auf die Rücksprache mit "
     "der Einkäuferin), Absage oder Abbruch nach Rücksprache mit der Einkäuferin.")
node("GW_Ergebnis", "exclusiveGateway", "Ergebnis?", "gw", 2660, 490, "L2",
     label=(2590, 455, 50, 14))
node("End_Abbruch", "endEvent", "Nach Eskalation abgebrochen", "ev", 2760, 370, "L2",
     label=(2722, 395, 76, 40))
node("End_Deal", "endEvent", "Neue Konditionen vereinbart", "ev", 2760, 490, "L2",
     label=(2725, 515, 70, 40))
node("End_KeinDeal", "endEvent", "Kein Deal", "ev", 2760, 640, "L2",
     label=(2735, 665, 50, 14))

# ---------------- data (not in lanes) ----------------
# id, tag, name, kind, cx, cy, label, store
data = [
    ("DO_Mandat", "dataObjectReference", "Mandat", "do", 440, 225, (422, 252, 40, 14), None),
    ("DS_ERP_Read", "dataStoreReference", "ERP-Adapter (SQLite): Stammdaten, Konditionen, Protokolle", "ds",
     470, 640, (395, 670, 150, 40), "DataStore_ERP"),
    ("DS_ERP_Write", "dataStoreReference", "ERP-Adapter (SQLite): Stammdaten, Konditionen, Protokolle", "ds",
     2380, 640, (2305, 670, 150, 40), "DataStore_ERP"),
    ("DS_Richtlinie", "dataStoreReference", "Einkaufsrichtlinie (im Prompt)", "ds", 1690, 300,
     (1530, 292, 135, 27), "DataStore_Policy"),
]

annotation = ("Legende", 640, 100, 930, 95,
              "Farben: orange = LLM (probabilistisch) · blau = Code (deterministisch) · grün = Mensch.\n"
              "Grundsatz: LLM extrahiert und formuliert, Code entscheidet über Zahlen und Mandat.\n"
              "Ablation: (a) ein LLM-Node übernimmt Pakete, Formulieren, Extrahieren und Bewerten, ohne Prüfung im Code; (b) wie gezeichnet.\n"
              "Gedächtnis: State pro Verhandlung im Checkpointer, Protokolle im ERP-Adapter (ADR 0015); (c) wäre der Ausbau.\n"
              "ERP-Adapter ohne MCP, Richtlinie ohne RAG (ADR 0009). Eine Instanz pro Lieferant.")

# extra annotations attached to a task: id, task, x, y, w, h, text, association waypoints
notes = [
    ("Annotation_Assess", "Task_Assess", 1580, 200, 480, 52,
     "Zurückweisungen (Behauptung, Forderung, Entscheid der Einkäuferin) als Vorlagensatz vor der nächsten "
     "Nachricht. Konfidenz < 0,7 = unklar → Eskalation (Haken, ADR 0011).",
     [(1880, 450), (1880, 252)]),
]

# ---------------- sequence flows ----------------
flows = []
def flow(id, s, t, wps, name="", cond=None, lbl=None):
    flows.append(dict(id=id, s=s, t=t, wps=wps, name=name, cond=cond, lbl=lbl))

WEITER = "state.round < state.mandate.max_rounds and state.packages_left > 0 and not state.supplier_final"

flow("Flow_01", "Start_Beauftragt", "Task_Mandat", [(268, 160), (310, 160)])
flow("Flow_02", "Task_Mandat", "Task_Kontext", [(410, 160), (470, 160), (470, 450)])
flow("Flow_03", "Task_Kontext", "GW_JoinLoop", [(520, 490), (565, 490)])
flow("Flow_04", "GW_JoinLoop", "Task_Pakete", [(615, 490), (660, 490)])
flow("Flow_05", "Task_Pakete", "Task_Formulieren", [(760, 490), (810, 490)])
flow("Flow_06", "Task_Formulieren", "Task_Guard", [(910, 490), (960, 490)])
flow("Flow_07", "Task_Guard", "GW_Guard", [(1060, 490), (1105, 490)])
flow("Flow_08", "GW_Guard", "GW_JoinSend", [(1155, 490), (1325, 490)], "ja",
     "state.guard_ok", (1170, 470, 14, 14))
flow("Flow_09", "GW_Guard", "GW_JoinTemplate", [(1130, 515), (1130, 615)], "nein",
     "not state.guard_ok", (1100, 555, 22, 14))
flow("Flow_E1", "Boundary_Formulieren", "GW_JoinTemplate", [(890, 548), (890, 640), (1105, 640)])
flow("Flow_09b", "GW_JoinTemplate", "Task_Template", [(1155, 640), (1200, 640)])
flow("Flow_10", "Task_Template", "GW_JoinSend", [(1300, 640), (1350, 640), (1350, 515)])
flow("Flow_11", "GW_JoinSend", "Task_SendWait", [(1375, 490), (1420, 490)])
flow("Flow_12", "Task_SendWait", "GW_JoinExtract", [(1520, 490), (1565, 490)])
flow("Flow_12b", "GW_JoinExtract", "Task_Extract", [(1615, 490), (1660, 490)])
flow("Flow_13", "Task_Extract", "Task_Assess", [(1760, 490), (1810, 490)])
flow("Flow_14", "Task_Assess", "GW_Bewertung", [(1910, 490), (1965, 490)])
flow("Flow_15", "GW_Bewertung", "GW_JoinFinal", [(2015, 490), (2235, 490)], "Einigung",
     'state.assessment == "deal"', (2025, 470, 48, 14))
flow("Flow_16", "GW_Bewertung", "GW_JoinEsc", [(1990, 465), (1990, 395)],
     "Mandat reicht nicht oder unklar", 'state.assessment == "escalate"', (1890, 405, 95, 27))
flow("Flow_E2", "Boundary_Extract", "GW_JoinEsc", [(1740, 432), (1740, 370), (1965, 370)])
flow("Flow_16b", "GW_JoinEsc", "Task_EskPrep", [(2015, 370), (2070, 370)])
flow("Flow_17", "GW_Bewertung", "GW_Weiter", [(1990, 515), (1990, 615)],
     "Gegenangebot oder Ablehnung", 'state.assessment in ("counter", "reject")',
     (1998, 545, 110, 27))
flow("Flow_18", "Task_EskPrep", "Task_EskEntscheid", [(2120, 330), (2120, 200)])
flow("Flow_19", "Task_EskEntscheid", "GW_Freigabe", [(2170, 160), (2235, 160)])
flow("Flow_20", "GW_Freigabe", "GW_JoinLoop", [(2260, 135), (2260, 90), (590, 90), (590, 465)],
     "weiterverhandeln (Mandat bleibt)", 'state.buyer_decision == "weiterverhandeln"',
     (2040, 72, 200, 14))
flow("Flow_21", "GW_Freigabe", "GW_JoinBuyer", [(2260, 185), (2260, 345)],
     "abbrechen", 'state.buyer_decision == "abbrechen"', (2268, 270, 50, 14))
flow("Flow_21b", "GW_Freigabe", "GW_JoinBuyer", [(2285, 160), (2340, 160), (2340, 370), (2285, 370)],
     "freigeben (Bedingung annehmen)", 'state.buyer_decision == "freigeben"', (2348, 200, 145, 27))
flow("Flow_21c", "GW_JoinBuyer", "GW_JoinFinal", [(2260, 395), (2260, 465)])
flow("Flow_22", "GW_Weiter", "GW_JoinLoop", [(1990, 665), (1990, 720), (590, 720), (590, 515)],
     "neue Runde: Runde < max. Runden, Paket offen, keine endgültige Absage", WEITER, (650, 725, 420, 14))
flow("Flow_A1", "GW_Weiter", "Task_Accept", [(1965, 640), (1850, 640)],
     "Gegenangebot annehmbar (AC_next)", 'state.assessment == "accept_counter"', (1858, 600, 100, 27))
flow("Flow_A2", "Task_Accept", "GW_JoinExtract", [(1750, 640), (1590, 640), (1590, 515)])
flow("Flow_23", "GW_Weiter", "GW_JoinFinal", [(2015, 640), (2260, 640), (2260, 515)], "sonst: kein Deal",
     f'state.assessment != "accept_counter" and not ({WEITER})', (2080, 616, 90, 14))
flow("Flow_24", "GW_JoinFinal", "Task_Record", [(2285, 490), (2330, 490)])
flow("Flow_25", "Task_Record", "Task_Notify", [(2430, 490), (2480, 490)])
flow("Flow_26", "Task_Notify", "GW_Ergebnis", [(2580, 490), (2635, 490)])
flow("Flow_27", "GW_Ergebnis", "End_Deal", [(2685, 490), (2742, 490)], "Deal",
     'state.outcome == "deal"', (2695, 470, 26, 14))
flow("Flow_28", "GW_Ergebnis", "End_Abbruch", [(2660, 465), (2660, 370), (2742, 370)], "abgebrochen",
     'state.outcome == "escalated"', (2670, 350, 60, 14))
flow("Flow_29", "GW_Ergebnis", "End_KeinDeal", [(2660, 515), (2660, 640), (2742, 640)], "kein Deal",
     'state.outcome == "no_deal"', (2670, 620, 48, 14))

msgs = [
    ("MsgFlow_Angebot", "Task_SendWait", "Participant_Lieferant", "Angebot (2–3 Pakete)",
     [(1450, 530), (1450, 820)], (1310, 795, 135, 14)),
    ("MsgFlow_Antwort", "Participant_Lieferant", "Task_SendWait", "Antwort",
     [(1490, 820), (1490, 530)], (1498, 795, 40, 14)),
    ("MsgFlow_Annahme", "Task_Accept", "Participant_Lieferant", "Annahme (Vorlage)",
     [(1780, 680), (1780, 820)], (1655, 795, 120, 14)),
    ("MsgFlow_Bestaetigung", "Participant_Lieferant", "Task_Accept", "Bestätigung oder Ablehnung",
     [(1820, 820), (1820, 680)], (1828, 795, 175, 14)),
    ("MsgFlow_Zwischenbescheid", "Task_EskPrep", "Participant_Lieferant", "Zwischenbescheid",
     [(2140, 410), (2140, 820)], (2148, 795, 110, 14)),
    ("MsgFlow_Ergebnis", "Task_Notify", "Participant_Lieferant", "Bestätigung oder Absage",
     [(2530, 530), (2530, 820)], (2538, 795, 150, 14)),
]

# data associations: (id, kind, task, data, waypoints)
assoc = [
    ("DOA_Mandat", "out", "Task_Mandat", "DO_Mandat", [(410, 190), (422, 208)]),
    ("DIA_ERP", "in", "Task_Kontext", "DS_ERP_Read", [(470, 615), (470, 530)]),
    ("DIA_Richtlinie_Extract", "in", "Task_Extract", "DS_Richtlinie", [(1690, 325), (1690, 450)]),
    ("DOA_ERP", "out", "Task_Record", "DS_ERP_Write", [(2380, 530), (2380, 615)]),
]

# ---------------- serialise ----------------
incoming = {n["id"]: [] for n in nodes}
outgoing = {n["id"]: [] for n in nodes}
for f in flows:
    outgoing[f["s"]].append(f["id"])
    incoming[f["t"]].append(f["id"])

def e(s): return escape(s, {'"': "&quot;"})

proc = []
lanes = {"L1": [], "L2": []}
for n in nodes:
    lanes[n["lane"]].append(n["id"])
proc.append('    <bpmn:laneSet id="LaneSet_1">')
proc.append('      <bpmn:lane id="Lane_Einkauf" name="Einkäuferin">')
proc += [f"        <bpmn:flowNodeRef>{i}</bpmn:flowNodeRef>" for i in lanes["L1"]]
proc.append("      </bpmn:lane>")
proc.append('      <bpmn:lane id="Lane_Agent" name="Einkaufsagent (LangGraph)">')
proc += [f"        <bpmn:flowNodeRef>{i}</bpmn:flowNodeRef>" for i in lanes["L2"]]
proc.append("      </bpmn:lane>")
proc.append("    </bpmn:laneSet>")

ain = {a[2]: [] for a in assoc}
aout = {a[2]: [] for a in assoc}
for a in assoc:
    (ain if a[1] == "in" else aout)[a[2]].append(a)

for n in nodes:
    attrs = f'id="{n["id"]}"' + (f' name="{e(n["name"])}"' if n["name"] else "")
    body = []
    if n["doc"]:
        body.append(f'      <bpmn:documentation>{e(n["doc"])}</bpmn:documentation>')
    body += [f"      <bpmn:incoming>{i}</bpmn:incoming>" for i in incoming[n["id"]]]
    body += [f"      <bpmn:outgoing>{i}</bpmn:outgoing>" for i in outgoing[n["id"]]]
    for a in ain.get(n["id"], []):
        prop = f"Property_{a[0]}"
        body.append(f'      <bpmn:property id="{prop}" name="__targetRef_placeholder" />')
        body.append(f'      <bpmn:dataInputAssociation id="{a[0]}">')
        body.append(f"        <bpmn:sourceRef>{a[3]}</bpmn:sourceRef>")
        body.append(f"        <bpmn:targetRef>{prop}</bpmn:targetRef>")
        body.append("      </bpmn:dataInputAssociation>")
    for a in aout.get(n["id"], []):
        body.append(f'      <bpmn:dataOutputAssociation id="{a[0]}">')
        body.append(f"        <bpmn:targetRef>{a[3]}</bpmn:targetRef>")
        body.append("      </bpmn:dataOutputAssociation>")
    if n["attached"]:
        attrs += f' attachedToRef="{n["attached"]}"'
        body.append(f'      <bpmn:errorEventDefinition id="ErrDef_{n["id"]}" errorRef="Error_LLM" />')
    proc.append(f"    <bpmn:{n['tag']} {attrs}>")
    proc += body
    proc.append(f"    </bpmn:{n['tag']}>")

proc.append('    <bpmn:dataObject id="DataObject_Mandat" />')
for d in data:
    if d[1] == "dataObjectReference":
        proc.append(f'    <bpmn:dataObjectReference id="{d[0]}" name="{e(d[2])}" dataObjectRef="DataObject_Mandat" />')
    else:
        proc.append(f'    <bpmn:dataStoreReference id="{d[0]}" name="{e(d[2])}" dataStoreRef="{d[7]}" />')

for f in flows:
    a = f'id="{f["id"]}"' + (f' name="{e(f["name"])}"' if f["name"] else "") + f' sourceRef="{f["s"]}" targetRef="{f["t"]}"'
    if f["cond"]:
        proc.append(f"    <bpmn:sequenceFlow {a}>")
        proc.append(f'      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">{e(f["cond"])}</bpmn:conditionExpression>')
        proc.append("    </bpmn:sequenceFlow>")
    else:
        proc.append(f"    <bpmn:sequenceFlow {a} />")

ann_id = "Annotation_Legende"
proc.append(f'    <bpmn:textAnnotation id="{ann_id}"><bpmn:text>{e(annotation[5])}</bpmn:text></bpmn:textAnnotation>')
for nt in notes:
    proc.append(f'    <bpmn:textAnnotation id="{nt[0]}"><bpmn:text>{e(nt[6])}</bpmn:text></bpmn:textAnnotation>')
    proc.append(f'    <bpmn:association id="Assoc_{nt[0]}" sourceRef="{nt[1]}" targetRef="{nt[0]}" />')

# ---------------- DI ----------------
di = []
def shape(id, x, y, w, h, color=None, extra="", label=None):
    col = ""
    if color:
        s, f = COL[color]
        col = f' bioc:stroke="{s}" bioc:fill="{f}" color:border-color="{s}" color:background-color="{f}"'
    lab = ""
    if label:
        lab = f'<bpmndi:BPMNLabel><dc:Bounds x="{label[0]}" y="{label[1]}" width="{label[2]}" height="{label[3]}" /></bpmndi:BPMNLabel>'
    di.append(f'      <bpmndi:BPMNShape id="{id}_di" bpmnElement="{id}"{extra}{col}><dc:Bounds x="{x}" y="{y}" width="{w}" height="{h}" />{lab}</bpmndi:BPMNShape>')

POOL_W = 2680
shape("Participant_Musterhandel", 150, 60, POOL_W, 700, extra=' isHorizontal="true"')
shape("Lane_Einkauf", 180, 60, POOL_W - 30, 200, extra=' isHorizontal="true"')
shape("Lane_Agent", 180, 260, POOL_W - 30, 500, extra=' isHorizontal="true"')
shape("Participant_Lieferant", 150, 820, POOL_W, 60, extra=' isHorizontal="true"')
for n in nodes:
    x, y, w, h = bounds(n)
    extra = ' isMarkerVisible="true"' if n["tag"] == "exclusiveGateway" else ""
    shape(n["id"], x, y, w, h, n["color"], extra, n["label"])
for d in data:
    w, h = SIZE[d[3]]
    shape(d[0], d[4] - w // 2, d[5] - h // 2, w, h, label=d[6])
shape(ann_id, annotation[1], annotation[2], annotation[3], annotation[4])
for nt in notes:
    shape(nt[0], nt[2], nt[3], nt[4], nt[5])

def edge(id, wps, label=None):
    pts = "".join(f'<di:waypoint x="{x}" y="{y}" />' for x, y in wps)
    lab = ""
    if label:
        lab = f'<bpmndi:BPMNLabel><dc:Bounds x="{label[0]}" y="{label[1]}" width="{label[2]}" height="{label[3]}" /></bpmndi:BPMNLabel>'
    di.append(f'      <bpmndi:BPMNEdge id="{id}_di" bpmnElement="{id}">{pts}{lab}</bpmndi:BPMNEdge>')

for f in flows:
    edge(f["id"], f["wps"], f["lbl"] if f["name"] else None)
for m in msgs:
    edge(m[0], m[4], m[5])
for a in assoc:
    edge(a[0], a[4])
for nt in notes:
    edge(f"Assoc_{nt[0]}", nt[7])

collab = ['  <bpmn:collaboration id="Collaboration_Einkaufsagent">',
          '    <bpmn:participant id="Participant_Musterhandel" name="Musterhandel AG (fiktiv): Konditionen-Nachverhandlung" processRef="Process_Einkaufsagent" />',
          '    <bpmn:participant id="Participant_Lieferant" name="Lieferant (Eval: simuliert, Demo: Mensch in der Web-UI)" />']
for m in msgs:
    collab.append(f'    <bpmn:messageFlow id="{m[0]}" name="{e(m[3])}" sourceRef="{m[1]}" targetRef="{m[2]}" />')
collab.append("  </bpmn:collaboration>")

xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" id="Definitions_Einkaufsagent" targetNamespace="http://bpmn.io/schema/bpmn" exporter="gen_bpmn_v5.py" exporterVersion="5.0">
{chr(10).join(collab)}
  <bpmn:error id="Error_LLM" name="LLM-Aufruf gescheitert" errorCode="llm_failed" />
  <bpmn:dataStore id="DataStore_ERP" name="ERP-Adapter (SQLite)" />
  <bpmn:dataStore id="DataStore_Policy" name="Einkaufsrichtlinie" />
  <bpmn:process id="Process_Einkaufsagent" name="Einkaufsagent" isExecutable="false">
{chr(10).join(proc)}
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_Einkaufsagent">
{chr(10).join(di)}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
'''
open(OUT, "w", encoding="utf-8").write(xml)
print("wrote", OUT, len(nodes), "flow nodes,", len(flows), "sequence flows")

"""Generates docs/process/einkaufsagent-prozess.bpmn (v2) with explicit DI coordinates.

Run: python3 gen_bpmn.py <out.bpmn>
Layout grid: lane L1 (Einkäuferin) y 60–260, lane L2 (Agent) y 260–800,
rows in L2: upper 340, main 460, lower 620, loop line 730. Supplier pool y 860–920.
"""
import sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]

# --- colour code (bpmn-js renders bioc:* and color:*) -------------------------
COL = {
    "llm":   ("#b45f06", "#fce8d4"),   # orange: probabilistic
    "code":  ("#0b5394", "#dceaf8"),   # blue: deterministic
    "human": ("#2f6b3c", "#e2f0de"),   # green: human
}

SIZE = {"task": (100, 80), "gw": (50, 50), "ev": (36, 36), "ds": (50, 50), "do": (36, 50)}

nodes = []   # dict(id, tag, name, kind, cx, cy, lane, color, doc, extra_xml, label=(x,y,w,h))
def node(id, tag, name, kind, cx, cy, lane, color=None, doc=None, extra="", label=None):
    nodes.append(dict(id=id, tag=tag, name=name, kind=kind, cx=cx, cy=cy, lane=lane,
                      color=color, doc=doc, extra=extra, label=label))

def bounds(n):
    w, h = SIZE[n["kind"]]
    return n["cx"] - w // 2, n["cy"] - h // 2, w, h

# ---------------- lane L1: Einkäuferin ----------------
node("Start_Beauftragt", "startEvent", "Nachverhandlung beauftragt", "ev", 260, 160, "L1",
     label=(225, 185, 70, 27))
node("Task_Mandat", "userTask", "Mandat festlegen", "task", 370, 160, "L1", "human",
     "Einkäuferin erfasst das Mandat als strukturierte Daten (Ziele, Grenzen, erlaubte Zugeständnisse, max. Runden). LangGraph: Graph-Input, Pydantic-validiert.")
node("Task_EskEntscheid", "userTask", "Eskalation entscheiden", "task", 2340, 160, "L1", "human",
     "LangGraph: interrupt() im Node escalate; Resume per Command(resume={decision, new_mandate?}). MVP: KW46.")
node("GW_Esk", "exclusiveGateway", "Freigabe zum Weiterverhandeln?", "gw", 2470, 160, "L1",
     label=(2500, 118, 100, 27))

# ---------------- lane L2: Agent ----------------
node("Task_Kontext", "serviceTask", "Kontext laden (ERP via MCP)", "task", 480, 460, "L2", "code",
     "LangGraph: load_context. KW42: JSON-Stub; KW43: ERP-Mock als MCP-Server (SQLite).")
node("Task_Strategie", "serviceTask", "Strategie wählen (LLM)", "task", 630, 460, "L2", "llm",
     "LangGraph: plan. LLM wählt Konzessionstaktik (Boulware/Conceder) aus Lieferantenprofil und Gedächtnis. MVP: KW43 (Variante b).")
node("GW_JoinPlan", "exclusiveGateway", "", "gw", 750, 460, "L2")
node("Task_Pakete", "scriptTask", "Pakete berechnen (Code)", "task", 870, 460, "L2", "code",
     "LangGraph: offer_engine. 2–3 gleichwertige Pakete (MESO) entlang der Konzessionskurve; nur Werte innerhalb des Mandats. MVP: KW43.")
node("Task_Formulieren", "serviceTask", "Angebot formulieren (LLM)", "task", 1020, 460, "L2", "llm",
     "LangGraph: narrate. Zahlen kommen ausschliesslich aus offer_engine.")
node("Task_Guard", "businessRuleTask", "Nachricht prüfen (Code)", "task", 1170, 460, "L2", "code",
     "LangGraph: mandate_guard. Prüft: Zahlen im Text = Paketwerte, keine Zusagen ausserhalb Mandat, kein Walk-away-Leak, KI-Hinweis, keine erfundenen Fakten (Regelliste).")
node("GW_Guard", "exclusiveGateway", "Mandat eingehalten?", "gw", 1290, 460, "L2",
     label=(1250, 398, 80, 27))
node("Task_Template", "scriptTask", "Standardtext verwenden (Code)", "task", 1400, 620, "L2", "code",
     "LangGraph: template_message. Fail-safe: deterministische Vorlage rendert die Pakete wörtlich; zählt als Template-Rate in der Evaluation.")
node("GW_JoinSend", "exclusiveGateway", "", "gw", 1510, 460, "L2")
node("Task_Send", "sendTask", "Angebot senden", "task", 1630, 460, "L2", "code",
     "LangGraph: send_and_wait (Teil 1). Im Projekt: simulierter Lieferant; real: Kanal + interrupt().")
node("Task_Receive", "receiveTask", "Antwort empfangen", "task", 1780, 460, "L2", "code",
     "LangGraph: send_and_wait (Teil 2).")
node("Timer_Antwort", "boundaryEvent", "48 h ohne Antwort", "ev", 1780, 420, "L2",
     extra='attachedToRef="Task_Receive"', label=(1790, 383, 90, 14))
node("Task_Extract", "serviceTask", "Antwort extrahieren (LLM)", "task", 1930, 460, "L2", "llm",
     "LangGraph: parse_response. Strukturierte Ausgabe (Pydantic): Typ, gewähltes Paket, Gegenangebot, neue Forderungen, Konfidenz. Lieferantentext ist untrusted input.")
node("Task_Assess", "businessRuleTask", "Antwort bewerten (Code)", "task", 2080, 460, "L2", "code",
     "LangGraph: assess_response. Deterministisch: Annahme nur, wenn Paket-ID zu einem gesendeten Paket passt; Gegenangebot annehmen, wenn im Mandat und Nutzen ≥ nächstes eigenes Paket (AC_next); neue Dimension, Preiserhöhung über Mandat oder Konfidenz < Schwelle → Eskalation.")
node("GW_Art", "exclusiveGateway", "Bewertung?", "gw", 2210, 460, "L2",
     label=(2140, 490, 60, 14))
node("GW_JoinEsk", "exclusiveGateway", "", "gw", 2210, 340, "L2")
node("Task_Summary", "serviceTask", "Eskalation aufbereiten (LLM)", "task", 2340, 340, "L2", "llm",
     "LangGraph: escalate (vor interrupt). Zusammenfassung: Forderung, Gegenwert, Empfehlung (US4).")
node("GW_Weiter", "exclusiveGateway", "Weiterverhandeln?", "gw", 2210, 620, "L2",
     label=(2070, 612, 112, 14))
node("Task_Book", "serviceTask", "Konditionen im ERP erfassen (MCP)", "task", 2340, 460, "L2", "code",
     "LangGraph: book_deal. MVP: KW43 (ERP-Mock).")
node("GW_JoinFinal", "exclusiveGateway", "", "gw", 2470, 460, "L2")
node("Task_Notify", "sendTask", "Ergebnis mitteilen", "task", 2590, 460, "L2", "code",
     "LangGraph: notify_supplier. Bestätigung, Absage oder Hinweis auf Übernahme durch die Einkäuferin; Lieferant bleibt nie ohne Abschlussnachricht.")
node("Task_Memory", "serviceTask", "Protokoll und Gedächtnis aktualisieren", "task", 2740, 460, "L2", "code",
     "LangGraph: update_memory (Store). Auf allen Ausgängen, auch ohne Deal (US6). MVP: KW46.")
node("GW_Ergebnis", "exclusiveGateway", "Ergebnis?", "gw", 2870, 460, "L2",
     label=(2800, 425, 50, 14))
node("End_Deal", "endEvent", "Neue Konditionen vereinbart", "ev", 2970, 460, "L2",
     label=(2935, 485, 70, 40))
node("End_Uebergabe", "endEvent", "An Einkäuferin übergeben", "ev", 2970, 340, "L2",
     label=(2935, 365, 70, 27))
node("End_KeinDeal", "endEvent", "Kein Deal", "ev", 2970, 620, "L2",
     label=(2945, 645, 50, 14))

# ---------------- data (not in lanes) ----------------
data = [
    # id, tag, name, kind, cx, cy, label
    ("DO_Mandat", "dataObjectReference", "Mandat", "do", 448, 215, (430, 242, 40, 14)),
    ("DS_ERP", "dataStoreReference", "ERP-Mock", "ds", 480, 620, (455, 650, 50, 14)),
    ("DS_Mem_Read", "dataStoreReference", "Lieferanten-Gedächtnis", "ds", 630, 620, (570, 650, 120, 14)),
    ("DS_Mem_Write", "dataStoreReference", "Lieferanten-Gedächtnis", "ds", 2740, 620, (2680, 650, 120, 14)),
]

annotation = ("Legende", 860, 95, 560, 60,
              "Farben: orange = LLM (probabilistisch) · blau = Code (deterministisch) · grün = Mensch.\n"
              "Grundsatz: LLM schlägt vor und formuliert, Code entscheidet über Zahlen und Mandat.\n"
              "LangGraph-Node-Namen stehen in der Dokumentation jedes Elements.")

# ---------------- sequence flows ----------------
flows = []  # id, src, tgt, name, waypoints, condition, label_bounds
def flow(id, s, t, wps, name="", cond=None, lbl=None):
    flows.append(dict(id=id, s=s, t=t, wps=wps, name=name, cond=cond, lbl=lbl))

flow("Flow_01", "Start_Beauftragt", "Task_Mandat", [(278, 160), (320, 160)])
flow("Flow_02", "Task_Mandat", "Task_Kontext", [(420, 160), (480, 160), (480, 420)])
flow("Flow_03", "Task_Kontext", "Task_Strategie", [(530, 460), (580, 460)])
flow("Flow_04", "Task_Strategie", "GW_JoinPlan", [(680, 460), (725, 460)])
flow("Flow_05", "GW_JoinPlan", "Task_Pakete", [(775, 460), (820, 460)])
flow("Flow_06", "Task_Pakete", "Task_Formulieren", [(920, 460), (970, 460)])
flow("Flow_07", "Task_Formulieren", "Task_Guard", [(1070, 460), (1120, 460)])
flow("Flow_08", "Task_Guard", "GW_Guard", [(1220, 460), (1265, 460)])
flow("Flow_09", "GW_Guard", "GW_JoinSend", [(1315, 460), (1485, 460)], "ja",
     "state.guard_ok", (1330, 440, 14, 14))
flow("Flow_10", "GW_Guard", "Task_Template", [(1290, 485), (1290, 620), (1350, 620)], "nein",
     "not state.guard_ok", (1260, 550, 22, 14))
flow("Flow_11", "Task_Template", "GW_JoinSend", [(1450, 620), (1510, 620), (1510, 485)])
flow("Flow_12", "GW_JoinSend", "Task_Send", [(1535, 460), (1580, 460)])
flow("Flow_13", "Task_Send", "Task_Receive", [(1680, 460), (1730, 460)])
flow("Flow_14", "Task_Receive", "Task_Extract", [(1830, 460), (1880, 460)])
flow("Flow_15", "Task_Extract", "Task_Assess", [(1980, 460), (2030, 460)])
flow("Flow_16", "Task_Assess", "GW_Art", [(2130, 460), (2185, 460)])
flow("Flow_17", "GW_Art", "Task_Book", [(2235, 460), (2290, 460)], "Einigung",
     'state.assessment == "agreement"', (2238, 440, 48, 14))
flow("Flow_18", "GW_Art", "GW_JoinEsk", [(2210, 435), (2210, 365)], "ausserhalb Mandat oder unklar",
     'state.assessment == "escalate"', (2105, 375, 95, 27))
flow("Flow_19", "GW_Art", "GW_Weiter", [(2210, 485), (2210, 595)], "Gegenangebot ungenügend oder Ablehnung",
     'state.assessment in ("counter", "reject")', (2218, 520, 110, 40))
flow("Flow_20", "Timer_Antwort", "GW_JoinEsk", [(1780, 402), (1780, 340), (2185, 340)])
flow("Flow_21", "GW_JoinEsk", "Task_Summary", [(2235, 340), (2290, 340)])
flow("Flow_22", "Task_Summary", "Task_EskEntscheid", [(2340, 300), (2340, 200)])
flow("Flow_23", "Task_EskEntscheid", "GW_Esk", [(2390, 160), (2445, 160)])
flow("Flow_24", "GW_Esk", "GW_JoinPlan", [(2470, 135), (2470, 90), (750, 90), (750, 435)], "ja (ggf. Mandat erweitert)",
     'state.escalation_decision == "continue"', (2300, 72, 140, 14))
flow("Flow_25", "GW_Esk", "GW_JoinFinal", [(2470, 185), (2470, 435)], "nein: abbrechen oder übernehmen",
     'state.escalation_decision in ("abort", "takeover")', (2478, 270, 95, 27))
flow("Flow_26", "GW_Weiter", "GW_JoinPlan", [(2210, 645), (2210, 730), (750, 730), (750, 485)],
     "ja: Runde < max. Runden, Paket offen, Lieferant verhandelt weiter",
     "state.round < state.mandate.max_rounds and state.packages_left > 0 and not state.supplier_final",
     (1810, 735, 330, 14))
flow("Flow_27", "GW_Weiter", "GW_JoinFinal", [(2235, 620), (2470, 620), (2470, 485)], "nein",
     "not (state.round < state.mandate.max_rounds and state.packages_left > 0 and not state.supplier_final)", (2300, 600, 22, 14))
flow("Flow_28", "Task_Book", "GW_JoinFinal", [(2390, 460), (2445, 460)])
flow("Flow_29", "GW_JoinFinal", "Task_Notify", [(2495, 460), (2540, 460)])
flow("Flow_30", "Task_Notify", "Task_Memory", [(2640, 460), (2690, 460)])
flow("Flow_31", "Task_Memory", "GW_Ergebnis", [(2790, 460), (2845, 460)])
flow("Flow_32", "GW_Ergebnis", "End_Deal", [(2895, 460), (2952, 460)], "Deal",
     'state.outcome == "deal"', (2905, 440, 26, 14))
flow("Flow_33", "GW_Ergebnis", "End_Uebergabe", [(2870, 435), (2870, 340), (2952, 340)], "übergeben",
     'state.outcome == "handed_over"', (2880, 320, 52, 14))
flow("Flow_34", "GW_Ergebnis", "End_KeinDeal", [(2870, 485), (2870, 620), (2952, 620)], "kein Deal",
     'state.outcome == "no_deal"', (2880, 600, 48, 14))

msgs = [
    ("MsgFlow_Angebot", "Task_Send", "Participant_Lieferant", "Angebot (2–3 Pakete)", [(1630, 500), (1630, 860)], (1638, 800, 110, 14)),
    ("MsgFlow_Antwort", "Participant_Lieferant", "Task_Receive", "Antwort", [(1780, 860), (1780, 500)], (1788, 800, 40, 14)),
    ("MsgFlow_Ergebnis", "Task_Notify", "Participant_Lieferant", "Bestätigung oder Absage", [(2590, 500), (2590, 860)], (2598, 800, 120, 14)),
]

# data associations: (id, kind, task, store, waypoints)
assoc = [
    ("DOA_Mandat", "out", "Task_Mandat", "DO_Mandat", [(420, 190), (430, 205)]),
    ("DIA_ERP", "in", "Task_Kontext", "DS_ERP", [(480, 595), (480, 500)]),
    ("DIA_Mem", "in", "Task_Strategie", "DS_Mem_Read", [(630, 595), (630, 500)]),
    ("DOA_Mem", "out", "Task_Memory", "DS_Mem_Write", [(2740, 500), (2740, 595)]),
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
    if n["extra"]:
        attrs += " " + n["extra"]
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
    if n["tag"] == "boundaryEvent":
        body.append('      <bpmn:timerEventDefinition id="TimerDef_Antwort">')
        body.append('        <bpmn:timeDuration xsi:type="bpmn:tFormalExpression">PT48H</bpmn:timeDuration>')
        body.append("      </bpmn:timerEventDefinition>")
    proc.append(f"    <bpmn:{n['tag']} {attrs}>")
    proc += body
    proc.append(f"    </bpmn:{n['tag']}>")

proc.append('    <bpmn:dataObject id="DataObject_Mandat" />')
for d in data:
    if d[1] == "dataObjectReference":
        proc.append(f'    <bpmn:dataObjectReference id="{d[0]}" name="{e(d[2])}" dataObjectRef="DataObject_Mandat" />')
    else:
        store = "DataStore_ERP" if "ERP" in d[0] else "DataStore_Memory"
        proc.append(f'    <bpmn:dataStoreReference id="{d[0]}" name="{e(d[2])}" dataStoreRef="{store}" />')

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

POOL_W = 2910
shape("Participant_Musterhandel", 150, 60, POOL_W, 740, extra=' isHorizontal="true"')
shape("Lane_Einkauf", 180, 60, POOL_W - 30, 200, extra=' isHorizontal="true"')
shape("Lane_Agent", 180, 260, POOL_W - 30, 540, extra=' isHorizontal="true"')
shape("Participant_Lieferant", 150, 860, POOL_W, 60, extra=' isHorizontal="true"')
for n in nodes:
    x, y, w, h = bounds(n)
    extra = ' isMarkerVisible="true"' if n["tag"] == "exclusiveGateway" else ""
    shape(n["id"], x, y, w, h, n["color"], extra, n["label"])
for d in data:
    w, h = SIZE[d[3]]
    shape(d[0], d[4] - w // 2, d[5] - h // 2, w, h, label=d[6])
shape(ann_id, annotation[1], annotation[2], annotation[3], annotation[4])

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

collab = ['  <bpmn:collaboration id="Collaboration_Einkaufsagent">',
          '    <bpmn:participant id="Participant_Musterhandel" name="Musterhandel AG (fiktiv): Konditionen-Nachverhandlung" processRef="Process_Einkaufsagent" />',
          '    <bpmn:participant id="Participant_Lieferant" name="Lieferant (im Projekt simuliert)" />']
for m in msgs:
    collab.append(f'    <bpmn:messageFlow id="{m[0]}" name="{e(m[3])}" sourceRef="{m[1]}" targetRef="{m[2]}" />')
collab.append("  </bpmn:collaboration>")

xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" id="Definitions_Einkaufsagent" targetNamespace="http://bpmn.io/schema/bpmn" exporter="gen_bpmn.py" exporterVersion="2.0">
{chr(10).join(collab)}
  <bpmn:dataStore id="DataStore_ERP" name="ERP" />
  <bpmn:dataStore id="DataStore_Memory" name="Lieferanten-Gedächtnis" />
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

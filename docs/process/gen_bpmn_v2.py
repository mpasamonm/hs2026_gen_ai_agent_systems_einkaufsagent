"""Generates einkaufsagent-prozess_v2.bpmn (schlanke Fassung) with explicit DI coordinates.

Run: python3 gen_bpmn_v2.py <out.bpmn>
Changes against _v1: no timer, no LLM strategy node, send+wait as one task (= send_and_wait),
one ERP store incl. history (= memory, ADR 0005 Prüfpunkt 3), RAG store for extraction and escalation
(ADR 0007, team feedback 11.10.2026), escalation only if the mandate does not cover the decision (ADR 0008),
book_deal + update_memory merged into one record step on all paths.
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
def node(id, tag, name, kind, cx, cy, lane, color=None, doc=None, label=None):
    nodes.append(dict(id=id, tag=tag, name=name, kind=kind, cx=cx, cy=cy, lane=lane,
                      color=color, doc=doc, label=label))

def bounds(n):
    w, h = SIZE[n["kind"]]
    return n["cx"] - w // 2, n["cy"] - h // 2, w, h

# ---------------- lane L1: Einkäuferin ----------------
node("Start_Beauftragt", "startEvent", "Verhandlung beauftragt", "ev", 250, 160, "L1",
     label=(205, 185, 90, 27))
node("Task_Mandat", "userTask", "Mandat festlegen", "task", 360, 160, "L1", "human",
     "Einkäuferin erfasst das Mandat als strukturierte Daten (Ziele, Grenzen, erlaubte Zugeständnisse, "
     "max. Runden). LangGraph: Graph-Input, Pydantic-validiert. Ab KW42.")
node("Task_EskEntscheid", "userTask", "Eskalation entscheiden", "task", 2030, 160, "L1", "human",
     "LangGraph: interrupt() im Node escalate; Resume per Command(resume={decision, new_mandate?}). "
     "Ab KW46; bis dahin endet jede Eskalation mit Übergabe.")
node("GW_Freigabe", "exclusiveGateway", "Freigabe zum Weiterverhandeln?", "gw", 2170, 160, "L1",
     label=(2198, 112, 130, 27))

# ---------------- lane L2: Agent ----------------
node("Task_Kontext", "serviceTask", "Kontext laden (MCP)", "task", 470, 490, "L2", "code",
     "LangGraph: load_context. Stammdaten, heutige Konditionen und Verhandlungshistorie über den "
     "ERP-Adapter (MCP-Tool get_supplier_context). KW42 JSON-Stub, ab KW43 MCP (ADR 0005).")
node("GW_JoinLoop", "exclusiveGateway", "", "gw", 590, 490, "L2")
node("Task_Pakete", "scriptTask", "Pakete berechnen (Code)", "task", 710, 490, "L2", "code",
     "LangGraph: offer_engine. 2–3 gleichwertige Pakete (MESO) entlang der Konzessionskurve; nur Werte im "
     "Mandat. Variante (c): Startpunkt aus der Verhandlungshistorie. Ab KW43.")
node("Task_Formulieren", "serviceTask", "Angebot formulieren (LLM)", "task", 860, 490, "L2", "llm",
     "LangGraph: narrate. Formuliert die Pakete der offer_engine; Zahlen kommen ausschliesslich aus dem State. "
     "Ohne RAG: kein Richtlinientext an den Lieferanten (ADR 0007). Ab KW43.")
node("Task_Guard", "businessRuleTask", "Nachricht prüfen (Code)", "task", 1010, 490, "L2", "code",
     "LangGraph: mandate_guard. Regelliste: Zahlen im Text = Paketwerte, keine Zusagen ausserhalb Mandat, "
     "kein Walk-away-Leak, KI-Hinweis in der ersten Nachricht. Ab KW43; Basis für Safeguarding KW47.")
node("GW_Guard", "exclusiveGateway", "Mandat eingehalten?", "gw", 1130, 490, "L2",
     label=(1090, 428, 80, 27))
node("Task_Template", "scriptTask", "Standardtext verwenden (Code)", "task", 1240, 640, "L2", "code",
     "LangGraph: template_message. Fail-safe: Vorlage gibt die Pakete wörtlich wieder; Template-Rate ist Metrik.")
node("GW_JoinSend", "exclusiveGateway", "", "gw", 1350, 490, "L2")
node("Task_SendWait", "task", "Angebot senden, Antwort abwarten", "task", 1470, 490, "L2", "code",
     "LangGraph: send_and_wait. Im Projekt: simulierter Lieferant (regelbasiert, ab KW46 zusätzlich LLM); "
     "in der Demo: Chat-Oberfläche. Ab KW42.")
node("Task_Extract", "serviceTask", "Antwort extrahieren (LLM)", "task", 1620, 490, "L2", "llm",
     "LangGraph: parse_response. Strukturierte Ausgabe (Pydantic): Typ, gewähltes Paket, Gegenangebot, "
     "Aussagen mit Typ (Befugnis-Behauptung, Information, Forderung, Bedingung). Ab KW44 mit passender Regel aus "
     "der Einkaufsrichtlinie (RAG, Retrieval fest im Node). Lieferantentext ist untrusted input. Ab KW43.")
node("Task_Assess", "businessRuleTask", "Antwort bewerten (Code)", "task", 1770, 490, "L2", "code",
     "LangGraph: assess_response. Einigung, wenn das gewählte Paket einem gesendeten entspricht oder ein "
     "Gegenangebot im Mandat mindestens so viel wert ist wie das eigene nächste Paket (AC_next). "
     "Eskalation nur, wenn das Mandat den Entscheid nicht abdeckt: Bedingung, die das Mandat nicht regelt, "
     "abgelehnte Forderung wiederholt, oder Antwort nicht auswertbar (Schema ungültig, Paket unbekannt). "
     "Behauptungen über Zusagen ändern das Mandat nie: zurückweisen, protokollieren, weiter (ADR 0008). Ab KW43.")
node("GW_Bewertung", "exclusiveGateway", "Bewertung?", "gw", 1900, 490, "L2",
     label=(1830, 520, 60, 14))
node("Task_EskPrep", "serviceTask", "Eskalation aufbereiten (LLM + Tools)", "task", 2030, 370, "L2", "llm",
     "LangGraph: escalate (vor interrupt). LLM mit zwei Tools: Einkaufsrichtlinie (RAG, KW44) und "
     "Verhandlungshistorie (MCP). Ergebnis: Anlass, betroffene Regeln mit Quelle, Gegenwert, Empfehlung (US4). "
     "Fehler sind hier billig, weil die Einkäuferin entscheidet.")
node("GW_Weiter", "exclusiveGateway", "Weiterverhandeln?", "gw", 1900, 640, "L2",
     label=(1760, 632, 112, 14))
node("GW_JoinFinal", "exclusiveGateway", "", "gw", 2170, 490, "L2")
node("Task_Record", "serviceTask", "Ergebnis im ERP erfassen (MCP)", "task", 2290, 490, "L2", "code",
     "LangGraph: record_outcome (MCP-Tool record_outcome). Auf allen Ausgängen: Konditionen bei Deal, sonst "
     "Ergebnis und Protokoll. Die Historie ist das Lieferanten-Gedächtnis (Variante c, KW46). Ab KW43.")
node("Task_Notify", "sendTask", "Ergebnis mitteilen", "task", 2440, 490, "L2", "code",
     "LangGraph: notify_supplier. Vorlage: Bestätigung, Absage oder Hinweis auf Übernahme. Ab KW43.")
node("GW_Ergebnis", "exclusiveGateway", "Ergebnis?", "gw", 2570, 490, "L2",
     label=(2500, 455, 50, 14))
node("End_Uebergabe", "endEvent", "An Einkäuferin übergeben", "ev", 2670, 370, "L2",
     label=(2635, 395, 70, 27))
node("End_Deal", "endEvent", "Neue Konditionen vereinbart", "ev", 2670, 490, "L2",
     label=(2635, 515, 70, 40))
node("End_KeinDeal", "endEvent", "Kein Deal", "ev", 2670, 640, "L2",
     label=(2645, 665, 50, 14))

# ---------------- data (not in lanes) ----------------
# id, tag, name, kind, cx, cy, label, store
data = [
    ("DO_Mandat", "dataObjectReference", "Mandat", "do", 440, 225, (422, 252, 40, 14), None),
    ("DS_ERP_Read", "dataStoreReference", "ERP-Adapter (Mock): Stammdaten, Konditionen, Historie", "ds",
     470, 640, (395, 670, 150, 40), "DataStore_ERP"),
    ("DS_ERP_Write", "dataStoreReference", "ERP-Adapter (Mock): Stammdaten, Konditionen, Historie", "ds",
     2290, 640, (2215, 670, 150, 40), "DataStore_ERP"),
    ("DS_Richtlinie", "dataStoreReference", "Einkaufsrichtlinie (RAG)", "ds", 1910, 300,
     (1840, 330, 140, 14), "DataStore_Policy"),
]

annotation = ("Legende", 640, 103, 930, 80,
              "Farben: orange = LLM (probabilistisch) · blau = Code (deterministisch) · grün = Mensch.\n"
              "Grundsatz: LLM extrahiert und formuliert, Code entscheidet über Zahlen und Mandat.\n"
              "Ablation: (a) ein LLM-Node übernimmt Pakete, Formulieren, Extrahieren und Bewerten, ohne Prüfung im Code;\n"
              "(b) wie gezeichnet; (c) zusätzlich nutzt «Pakete berechnen» die Historie. Eine Instanz pro Lieferant.")

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
flow("Flow_09", "GW_Guard", "Task_Template", [(1130, 515), (1130, 640), (1190, 640)], "nein",
     "not state.guard_ok", (1100, 580, 22, 14))
flow("Flow_10", "Task_Template", "GW_JoinSend", [(1290, 640), (1350, 640), (1350, 515)])
flow("Flow_11", "GW_JoinSend", "Task_SendWait", [(1375, 490), (1420, 490)])
flow("Flow_12", "Task_SendWait", "Task_Extract", [(1520, 490), (1570, 490)])
flow("Flow_13", "Task_Extract", "Task_Assess", [(1670, 490), (1720, 490)])
flow("Flow_14", "Task_Assess", "GW_Bewertung", [(1820, 490), (1875, 490)])
flow("Flow_15", "GW_Bewertung", "GW_JoinFinal", [(1925, 490), (2145, 490)], "Einigung",
     'state.assessment == "agreement"', (1935, 470, 48, 14))
flow("Flow_16", "GW_Bewertung", "Task_EskPrep", [(1900, 465), (1900, 370), (1980, 370)],
     "Mandat reicht nicht oder unklar", 'state.assessment == "escalate"', (1800, 395, 95, 27))
flow("Flow_17", "GW_Bewertung", "GW_Weiter", [(1900, 515), (1900, 615)],
     "Gegenangebot ungenügend oder Ablehnung", 'state.assessment in ("counter", "reject")',
     (1908, 545, 110, 40))
flow("Flow_18", "Task_EskPrep", "Task_EskEntscheid", [(2030, 330), (2030, 200)])
flow("Flow_19", "Task_EskEntscheid", "GW_Freigabe", [(2080, 160), (2145, 160)])
flow("Flow_20", "GW_Freigabe", "GW_JoinLoop", [(2170, 135), (2170, 90), (590, 90), (590, 465)],
     "ja (ggf. Mandat erweitert)", 'state.escalation_decision == "continue"', (1990, 72, 170, 14))
flow("Flow_21", "GW_Freigabe", "GW_JoinFinal", [(2170, 185), (2170, 465)],
     "nein: abbrechen oder übernehmen", 'state.escalation_decision in ("abort", "takeover")',
     (2178, 270, 95, 27))
flow("Flow_22", "GW_Weiter", "GW_JoinLoop", [(1900, 665), (1900, 720), (590, 720), (590, 515)],
     "ja: Runde < max. Runden, Paket offen, keine endgültige Absage", WEITER, (650, 725, 420, 14))
flow("Flow_23", "GW_Weiter", "GW_JoinFinal", [(1925, 640), (2170, 640), (2170, 515)], "nein",
     f"not ({WEITER})", (1990, 620, 22, 14))
flow("Flow_24", "GW_JoinFinal", "Task_Record", [(2195, 490), (2240, 490)])
flow("Flow_25", "Task_Record", "Task_Notify", [(2340, 490), (2390, 490)])
flow("Flow_26", "Task_Notify", "GW_Ergebnis", [(2490, 490), (2545, 490)])
flow("Flow_27", "GW_Ergebnis", "End_Deal", [(2595, 490), (2652, 490)], "Deal",
     'state.outcome == "deal"', (2605, 470, 26, 14))
flow("Flow_28", "GW_Ergebnis", "End_Uebergabe", [(2570, 465), (2570, 370), (2652, 370)], "übergeben",
     'state.outcome == "handed_over"', (2580, 350, 52, 14))
flow("Flow_29", "GW_Ergebnis", "End_KeinDeal", [(2570, 515), (2570, 640), (2652, 640)], "kein Deal",
     'state.outcome == "no_deal"', (2580, 620, 48, 14))

msgs = [
    ("MsgFlow_Angebot", "Task_SendWait", "Participant_Lieferant", "Angebot (2–3 Pakete)",
     [(1450, 530), (1450, 820)], (1310, 795, 135, 14)),
    ("MsgFlow_Antwort", "Participant_Lieferant", "Task_SendWait", "Antwort",
     [(1490, 820), (1490, 530)], (1498, 795, 40, 14)),
    ("MsgFlow_Ergebnis", "Task_Notify", "Participant_Lieferant", "Bestätigung oder Absage",
     [(2440, 530), (2440, 820)], (2448, 795, 150, 14)),
]

# data associations: (id, kind, task, data, waypoints)
assoc = [
    ("DOA_Mandat", "out", "Task_Mandat", "DO_Mandat", [(410, 190), (422, 208)]),
    ("DIA_ERP", "in", "Task_Kontext", "DS_ERP_Read", [(470, 615), (470, 530)]),
    ("DIA_Richtlinie", "in", "Task_EskPrep", "DS_Richtlinie", [(1935, 300), (2000, 300), (2000, 330)]),
    ("DIA_Richtlinie_Extract", "in", "Task_Extract", "DS_Richtlinie", [(1885, 300), (1620, 300), (1620, 450)]),
    ("DOA_ERP", "out", "Task_Record", "DS_ERP_Write", [(2290, 530), (2290, 615)]),
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

POOL_W = 2590
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
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" id="Definitions_Einkaufsagent" targetNamespace="http://bpmn.io/schema/bpmn" exporter="gen_bpmn_v2.py" exporterVersion="2.0">
{chr(10).join(collab)}
  <bpmn:dataStore id="DataStore_ERP" name="ERP-Adapter (Mock)" />
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

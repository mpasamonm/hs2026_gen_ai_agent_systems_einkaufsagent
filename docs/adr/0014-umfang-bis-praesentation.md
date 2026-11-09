# ADR 0014 – Umfang bis zur Abschlusspräsentation am 23.11.2026

- **Status:** angenommen am 09.11.2026
- **Datum:** 09.11.2026
- **Berührt:** ADR 0009 (MCP als Ausbau), ADR 0010 (Testset, Bias), ADR 0011 (granite-Zeile, Spike Klassifikation),
  ADR 0012 (Demo), ADR 0013 (Kippregeln), ADR 0015 (Memory und Human-in-the-loop)

## Kontext

Am 09.11.2026 bleiben zwei Wochen bis zur Präsentation. Seit dem 19.10.2026 ist auf `main` nur ein Beitrag dazugekommen:
die Umformulierungen der Simulator-Texte (ADR 0010, Nachtrag; PR #2, gemergt am 09.11.2026). Aus dem alten Plan sind
offen: ERP-Adapter mit Protokoll, granite-Zeile, Spike Klassifikation, `_v4`, Testset mit Angriffen und Bias,
Eskalation per `interrupt()`, Mensch als Lieferant, Gedächtnis (c) und optional MCP. Zusammen sind das über 20 h.

Nicht verhandelbar sind Variante (b) und die Ablation (beide erledigt), das Testset mit Angriffen und eine Live-Demo
oder ihre Aufzeichnung. Die trennende Achse ist **Beitrag zur Kernthese und zur Prüfung gegen Zeit**.

## Entscheid

| Baustein | Entscheid | Grund | Kippt, wenn |
| --- | --- | --- | --- |
| ERP-Adapter mit Protokoll, Metrik `korrekt_gebucht` | bauen (Bau 1) | Langzeitgedächtnis und Wochenauftrag «Memory festlegen» (ADR 0015); die Paketwahl pro Lieferant wird gespeichert | – |
| Eskalation per `interrupt()`, Einkäuferin im Terminal | bauen (Bau 1) | Human-in-the-loop, in `_v3` gezeichnet, aber noch nicht gebaut (ADR 0015) | – |
| Mensch als Lieferant im Terminal | bauen (Bau 1) | Grundlage der Demo und der Live-Runden (ADR 0012) | – |
| BPMN `_v4` | bauen (Bau 1, sonst Abschluss) | Prozess und Code müssen übereinstimmen; Abweichungen sind bekannt | – |
| Testset 12–15 Szenarien mit Angriffen | bauen (Bau 2) | Die Kippregeln aus ADR 0008 und 0013 hängen daran; die Präzisierungen im Parse-Prompt sind am Dev-Set entstanden | – |
| Eskalation aufbereiten | Vorlage im Code (Verlauf, Grund, Forderung); Zusammenfassung durch das LLM nur, wenn Zeit bleibt | Die Einkäuferin braucht die Fakten; der LLM-Text ist Komfort | die Vorlage ist in der Demo unlesbar |
| granite-Zeile (`ibm/granite4.1:3b`) | nur, wenn Zeit bleibt (Bau 2) | rund 30 Min.; beantwortet, ob (b) ein 3B-Modell trägt (ADR 0011) | – |
| Bias-Varianten | nur, wenn Zeit bleibt; sonst Limitation | In (b) entscheidet der Code; Unterschiede kämen nur aus der Extraktion | – |
| Spike Klassifikation (ADR 0011) | **gestrichen** | (b) extrahiert mit Luna auch umformulierte Antworten zu 95–98 % richtig (ADR 0010, Nachtrag); `tev1:0.8b` hat im Smoke-Test schon den Injection-Fall falsch gewertet. Der Haken `confidence` bleibt als Ausbau | das Testset zeigt in (b) mehr als 10 % Fehler beim Extrahieren: dann ein kleiner Vergleich nur auf den Fehlfällen |
| Gedächtnis (c) | **gestrichen**, Ausbau in der Präsentation | Checkpointer und Protokoll erfüllen «Memory festlegen»; (c) bräuchte eine Historie per Self-Play und eine eigene Messung (3–4 h) | Bau 1 ist bis 12.11. fertig |
| MCP nur lesend | **gestrichen**, Ausbau in der Präsentation (ADR 0009) | trägt nicht zur Kernthese bei | – |

Reihenfolge, wenn die Zeit nicht reicht: zuerst Bias, dann granite, dann die LLM-Zusammenfassung der Eskalation.

**Zeitplan.** Bau 1 bis 13.11.2026, Bau 2 bis 15.11.2026, danach keine neuen Funktionen. Vom 16. bis 22.11.2026:
SW9 einordnen, voller Eval-Lauf, Ergebnisfolie, 5–10 Live-Runden mit Spielkarte, Folien als PDF, Demo-Probe mit
Aufzeichnung.

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| alles aus dem alten Plan bauen | über 20 h; dann fehlen Zeit für den vollen Eval-Lauf, die Demo-Probe und die Prüfungsvorbereitung |
| nicht mehr bauen, nur noch Eval und Folien | ohne Mensch als Lieferant keine Demo nach ADR 0012, ohne `interrupt()` kein Human-in-the-loop; die Eskalation endet heute mit einer Vorlage |
| Spike statt Testset | Das Testset prüft, ob die Präzisierungen verallgemeinern; der Spike optimiert einen Baustein, der heute schon trägt |

## Kippt, wenn

- Bau 1 bis 14.11. nicht fertig ist: `_v4` in den Abschluss schieben; Testset mit mindestens 8 Szenarien, davon 3
  Angriffe;
- der Proxy in der Demo-Probe unzuverlässig ist: Aufzeichnung statt Live-Demo (ADR 0012). Am 09.11.2026 lieferte
  `ea-check-models` für Luna einmal einen 422-Fehler, die Wiederholung lief.

## Konsequenzen

- ADR 0011: Status «Spike gestrichen (ADR 0014)»; die granite-Zeile bleibt optional.
- `docs/gesamtsystem.md` §3.2, §6 und §9 sowie CLAUDE.md §7 folgen diesem Plan.
- Für die Präsentation: Gedächtnis (c), MCP nur lesend und ein Entscheidungsmodell mit Konfidenz sind Ausbaustufen mit
  Begründung, keine Lücken.

## Nachtrag 09.11.2026: Abgabe am selben Tag, Arbeit auf die Abgabe hin

Die Abgabe ist am 23.11.2026, am Tag der Präsentation: Link auf die ausführbare Lösung (bei uns das Repository),
Projektartefakte und die Präsentation als PDF. Ab jetzt richtet sich die Arbeit nach diesen zwei Abgaben, nicht mehr
nach den Wochenaufträgen des Semesterprogramms. Die Reihenfolge bleibt: Bau 1, Bau 2 (danach Feature-Freeze),
Abgabe-Paket. Neu im Abgabe-Paket: README als Einstieg für die Dozierenden, die Ergebnisse der finalen Läufe versioniert
unter `docs/ergebnisse/` (heute liegt `results/` nicht im Git), eine Prüfung, ob das Repo veröffentlicht werden könnte,
und die Folien als Slides-Artifact mit PDF-Export. Über den Zugriff für die Dozierenden (öffentlich oder Einladung)
entscheidet der Nutzer am Schluss.


## Nachtrag 09.11.2026: Kippregel Gedächtnis (c) geprüft

Bau 1 war am 09.11.2026 fertig, vor dem 12.11. Damit greift formal die Kippregel für Gedächtnis (c). Entscheid des
Nutzers (Empfehlung übernommen): **zuerst das Testset mit Angriffen (Bau 2); (c) nur, wenn danach vor dem 15.11.2026 noch
Zeit bleibt** (3–4 h, Historie per Self-Play und eigene Messung). Grund: Die Kippregeln aus ADR 0008 und 0013 hängen am
Testset, (c) ist ein Ausbau ohne offene Prüffrage. Reicht die Zeit nicht, bleibt (c) Ausbau in der Präsentation.

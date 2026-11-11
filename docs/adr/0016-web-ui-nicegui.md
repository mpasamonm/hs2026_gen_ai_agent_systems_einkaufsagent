# ADR 0016 – Web-UI mit NiceGUI über dem Runner

- **Status:** angenommen und gebaut am 10.11.2026
- **Datum:** 10.11.2026
- **Berührt:** ADR 0012 (Demo über Web-UI, Nachtrag), ADR 0014 (Ausnahme vom Feature-Freeze, Nachtrag), ADR 0015
  (Kippregel «Web-UI», Nachtrag)

## Kontext

Die Demo läuft über eine schlanke Web-UI als reine Darstellung über `live.run_live` (ADR 0012 und 0014, Nachträge). Offen
war die Bibliothek. Vorgabe des Nutzers: Die UI muss für die Demo bereit sein; kurz vorher testen, neu starten und dann
die Demo zeigen muss ohne Umwege gehen. Technisch läuft der Graph synchron, und `ask` blockiert, bis ein Mensch antwortet.
Die UI startet den Runner deshalb in einem Hintergrund-Thread und reicht die Eingaben aus dem Browser weiter.

Die trennende Achse ist, **wo der blockierende Lauf lebt: in der Browser-Sitzung oder im Server-Prozess**. Hängt er an
der Sitzung, geht er bei einem Reload der Seite verloren. Unter den Bibliotheken, die ihn im Server halten, trennen
Grösse, Telemetrie und Netzbedarf.

Recherche am 09.11.2026: Versionen und Daten auf PyPI, API in der Doku und im installierten Paket geprüft. In allen vier
Bibliotheken lief ein Prototyp über dem echten `run_live` im Headless-Browser durch (S11 mit Eskalation, S04 mit Mensch).
Bei keiner ändert sich ein gepinntes Paket im Lockfile.

## Entscheid

**NiceGUI 3.18.0** (MIT, Release 07.10.2026, [stable]), gepinnt als normale Abhängigkeit, damit `uv sync` und
`uv run ea-ui` ohne weitere Optionen reichen. Die 4.0.0 vom 04.11.2026 ist eine neue Hauptversion ([emerging]) und wird
bewusst nicht genommen. Dazu kommen 33 Pakete (+65 MB). NiceGUI hat keine Telemetrie und liefert Vue, Quasar, Tailwind und
die Schriften mit; die Seite braucht zur Laufzeit kein Internet.

**Bauweise**
- `live.py`: optionaler Callback `emit` mit strukturierten Ereignissen (start, memory, round, step, message, escalation,
  ask, report). Ohne `emit` bleibt das Terminal byte-gleich (geprüft über sechs Pfade, Test
  `test_emit_does_not_change_terminal_output`).
- `ui_session.py`: `Session` ohne NiceGUI. Sie startet `run_live` im Thread und blockiert `ask` an einer Queue. Eine
  Eingabe wird nur angenommen, wenn der Lauf genau darauf wartet (Lieferant, Entscheid, Zustimmung); sonst wird sie
  verworfen und rutscht nicht in eine spätere Frage. `cancel()` beendet einen laufenden oder wartenden Lauf. Fehler
  erscheinen auf der Seite, statt den Thread still zu beenden. Offline getestet (`tests/test_ui_session.py`).
- `ui.py`: Seite mit dem Chat links und rechts den Karten für Eskalation (Grund, Hinweise, Verlauf, Notiz, zwei Knöpfe)
  und Zustimmung (`deal:not_agreed`), der Auswertung gegen die Spielkarte und den Schritten in den BPMN-Farben aus
  `gen_bpmn_v4.py`. Ein Timer (0,25 s) überträgt neue Ereignisse. Einstieg `ea-ui`.

**Demo-Bereitschaft**
- «Neue Verhandlung» bricht einen laufenden Lauf nach einer Rückfrage ab und startet sofort neu; ein Reload der Seite zeigt
  denselben Stand, auch mitten in der Eskalation.
- ERP wählbar: die Demo-Datei (Langzeitgedächtnis über Läufe) oder «nur im Speicher» für Proben ohne Spuren in der
  Demo-Datei.
- Modell wählbar: Luna oder «offline» (Vorlage + Regex) für den Fallback ohne Proxy, zum Beispiel S11 mit dem Simulator.
- Jeder Lauf schreibt seine Ereignisse als JSONL nach `results/ui/` (für die Tabelle der Live-Runden). Die Server-Konsole
  zeigt dieselbe Ausgabe wie das Terminal.
- Der Server lauscht nur auf `127.0.0.1`. Der Windows-Browser erreicht die Seite unter WSL (Netzwerkmodus `mirrored`)
  über `http://127.0.0.1:8080`, nicht über `localhost` (dort Timeout, vermutlich IPv6 zuerst).

## Verworfene Alternativen

| Alternative | Grund |
| --- | --- |
| Gradio 6.30.0 (Apache-2.0) | hält den Lauf im Server, fragt aber alle 0,5 s nach; +235 MB (numpy, pandas); Telemetrie an `api.gradio.app` standardmässig an. Zweite Wahl, falls NiceGUI in der Probe versagt |
| Streamlit 1.66.1 (Apache-2.0) | Das Rerun-Modell arbeitet gegen den blockierenden Thread; Fallstricke (`st.html("")`, E-Mail-Abfrage beim ersten Start, lauscht auf allen Schnittstellen); +379 MB; Telemetrie aus dem Browser standardmässig an |
| Chainlit 2.12.0 (Apache-2.0) | Der Lauf hängt an der Websocket-Sitzung, ein Reload verliert ihn; +107 Pakete (u.a. `mcp`, OpenTelemetry), Schriften und KaTeX aus dem Netz; seit Mai 2025 von der Community gepflegt |
| LangGraph Studio | verlangt `interrupt()` für den Lieferanten und eine neue Messung (ADR 0012, Nachtrag) |

## Kippt, wenn

- die Seite in der Probe auf dem Präsentationsrechner ruckelt oder nicht läuft: dann Gradio 6.30.0 oder die Demo im
  Terminal (`ea-run --human`, ADR 0012);
- die UI einen Neustart des Prozesses überdauern oder mehrere Verhandlungen gleichzeitig führen soll: dann `interrupt()`
  für den Lieferanten und `SqliteSaver` (ADR 0015, Nachtrag).

## Konsequenzen und Prüfung (10.11.2026)

- Keine Änderung an Graph, Prompts, Regeln oder Eval, deshalb keine neue Messung. 85 Tests grün (6 neu), ruff sauber;
  die Canary-Prüfung gilt auch für die Ereignisse und das JSONL der UI.
- Headless-Browser offline: S11 mit Eskalation, Reload mitten in der Eskalation, Neustart mitten in einer Eskalation,
  S04 mit Mensch bis zur Auswertung.
- Mit Luna die vier Demo-Sätze aus `docs/demo.md` (nach einem Vorlauf mit dem Simulator): Behauptung zurückgewiesen,
  kein Leak, Eskalation, «weiterverhandeln», Abschluss in Runde 4 mit CHF 4'000, Anteil 0.52, keine Verstösse, also
  dasselbe Ergebnis wie die Probe des Nutzers. Der Agent brauchte 2–4 s pro Runde.
- Befund aus dem Browser-Test, behoben: Das Eingabefeld blieb nach dem Senden bis zum nächsten Tick aktiv, eine schnelle
  zweite Eingabe wurde ohne Rückmeldung abgewiesen. Jetzt sperrt die Seite sofort und meldet, wenn der Agent am Zug ist.
- Die Prototypen der Recherche liegen nicht im Repo.

## Nachtrag 10.11.2026: lesbare Seite (Rollen, Mandat, Begriffe)

**Anlass.** Bei der Vorbereitung von Etappe 5 war auf der Seite nicht sofort klar, wer welche Rolle spielt und was die
Begriffe bedeuten (Spielkarte, Protokoll und Konditionen im ERP, Verstösse, Knotennamen wie `narrate`). Die Seite zeigt die
Sicht des Lieferanten (Chat) und die interne Sicht des Einkaufs (Schritte, Eskalation, Auswertung) nebeneinander, ohne das
zu sagen, und das Mandat, gegen das der Code entscheidet, war gar nicht zu sehen. Bei Pactum sieht der Lieferant nur den
Chat über den Link aus der Einladungs-E-Mail; der Einkauf sieht Konfiguration, Dashboard, Eskalationen und Audit-Trail
(`docs/gesamtsystem.md` §2.5).

Trennende Achse: **wie stark die Demo die beiden Sichten trennt.**

| Alternative | Grund |
| --- | --- |
| A: nur Erzählung (Folie, Moderation), Seite unverändert | Die Seite selbst bliebe unverständlich, auch im Bildschirmvideo und für die Dozierenden im Repo |
| B: zwei Ansichten `/lieferant` und `/einkauf` in zwei Fenstern | Am Beamer sieht man ein Fenster oder beide nebeneinander, also wieder eine Seite; die Kernthese steht nur in der Innensicht; rund 3–4 h und mehr bewegliche Teile in der Demo |
| **C+: eine Seite, beschriftet (gewählt)** | kleinster Schritt, der die Verwirrung auf dem Bildschirm selbst behebt |

**Entscheid des Nutzers (10.11.2026): C+.** Nur Darstellung in `ui.py` und neu `ui_text.py` (ohne NiceGUI, offline
getestet); Graph, Prompts, Regeln, Eval und `live.py` bleiben unverändert, die Terminal-Ausgabe ebenso.
- Links «Sicht des Lieferanten» mit dem Hinweis, dass real der Link aus der Einladungs-E-Mail dorthin führt. Die Frage
  «Stimmen Sie zu?» steht jetzt dort zwischen Chat und Eingabefeld, weil sie der Lieferant beantwortet (real: Vertrag zur
  Signatur).
- Rechts «Intern: Einkauf der Musterhandel AG · sieht der Lieferant nicht». Oben die Karte «Mandat der Einkäuferin» mit
  heutigen Konditionen, Ziel, Grenzen, Mindestnutzen, Bewertungssätzen in CHF, wer es liest (nur Code) und Quelle. Sie ist
  zugeklappt, damit eine Person in Live-Runden den Mindestnutzen nicht sieht; in der Demo öffnet sie die Moderation. Die
  Werte stammen nur aus dem öffentlichen Teil des Szenarios (Test mit Canary).
- Schritte mit dem Namen der BPMN-Aufgabe («Angebot formulieren»), darunter klein der Knoten im Code (`narrate`). Die
  Felder von `parse_response` stehen auf Deutsch mit dem Code in Klammern, z.B. «nimmt an (accept) · Paket B · Bedingung
  zu Vertragslaufzeit (condition/contract_term)».
- Auswertung: unter jeder Zeile eine kurze Erklärung (Protokoll = Audit-Trail, Konditionen im ERP, Spielkarte und Anteil
  am Spielraum, Verstösse); Verstösse zusätzlich mit deutscher Bedeutung.
- Kopfzeile mit der Legende «LLM schlägt vor · Code entscheidet · Mensch entscheidet den Rest».

**Prüfung.** 89 Tests grün (4 neu in `tests/test_ui_text.py`, darunter: jeder Knoten des Graphen hat einen BPMN-Namen),
ruff sauber. Headless-Browser offline: S11 mit Simulator bis zur Eskalation (Mandat aufgeklappt) und zur Auswertung, S04
mit Mensch bis zur Zustimmung. Die Zustimmungskarte sitzt über dem Eingabefeld, damit sie bei 1000 px Fensterhöhe sichtbar
bleibt. Mit Luna nicht neu gemessen, weil sich nur Texte und Anordnung ändern; die Demo-Probe prüft den Ablauf.

**Kippt, wenn** Personen in den Live-Runden rechts mitlesen und ihr Verhalten danach ausrichten: dann eine Ansicht
`/lieferant` nur mit Chat und Zustimmung (Variante B), vor dem Stichtag 15.11.

## Nachtrag 11.11.2026: Einladung vor dem Chat (Gegenstand und freie Antwort sichtbar)

**Anlass.** In einer Probe des Nutzers (S04, Luna, 10.11.2026) entstand das Gefühl, nur unter den drei Paketen wählen zu
können. Das Protokoll zeigt: Der Agent lud in jeder Runde zum Gegenvorschlag ein («Bitte wählen Sie eines der folgenden
Pakete oder unterbreiten Sie uns einen Gegenvorschlag»), und der Nutzer konterte auch («90 Tage mit 2 % Rabatt»), aber
ohne Mengenzusage und damit für ihn teurer als jedes unserer Pakete (Befund in `docs/demo.md` §1). Gefehlt hat der
Rahmen: worum es geht und was die drei Grössen bedeuten. Real erfährt der Lieferant das aus der Einladung per E-Mail
(Walmart-Ablauf, Schritt 3, `docs/gesamtsystem.md` §2.5); die fehlte bei uns.

Trennende Achse: **wo der Lieferant den Rahmen der Verhandlung erfährt.**

| Alternative | Grund |
| --- | --- |
| U1: Hinweis unter dem Eingabefeld | wiederholt nur den Satz des Agenten; erklärt weder den Gegenstand noch die Mengenzusage |
| **E: Einladung als erste Nachricht links (gewählt)** | entspricht der E-Mail im realen Ablauf; zeigt Gegenstand (ADR 0001, Nachtrag 11.11.) und freie Antwort auf der Seite, auch im Video |
| U2: Schnellantworten, die das Eingabefeld vorbefüllen | realistisch (Pactum mischt Klick-Optionen und Freitext), aber mehr bewegliche Teile in der Demo; bleibt Kippoption |
| U3: Agent fragt von sich aus nach einer Gegenleistung | Prompt-Änderung (Feature-Freeze, neue Messung); 2024–2026 auch bei Pactum nicht belegt; Limitation und Ausbau in `docs/gesamtsystem.md` §5 und §6 |

**Entscheid des Nutzers (11.11.2026): E.**
- `ui_text.invitation_text` erzeugt die Einladung aus dem öffentlichen Teil des Szenarios: Gegenstand (Konditionen für
  alle Bestellungen der nächsten 12 Monate, Volumen im Vorjahr), heutige Konditionen, Bedeutung von Zahlungsziel, Rabatt
  und Mengenzusage, «Antworten Sie frei: Wählen Sie ein Paket, machen Sie einen eigenen Vorschlag oder lehnen Sie ab»,
  Hinweis auf die Einkäuferin. Kein Ziel, keine Grenze, kein Mindestnutzen (Test mit Canary und Mandatswerten).
- Grau als erste Nachricht im Chat, beschriftet «Einladung per E-Mail · vor dem Chat (Vorlage, nicht vom Agenten)»; sie
  steht auch beim Simulator da, der sie nicht liest.
- Platzhalter des Eingabefelds: «Freie Antwort: Paket wählen, eigener Vorschlag oder ablehnen · Enter sendet».
- Spielkarten mit dem Gegenstand und dem Satz, dass eigene Werte und Tauschgeschäfte erlaubt sind (`docs/demo.md` §4).
- Graph, Prompts, Regeln, Eval und `live.py` unverändert; die Einladung erreicht keinen Prompt und kein Protokoll.

**Prüfung.** 90 Tests grün (1 neu), ruff sauber. Headless-Browser offline (S04, Simulator, 1600 × 1000 px): Einladung über
der ersten Nachricht des Agenten, Platzhalter sichtbar, Verlauf und Auswertung unverändert (Abschluss nach Runde 1,
CHF 5'250, Anteil 0.84). Mit Luna nicht neu gemessen, weil sich nur der Text der Seite ändert.

**Kippt, wenn** die Einladung in der Demo-Probe am Beamer zu viel Platz frisst (dann auf zwei Sätze kürzen); U2, wenn
Personen in den Live-Runden trotz Einladung nur Pakete wählen oder nie über die Mengenzusage verhandeln.

## Nachtrag 11.11.2026: Wortlaut «Grenzen» der Mandat-Karte (Entscheid B)

Anlass: Red-Teaming R6 (`docs/demo.md` §3). Ein Gegenangebot mit 95 Tagen nahm der Code an, die Mandat-Karte nannte
«Zahlungsziel höchstens 90 Tage» aber eine Grenze. `check_terms` prüft nur Grenzen zulasten der Musterhandel AG;
`payment_days_max` und `discount_max_pct` halten ZOPA-Analyse und `offer_engine` nur bei eigenen Paketen ein.
Entscheid des Nutzers (11.11.): B, nur den Wortlaut präzisieren, keine neue Regel (Feature-Freeze; eine Regel wäre eine
Änderung an `check_terms` mit neuer Messung).
- `ui_text.mandate_lines`: «Grenzen» nennt nur, was der Code bei jedem Angebot und Abschluss prüft (Mengenzusage
  höchstens, keine Preiserhöhung, Zahlungsziel und Rabatt nicht unter heute, Rundenlimit). Neue Zeile «Richtlinie»:
  Zahlungsziel und Rabatt höchstens …, «nur für unsere Pakete; ein Gegenangebot darüber darf der Code annehmen».
- Test `test_mandate_in_words_only_from_public_part` angepasst. 90 Tests grün, ruff sauber; Karte im Headless-Browser
  offline geprüft (S04, 1600 × 1000 px, eine Zeile mehr, ohne Scrollen lesbar).

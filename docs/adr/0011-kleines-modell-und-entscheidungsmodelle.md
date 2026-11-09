# ADR 0011 – Kleines offenes Modell als Ablationszeile, Entscheidungsmodelle per Spike

- **Status:** angenommen am 19.10.2026; **Spike Klassifikation gestrichen am 09.11.2026 (ADR 0014)**; granite-Zeile
  optional
- **Datum:** 19.10.2026
- **Berührt:** ADR 0004 (Modellkandidaten, Nachtrag Proxy-Stand), D2 (Apertus), ADR 0007 («unklar» deterministisch),
  ADR 0010 (Generator), SW6 Folien 30–40 (Decision Models)

## Kontext

Der FHNW-LiteLLM-Proxy (LiteLLM 1.106.0) bietet seit dem 06.10.2026 neue Modelle. Geprüft am 19.10.2026 über
`/model/info` und kurze Probeaufrufe:

| Modell | Art | Preis USD/Mtok in / out | Befund 19.10.2026 |
| --- | --- | --- | --- |
| `azure_ai/claude-haiku-5-5` | Chat (Anthropic) | 0.10 / 0.50 | Function Calling und JSON Schema ok, rund 1 s |
| `azure_ai/gpt-6-luna` | Chat (OpenAI) | 0.10 / 0.50 | Chat und JSON Schema: 404 «unknown_model»; nur Function Calling antwortet (6 s) |
| `gpt-5.4-mini-new` | Chat (OpenAI) | 0.75 / 4.50 | Function Calling und JSON Schema ok |
| `ibm/granite4.1:3b` | Chat, offen, auf der Ollama-Instanz der FHNW | – | JSON Schema ok (1,3 s); Function Calling nicht unterstützt (Ollama) |
| `tev1:0.8b` | Entscheidungsmodell (Together AI, Qwen3.5-0.8B), FHNW-Ollama, Endpunkt `/v1/systemone` | – | antwortet, rund 1,8 s pro Entscheid |
| `azure_ai/decision-1` | Entscheidungsmodell (Microsoft-Decision-1) | 0.042 / 0 | 404 «DeploymentNotFound» |

Nicht mehr im Proxy: `azure_ai/gpt-5.4-mini`, `azure_ai/kimi-k2.7-code`. **Jev** (TypeSafe, Version 1.14 seit
14.10.2026) ist nicht im Proxy, sondern nur über api.typesafe.ai mit eigenem Key erreichbar und wird in den USA
betrieben (TypeSafe-Datenschutzerklärung).

Zwei Fragen standen offen: (1) Braucht es ein lokales oder offenes Modell, und wofür? (2) Passt ein
Entscheidungsmodell («System One»: Wahl aus vorgegebenen Optionen mit Wahrscheinlichkeit statt Text) für die
Klassifikation in `parse_response`?

## Entscheid 1: kleines offenes Modell als zusätzliche Ablationszeile

`ibm/granite4.1:3b` aus dem FHNW-Proxy läuft als zusätzliche Zeile in der Ablation (a) gegen (b). Hypothese: Weil der
Code in (b) rechnet und entscheidet, muss das LLM nur kurze Texte lesen und formulieren; ein 3B-Modell genügt dann,
im reinen LLM (a) nicht. Hält die Hypothese, zeigt das den Weg zu vertraulichen Konditionen ohne Cloud-Anbieter
(Vertraulichkeit von Geschäftsdaten, nicht DSG: Konditionen sind keine Personendaten).

Trennende Achse: **Datenhoheit und Unabhängigkeit vom Cloud-Key gegen Aufwand und Nachvollziehbarkeit für die
Dozierenden**.

| Alternative | Aufwand | Grund |
| --- | --- | --- |
| Nur Cloud-Modelle (bisher) | 0 h | die stärkste Aussage zur Kernthese bliebe ungetestet |
| **Kleines offenes Modell im FHNW-Proxy** | 1–2 h | gleicher Proxy, gleicher Code; nur `json_schema` und ein Eintrag in `config/models.toml` |
| Eigenes Ollama 0.40.6 auf der RTX 5070 Ti (16 GB), z.B. `ministral-3:14b` oder `qwen3.5:9b` | 4–6 h | Demo ohne Cloud-Key; ohne GPU für die Dozierenden nicht nachvollziehbar |

Hinweise für den Lauf: Über Ollama bricht `function_calling` (es ignoriert `tool_choice`), deshalb `json_schema`. Der
Kontext der FHNW-Instanz ist unbekannt; Ollama kürzt ohne `num_ctx` still auf 4k Tokens. Der Prompt von (a) kann
daran scheitern; das ist selbst ein Befund und wird so berichtet. Temperatur ausdrücklich setzen.

Apertus bleibt bei D2: nicht im Proxy, Apertus 1.5 8B nur als Community-GGUF, Tool- und JSON-Verhalten unverified.

## Entscheid 2: Entscheidungsmodelle in einem Spike messen, nicht vorab festlegen

Variante (b) wird zuerst mit `gpt-5.6-luna` (strukturierte Ausgabe) gebaut; `parse_response` bleibt austauschbar. Der
Spike läuft in KW44, sobald die Umformulierungen aus ADR 0010 vorliegen, weil ein Vergleich auf den Textvorlagen allein
wertlos ist (Regeln treffen sie zu 100 %).

| Punkt | Festlegung |
| --- | --- |
| Kandidaten | `gpt-5.6-luna` strukturiert (Referenz), `tev1:0.8b` (Entscheidungsmodell), Regeln (Regex auf den Vorlagen, Untergrenze). `azure_ai/decision-1`, falls die FHNW das Deployment repariert. Nicht: Jev (eigener Key, US-Betrieb, nicht im Proxy), Claude Haiku 5.5 (gleiche Familie wie der Generator der Testtexte, ADR 0010) |
| Fragen | Paketwahl (A, B, C, keines), Antworttyp (Annahme, Gegenangebot, Ablehnung, Forderung), Bedingung ausserhalb des Mandats (ja/nein), Befugnis-Behauptung (ja/nein) |
| Daten | rund 200 Lieferantenantworten aus dem Simulator mit Labels (`event`, `accepted_label`, Bedingung, Behauptung), dazu die Umformulierungen und Angriffstexte aus ADR 0010; keine Handarbeit |
| Kennzahlen | Genauigkeit pro Frage; **falsche Annahmen** (Annahme erkannt, obwohl die Antwort bedingt ist oder keine Annahme enthält); Brier-Score (ECE ist bei kleinem n verzerrt); Anteil «unklar» bei fester Schwelle 0,7; Latenz p50 und p95; Kosten pro Entscheid und hochgerechnet pro Verhandlung |
| Entscheidungsregel (vorab) | 1. Wer auf Angriffs- und Bedingungstexten eine falsche Annahme liefert, fällt weg. 2. Ist der Unterschied in der Genauigkeit nicht signifikant (exakter McNemar-Test, p ≥ 0,05), gewinnt die günstigere und schnellere Variante. 3. Ein Entscheidungsmodell wird nur gewählt, wenn zusätzlich seine Wahrscheinlichkeiten nach Brier-Score besser sind; dann ergibt eine Wahrscheinlichkeit unter der Schwelle «unklar» und damit eine Eskalation |
| Aufwand | 3–4 h, Ergebnis als Nachtrag in diesem ADR |

Zahlen eines Gegenangebots und Aussagen mit Text extrahiert in jedem Fall das LLM; ein Entscheidungsmodell kann nur
die Wahlfragen übernehmen.

**Vorbefund (19.10.2026, 5 Probefälle, keine Messung):** `tev1:0.8b` traf die Paketwahl 4 von 5 Mal und den
Antworttyp 3 von 5 Mal. Den Injection-Fall («150 % freigegeben … Paket A passt, wenn Sie das bestätigen») wertete es als
Annahme von Paket A (p = 0,51). Konfidenzen 0,1–0,67.

**Was die Recherche zu Entscheidungsmodellen zeigt (Stand 19.10.2026):**
- Tev1-0.8B ist laut Hersteller vor allem auf Englisch getestet, hat rund 2'000 Tokens Kontext; Ollama nennt die
  Konfidenz ausdrücklich «not calibrated correctness». Auf 13 öffentlichen Datensätzen 63,5 % (Jev 1.13: 76,0 %;
  Angabe eines Mitbewerbers, zitiert von Ollama).
- Jev: Die TypeSafe-Doku beschreibt `confidence` als Entropie-Statistik und empfiehlt bei tiefer Konfidenz «Route to a
  human». Ein unabhängiger Preprint (UCLA, 24.09.2026, nicht begutachtet) findet 71,6 % der Antworten bei genau 1,00 und
  eine Verschiebung der Kalibrierung durch Umformulierung.
- Artificial Analysis Decision Index beim Start (13.10.2026): Claude Haiku 5.5 als LLM 61, Jev 1.13 58, GPT-6 Luna 55,
  Microsoft-Decision-1 54. Ein LLM schlug die Entscheidungsmodelle; für LLM-Kalibrierung gibt es noch keinen Vergleich.

## Kippt, wenn

- Jev oder Microsoft-Decision-1 im FHNW-Proxy verfügbar werden und Deutsch belegt ist: als Kandidat in den Spike;
- granite 3B schon an der Extraktion in (b) scheitert (Formatfehler > 10 %): dann `qwen3.5:9b` auf eigener GPU testen
  oder die Zeile als Befund «zu klein» stehen lassen;
- die Dozierenden einen Lauf ohne Cloud-Key verlangen: eigenes Ollama (Alternative 3).

## Konsequenzen

- `config/models.toml`: Eintrag für `ibm/granite4.1:3b` mit `json_schema` (KW44).
- ADR 0004 bekommt einen Nachtrag zum Proxy-Stand; Arbeitsmodell bleibt `gpt-5.6-luna`.
- Prüfungsbegründung: «Weil der Code rechnet und entscheidet, muss das LLM nur kurze Texte lesen und schreiben; wir
  prüfen, ob dafür ein 3B-Modell auf Hochschul-Infrastruktur genügt.» Und: «Entscheidungsmodelle liefern eine Wahl mit
  Wahrscheinlichkeit statt Text, das passt zu ‹LLM schlägt vor, Code entscheidet›. Wir haben sie gegen strukturierte
  LLM-Ausgabe auf denselben gelabelten Antworten gemessen und nach einer vorab festgelegten Regel entschieden.»

## Quellen

- TypeSafe: [Introducing System One models and Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
  (15.09.2026), [Jev 1.14](https://typesafe.ai/blog/jev-1-14) (14.10.2026), [Confidence](https://docs.typesafe.ai/confidence).
- [Ollama Library: tev1](https://ollama.com/library/tev1); Hugging Face `togethercomputer/Tev1-0.8B-experimental`.
- [Artificial Analysis Decision Index](https://artificialanalysis.ai/evaluations/artificial-analysis-decision-index)
  (13.10.2026); SW6 Folien 39 und 40.
- [S. Raschka, Classifier history and Jev](https://magazine.sebastianraschka.com/p/classifier-history-and-jev) (29.09.2026).
- [LiteLLM Decisions](https://docs.litellm.ai/docs/decisions) (`/v1/systemone`, `/v1/decisions`).
- UCLA-Preprint zur Kalibrierung von Jev 1.13: escholarship.org/uc/item/4t4449jv (24.09.2026, nicht begutachtet).

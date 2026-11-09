# Umformulierungen der Simulator-Vorlagen (ADR 0010)

Eingefroren am 26.10.2026. **Nie neu erzeugen**; eine Änderung ist eine neue Datei mit eigenem Datum (D4, hermetische
Evals).

| | |
| --- | --- |
| Datei | `supplier_templates.json` |
| Generator | Claude Opus 5.5 (`claude-opus-5-5`) über Claude Code, Session vom 26.10.2026 |
| Umfang | 14 Vorlagen × (Original + 5 Umformulierungen), dazu 6 Schreibweisen der Konditionen |
| Auswahl | `SupplierSimulator(..., paraphrase=True)` bzw. `--paraphrase` in `ea-run`, `ea-eval`, `ea-benchmark`; eigener Zufallsgenerator mit dem Seed des Szenarios |
| Code-Prüfung | `paraphrases.validate()` (Test `tests/test_paraphrases.py`) |
| Stichprobe | `stichprobe.md`, erzeugt mit `uv run python scripts/sample_paraphrases.py --neu` (jede Vorlage mindestens einmal; ohne `--neu` bleibt eine bestehende Datei stehen) |

## Was umformuliert ist und was nicht

- **Umformuliert:** alle Sätze mit Bedeutung für die Extraktion: Annahme (mit und ohne Paketlabel), Annahme unter
  Bedingung, Gegenangebot, Ablehnung ohne Spielraum, letztes Wort, letztes Angebot, Preisforderung (erste und
  wiederholte), Bestätigung, «entspricht nicht unserem Vorschlag», «kein Angebot gemacht», Abbruch. Dazu die
  Schreibweise der Konditionen (Reihenfolge, «%» oder «Prozent», Trennzeichen, Synonyme wie Zahlungsfrist, Nachlass,
  Vorjahresmenge).
- **Nicht umformuliert:** die Einleitungen pro Charakter (tragen keine Bedeutung) und die Texte aus den Szenarien
  (Begründung der Preisforderung, Injection, Bedingung). Diese gehören zum Testset und zu den Angriffen (KW45).
- Index 0 ist das Original. Ohne `--paraphrase` ist der Simulator byte-gleich zu vorher; alle bisherigen Zahlen
  bleiben gültig.

## Prompt (sinngemäss, in der Session gestellt)

Der Wortlaut wurde nicht gespeichert; ADR 0010 (Schritt 4) verlangt ihn neben den Daten. Nachgefragt am 09.11.2026.

> Du schreibst Umformulierungen für einen regelbasierten Lieferanten-Simulator. Zu jeder Vorlage genau 5 Varianten auf
> Deutsch (Schweizer Rechtschreibung, «ss»), Ton eines kleinen Lieferanten im Geschäftsbrief. Pflicht: dieselbe
> Bedeutung und dasselbe Ereignis (annehmen, Gegenangebot, ablehnen und gesprächsbereit bleiben, Gespräch beenden,
> Preis fordern). Die Platzhalter `{opener}`, `{terms}`, `{label}`, `{cond}`, `{reason}`, `{pct}` genau so übernehmen;
> keine eigenen Zahlen, Fristen oder Werte. Eine Ablehnung mit offenem Gespräch darf nicht wie ein Abbruch klingen und
> umgekehrt. Bevorzugt andere Satzstellung und andere Schlüsselwörter als das Original, damit eine Regex auf das
> Original nicht greift. Für die Konditionen 5 Schreibweisen, die jede Zahl genau einmal nennen.

## Prüfung

1. **Code** (`validate`): gleiche Platzhalter wie das Original, keine eigenen Zahlen, keine Dubletten; gerendert mit
   Beispielwerten stehen genau die Zahlen des Originals im Text. Test: gleiche Ereignisse und Konditionen mit und ohne
   Umformulierung in allen 11 Szenarien.
2. **Von Hand:** 20 Zeilen in `stichprobe.md`. Kippregel: mehr als 2 Fehler → Prompt verschärfen und neu erzeugen,
   bevor die Daten gelten. Die erste Stichprobe (26.10.2026) deckte 3 der 14 Vorlagen nicht ab (`counter`,
   `accept_label`, `conditional_single`) und war nur vom Generator gelesen; am 09.11.2026 neu gezogen, jede Vorlage
   mindestens einmal. **Die Lesung von Hand steht aus** (Spalte «ok?» ausfüllen, Person und Datum hier eintragen).

## Grenzen

- `reject_no_room` (Index 2 und 4), `counter` (Index 3) und `last_offer` (Index 2) verwenden «entgegenkommen»; das Wort
  steht auch im Beispiel des Parse-Prompts («ohne Entgegenkommen geht das nicht»), das am Dev-Set entstanden ist
  (ADR 0013). Ebenso nennt die Schreibweise 4 der Konditionen «auf die Listenpreise» (Prompt-Beispiel: «höhere
  Listenpreise»). Für diese Varianten ist die Messung vermutlich zu günstig. Das Testset (KW45) meidet beide Wortfelder.
- Die Schreibweisen 1 und 5 der Konditionen ergeben in einigen Vorlagen ungrammatische Sätze («mit ein Zahlungsziel»).
- Die Variante hängt am Seed des Szenarios und ist in allen Wiederholungen gleich; `pass^3` misst damit Streuung des
  Modells, nicht sprachliche Vielfalt.

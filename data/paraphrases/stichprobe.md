# Stichprobe Umformulierungen (ADR 0010)

Je Zeile prüfen: gleiche Bedeutung, gleiches Ereignis (annehmen, Gegenangebot, ablehnen, Abbruch …), gleiche Zahlen. Befund in die letzte Spalte; mehr als 2 Fehler von 20 → Prompt verschärfen, neu erzeugen.

| # | Vorlage | Original | Umformulierung | ok? |
| --- | --- | --- | --- | --- |
| 1 | accept_single[4] | Danke für Ihre Nachricht. Wir nehmen Ihren Vorschlag an: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. | Danke für Ihre Nachricht. Abgemacht, wir nehmen das so an: 45 Tage Zahlungsziel, 1.75 % Rabatt und eine Mengenzusage von 60 % des Vorjahresvolumens. | |
| 2 | conditional_label[1] | Danke für Ihre Nachricht. Paket B passt für uns: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. Das gilt nur, wenn Sie den Rahmenvertrag verlängern. | Danke für Ihre Nachricht. Paket B wäre für uns grundsätzlich machbar: ein Zahlungsziel von 45 Tagen, ein Rabatt von 1.75 % sowie Ihre Zusage über 60 % des letztjährigen Volumens. Das gilt nur, wenn Sie den Rahmenvertrag verlängern. | |
| 3 | confirm[1] | Einverstanden, damit haben wir eine Einigung: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. | Sehr gut, dann ist es abgemacht: 45 Tage Zahlungsziel, 1.75 % Rabatt und eine Mengenzusage von 60 % des Vorjahresvolumens. | |
| 4 | confirm[4] | Einverstanden, damit haben wir eine Einigung: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. | Gut, dann gilt ab sofort: 45 Tage Zahlungsziel, 1.75 % Rabatt und eine Mengenzusage von 60 % des Vorjahresvolumens. | |
| 5 | decline[2] | Das entspricht nicht unserem Vorschlag. Unser Angebot war: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. | Das haben wir so nicht vorgeschlagen. Unser Gegenangebot lautete Zahlungsfrist 45 Tage; Rabatt 1.75 Prozent; zugesagtes Volumen 60 Prozent des Vorjahres. | |
| 6 | decline[3] | Das entspricht nicht unserem Vorschlag. Unser Angebot war: Zahlungsziel 45 Tage, Rabatt 1.75 %, Mengenzusage 60 % des Vorjahresvolumens. | Diese Werte stammen nicht von uns. Zur Erinnerung, unser Vorschlag: 45 Tage Zahlungsziel, 1.75 % Rabatt und eine Mengenzusage von 60 % des Vorjahresvolumens. | |
| 7 | demand_first[1] | Danke für Ihre Nachricht. Bevor wir über Zahlungsziele sprechen: Die Rohstoffpreise sind gestiegen. Wir müssen die Preise deshalb ab dem nächsten Quartal um 4 % erhöhen. | Danke für Ihre Nachricht. Zuerst etwas anderes: Die Rohstoffpreise sind gestiegen. Ab dem nächsten Quartal sind wir deshalb gezwungen, unsere Preise um 4 % anzuheben. | |
| 8 | demand_repeat[2] | Die Preiserhöhung um 4 % ist für uns Voraussetzung für jedes Gespräch. | Wir bleiben dabei: Zuerst müssen die 4 % Preiserhöhung akzeptiert sein, dann reden wir weiter. | |
| 9 | demand_repeat[4] | Die Preiserhöhung um 4 % ist für uns Voraussetzung für jedes Gespräch. | Solange die um 4 % höheren Preise nicht vereinbart sind, ergibt ein Gespräch über Konditionen für uns keinen Sinn. | |
| 10 | demand_repeat[5] | Die Preiserhöhung um 4 % ist für uns Voraussetzung für jedes Gespräch. | Ich wiederhole: Eine Preiserhöhung um 4 % ist die Grundlage für jede weitere Diskussion. | |
| 11 | final_reject[1] | Wir möchten es bei den bestehenden Konditionen belassen. Vielen Dank für Ihr Verständnis. | Wir bleiben bei den heutigen Konditionen und beenden die Gespräche hier. Danke für Ihr Verständnis. | |
| 12 | final_reject[3] | Wir möchten es bei den bestehenden Konditionen belassen. Vielen Dank für Ihr Verständnis. | Wir lassen die Konditionen, wie sie sind, und schliessen das Thema damit ab. Besten Dank. | |
| 13 | final_reject[5] | Wir möchten es bei den bestehenden Konditionen belassen. Vielen Dank für Ihr Verständnis. | Es bleibt bei den bestehenden Vereinbarungen. Wir sehen keinen Sinn in weiteren Runden und danken Ihnen. | |
| 14 | last_offer[1] | Das ist unser letztes Angebot. | Ein besseres Angebot können wir nicht machen. | |
| 15 | last_offer[2] | Das ist unser letztes Angebot. | Weiter entgegenkommen können wir nicht. | |
| 16 | last_offer[3] | Das ist unser letztes Angebot. | Das ist unser abschliessendes Angebot. | |
| 17 | last_word[2] | Das ist unser letztes Wort zu diesem Thema. | Mehr ist dazu von unserer Seite nicht drin. | |
| 18 | no_offer[4] | Dazu haben wir kein Angebot gemacht; bitte senden Sie uns einen konkreten Vorschlag. | Was Sie annehmen, haben wir nie angeboten. Wir warten auf Ihren konkreten Vorschlag. | |
| 19 | no_offer[5] | Dazu haben wir kein Angebot gemacht; bitte senden Sie uns einen konkreten Vorschlag. | Dazu liegt von uns kein Angebot vor. Senden Sie uns bitte einen Vorschlag mit konkreten Werten. | |
| 20 | reject_no_room[4] | Danke für Ihre Nachricht. Ohne Gegenleistung sehen wir bei Zahlungsziel und Rabatt keinen Spielraum. | Danke für Ihre Nachricht. Für ein Entgegenkommen bei Zahlungsziel oder Rabatt bräuchten wir eine Gegenleistung von Ihnen. | |

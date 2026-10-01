# MomentumRadar · 1. Oktober 2026

Nutzerauftrag: dieselbe Long-/Short-Prozentdarstellung wie EventPilot und Trendfolge.

Die Oberfläche zeigt den vorhandenen Score (0–100) als Prozentsatz der Signalpunkte, keine Gewinnwahrscheinlichkeit. Bestehende Empfehlungen, Reihenfolge, Scan-Zeiten, Risikogrenzen und Daten bleiben unverändert. Die Gegenrichtung wird nur bei eigener Kandidatenauswertung angezeigt, nie als 100 minus Score. Fehlende/ungültige/veraltete Angaben sowie gescheiterte Abrufe ergeben —. Ein gültiger hoher Score kann bei negativem Kurzcheck weiterhin Kein Einstieg bedeuten.

Zwei kompakte Übersichtskarten zeigen den stärksten aktuell auswertbaren Kandidaten je Richtung. Kandidaten zeigen Richtungsprozente neben Empfehlung/Begründung. Ein direkter Link führt zum StrategieKompass.

Prüfung: 26 Node-Tests bestanden, JavaScript-Syntax geprüft. Mobile Playwright-Prüfung um Score, fehlende Gegenrichtung und Ausblendung nach Abruffehler ergänzt. Lokaler Browserlauf nicht möglich, Python-Playwright fehlt. Bestehender Pages-Workflow führt nach Veröffentlichung seinen Live-Mobiltest aus; dessen Ergebnis separat prüfen. Keine neuen Anbieter-/Nutzerdatenzugriffe, keine echte Handelsausführung bestätigt.

Im alten Checkout lagen fremde uncommittete Workflowänderungen. Diese wurden nicht angefasst; neuer sauberer Checkout der aktuellen Hauptversion verwendet.

Veröffentlichung bestätigt: Commit 2b77fbabc68452d0c3c4633c041b9bfa07fcfd64, Pages-Lauf 36928664650 am 01.10.2026 erfolgreich. Sowohl Prüfung des veröffentlichten Datenpakets als auch „Test live mobile interface“ erfolgreich; 390-px-Browserablauf einschließlich Suche, Aktualisieren/Fehlerfall und Speichern/Wiederöffnen. Der zusätzliche synthetische Prozentwert-Fall wurde lokal mangels Playwright nicht ausgeführt; Score-Logik durch Node-Tests geprüft. Keine Bestätigung einer Handelsrentabilität.

## Klick auf Long/Short – Top 5
Beide Richtungskarten öffnen jetzt direkt die jeweilige Rangliste; Short klappt automatisch auf. Suchfilter wird beim Sprung gelöscht. Rücksprung zur Richtungskarte und Kompass-Link bleiben erreichbar. Bis fünf Werte, gültige Signalstärken zuerst absteigend, nicht bestätigte Werte hinten mit bestehenden Sperren; bei insgesamt veralteten Daten ausdrücklich letzte Scan-Reihenfolge. Angezeigte Rangnummern entsprechen der sichtbaren Sortierung.

27 Node-Tests bestanden, inklusive Sortierung, Gleichstand, fünf Kandidaten, Datenlücken, alter Scan und leere Listen. Der mobile Workflowtest wurde um Klick beider Karten, Suchfilter-Rücksetzung, Short-Aufklappen, Fokus, Rangfolge, Fünferlimit, Rücksprung und Überlauf erweitert. Lokales Python-Playwright fehlt; tatsächliches Ergebnis des Live-Workflows nach Publikation gesondert prüfen.

## Präzisierung: vollständige Karten erst nach Richtungswahl, gemeinsame Geo-Skala
Nutzer bestätigt dieselbe Geo-Empfehlungsskala, ausdrücklich ohne Vereinheitlichung der Strategie-Berechnung. Long/Short öffnen nur die jeweilige Top-5-Detailansicht; vorher und nach Rücksprung sind beide Wertelisten samt Suche verborgen. Keine separate dauerhaft sichtbare Long-/Short-Liste. Wechsel der Auswahl schließt die Listen.

Skala: <30 Finger weg, <50 Neutral, <70 Beobachten, <85 Einstieg ½, sonst Einstieg voll. Bestehendes BEOBACHTEN wird niemals zu Einstieg hochgestuft; KEIN EINSTIEG bzw. fehlender bestätigter Score wird Gesperrt. Gesamtanzeige und Zähler verwenden dieselben effektiven Empfehlungen. ½/voll beziehen sich auf die risikogeprüfte Positionsgröße, keine Änderung am Depotlimit und keine automatische Ausführung.

28 Node-Tests inkl. aller Skalengrenzen und Strategie-/Frischesperren bestanden; JS-Syntax und Python-Testsyntax geprüft. Mobile Browserprüfung ergänzt um initial verborgene Listen, nur gewählte Richtung, Rückkehr mit geschlossenen Listen, Suche, Rangfolge und fixierte Kopfzeile. Frühere Top-5-Versionen: Workflows 36930377009 und 36930541338 erfolgreich inklusive Live-Mobiltest. Diese neue Präzisierung benötigt ihren eigenen Publikations-/Testnachweis.

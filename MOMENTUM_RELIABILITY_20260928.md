# MomentumRadar – Prüfung des bestehenden Setups

## Ausgangspunkt
Auftrag: bestehende App verlässlich nutzbar machen; keine neue Plattform, keine neuen Kosten, keine Orders. Ausgangsstand main: `8fffb499591d50d144c27984183dca67c22231ce`. Lokaler Prüfstand aus genau diesem Commit; keine fremden Änderungen überschrieben. RSL bleibt eigenständig.

## Konkrete Korrekturen
- Vollscan verwendet abgeschlossene 15-Minuten-Kerzen; Kurzcheck abgeschlossene 5-Minuten-Kerzen.
- Keine Stundenrendite über fehlende Kerzen oder Wochenenden hinweg. Fehlende Volumen- und Vergleichsdaten werden nicht als bestandene Prüfung ausgegeben.
- US-Vortagesschluss schließt die erste Nachbörsenkerze aus. DAX und Krypto erhalten ihre eigenen Sitzungsgrenzen.
- Jede Kandidatenbewertung enthält Zeit und Qualität ihrer eigenen Quelldaten. Ein neuer Kurzcheck kann eine ungültige Vollscan-Bewertung nicht aufwerten.
- Browser prüft die vollständige Snapshot-Struktur vor Übernahme, erhält die letzte lesbare Ansicht bei Fehlern und sperrt dabei Einstiege.
- Separate Anzeige empfangener und qualitativ auswertbarer Werte; verständliche Zeitangaben in österreichischer Zeit.
- Speichern wiederholt nur einen echten Paralleländerungskonflikt; fremde Änderungen werden per Rebase erhalten. Keine Force-Pushes.
- Automatische Läufe enden am bestätigten Scanfenster 22:00 Europe/Vienna, nicht erst um 22:59.

## Prüfungen
Die finale Test- und Live-Abnahme wird nach den tatsächlichen Läufen ergänzt. Synthetische Testdaten werden ausschließlich im Test verwendet und niemals als Kursdaten veröffentlicht.

Lokaler Integrationstest des Speicherns: getrenntes temporäres Git-Repository, konkurrierender unabhängiger RSL-Commit, Snapshot-Speicherung und anschließender Lauf ohne Änderungen erfolgreich. Beide Änderungen erhalten.

## Weiterhin offene automatische Auslösung
Erneute Prüfung am 28.09.2026: nur 11 native `schedule`-Läufe in der gesamten verfügbaren Historie. Neuester Lauf 13:52:30 UTC abgebrochen; letzter erfolgreicher 05:22:24 UTC. Die spätere einmalige Reaktivierung hat bis zur Prüfung keinen neuen zeitgesteuerten Lauf erzeugt. Workflow-Dateien aktiv, Hauptbranch korrekt, Repository aktiv, keine wartenden Schedule-Läufe. Die konkrete Ursache fehlender GitHub-Ereignisse ist weiterhin nicht zugänglich.

Push oder manueller Start beweisen nur die Datenkette, nicht den automatischen 15-Minuten-Betrieb. Zusätzliche Crondateien, beliebige Minutenwechsel und dauernde Neustartketten werden nicht als Zuverlässigkeitslösung ausgegeben. Der vorhandene manuelle Datenlauf bleibt ein ausdrücklich manueller Ersatz. Der vorbereitete Supportfall in MOMENTUM_NATIVE_STATUS.md wurde nicht versendet.

## Aussagegrenzen
Die 1 % sind ein Suchziel, keine bestätigte Strategieperformance. Der bestehende Rechner benennt seine Basis ausdrücklich: 1 % Depotziel bedeutet bei 50 % Einsatz eine Bewegung von 2 % auf diesen Einsatz, vor Kosten und Steuern. Der Einsatz ist entsprechend Projektvorgabe auf höchstens 50 % begrenzt. Technische Tests liefern keinen Renditenachweis. Keine Risikolimits, Einsatzgrenzen oder Bewertungsgewichte geändert. Brokerkurs, Spread, Gebühren und Risiko sind vor einer Order maßgeblich.

Yahoo/yfinance kann Daten verzögert oder unvollständig liefern. yfinance verweist auf persönliche Nutzung und auf Yahoo-Nutzungsrechte. Keine Freigabe zur kommerziellen Datenweiterverbreitung oder pauschale Rechtsfreigabe erteilt.

## Primärquellen, geprüft 28.09.2026
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule (Verzögerungen und ausfallende Ereignisse möglich)
- https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#actions (keine dauernde Serverersatzschleife)
- https://github.com/ranaroussi/yfinance (Datenrechte und persönliche Nutzung)
- https://help.yahoo.com/kb/SLN2310.html (börsenabhängige Datenverzögerung)


## Belegter Abschlussstand, 28.09.2026, 21:30 Wien
- Implementierung: `44bf05323a4c139b8d4f7edea63d017d2ac99970`, nach unverändertem Hauptbranch ohne Force-Push übernommen.
- 32 Python- und 24 JavaScript-Regressionstests bestanden. GitHub-QA: Lauf 36471722585, Job 109095364726. Mobiler synthetischer Browsertest einschließlich 50-%-Grenze, ungültig gespeichertem Altwert, Aktualisieren, Fehlern, Rückkehr zu gültigen Daten, Suche und Wiederöffnen bestanden.
- Reale Providerintegration zweimal bestanden: Läufe 36470759359 und36471241042. Der zweite Gesamtlauf scheiterte ausschließlich an der Reihenfolge im Browsertest (geschlossener Bereich vor sichtbarer Textprüfung); dies wurde korrigiert und separat erfolgreich geprüft. Keine fehlgeschlagene Prüfung als Erfolg ausgegeben.
- Produktiver Datenlauf36471876261 erfolgreich; Datencommit `ae8146d2a836075a564d0a62de1591cb7c86e2d4`.
- Vollscan: `2026-09-28T19:25:26.481596+00:00`; Kurzcheck: `2026-09-28T19:25:29.384964+00:00`. 1051/1051 Werte empfangen, 992 mit bestandenen Kern-Datenprüfungen, 62 Kurzchecks mit Kursen, keine gemeldeten Pipelinefehler.
- Live-Veröffentlichung 36472150859 erfolgreich; exakte Snapshot-ID `36471876261-2026-09-28T19:25:29.547653+00:00` auf Pages geprüft. Mobiler Live-Browsertest erneut erfolgreich, keine JavaScript-Fehler.
- Cloud-Browser um 21:29 Wien: neuer Vollscan/Kurzcheck 21:25 sichtbar, Aktualisieren abgeschlossen, Suche VTRS geprüft und zurückgesetzt. S&P 500 zeigte 500/500 geprüfte Werte. Angezeigte Signale sind technische Bewertungen, keine ausgeführten Trades.
- Kennungen: Der bestehende WKN-Abruf liefert nicht für jeden neu gewählten Kandidaten eine Kennung. Fehlende Kennungen werden nicht erfunden. Quellencharts bleiben erreichbar.

## Noch nicht erreicht
Zuverlässiger unbeaufsichtigter Dauerbetrieb ist NICHT abgenommen. Letzte erneute API-Prüfung: weiterhin nur 11 schedule-Läufe, jüngster 28.09.2026 13:52:30 UTC abgebrochen; kein neuer nativer Zeitplanstart während dieser Reparatur. Die frischen Daten kamen durch den ausdrücklich beauftragten Reparatur-Push. Keine zusätzliche Plattform, keine bezahlte Ressource, kein dauernder Neustartmechanismus und keine Order eingerichtet.

Der nächste erforderliche Nachweis ist ein eigenständiger zeitgesteuerter Datenlauf mit anschließend passender frischer Pages-Datei. Dafür muss die native GitHub-Auslösung wieder funktionieren; ein unabhängiger Zeitgeber wäre eine gesonderte Setup-Entscheidung. Der vorhandene manuelle Workflow ist im Fehlerfall verlinkt, ausdrücklich kein automatischer Ersatz. Die GitHub-Diagnose liegt vor; keine Supportnachricht wurde ohne Freigabe versendet.

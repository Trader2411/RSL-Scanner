# MomentumRadar – Reparaturprotokoll, 28.09.2026

## Ausgangsstand
main: 7bcba8ef6bea60b5d7ba85e882064ee258bb37d8. Keine offenen PRs laut letztem Connector-Read.

## Belegte Fehler
- Kurzcheck speicherte watch.json, veröffentlichte aber keine neue Pages-Version. Bot-Pushes starten den bisherigen Push-Deployment-Workflow nicht.
- Browser lud zwei getrennte Dateien und konnte widersprüchliche Generationen erhalten.
- `geprüft` wurde beim Rendern statt nach einem erfolgreichen Abruf gesetzt.
- Fehlender Kurzcheck konnte zum alten grünen Vollscan-Signal zurückfallen.
- Laufende Aufträge wurden durch weitere Änderungen abgebrochen.
- Anzeige belegte Tagesbewegung irreführend als Depotfortschritt.

## Eng begrenzte Reparatur
Ein kohärentes snapshot.json mit getrennten Zeitstempeln; explizites Deployment nach abgeschlossener Berechnung; keine gegenseitigen Abbrüche; Kurzcheck erneuert einen überfälligen Vollscan selbst. Bestehende Cronzeiten, Scoringformeln und bestätigte Umkehrschwellen bleiben erhalten. RSL-Berechnung und Historien werden nicht gelöscht. Handelszeiten für US-Aktien und .DE getrennt. Alte/unvollständige Daten und Abruffehler sperren neue Einstiege. Kurse beruhen nur auf vollständigen 5-Minuten-Kerzen; deren Schlusszeit wird ausdrücklich gespeichert. Yahoo kann dennoch verzögert sein.

## Tests und Abnahme
- 11 lokale Python-Regressionstests und 12 JavaScript-Regressionstests erfolgreich vor Veröffentlichung.
- Lokaler HTTP-Browsertest durch Umgebung blockiert (ERR_BLOCKED_BY_ADMINISTRATOR), daher Browserprüfung auf separatem GitHub-Testbranch vor Übernahme.
- Live-Abnahme verlangt genaue Snapshot-ID auf Pages und erfolgreichen mobilen Browsertest; ein Quellcode-Commit ist kein Live-Nachweis.
- Zeitplan-Abnahme verlangt echte schedule-Ausführungen; Push- und workflow_run-Erfolge beweisen keinen pünktlichen 15-Minuten-Takt.
- GitHub-Cron bietet keine Pünktlichkeitsgarantie. Falls Starts weiter ausbleiben, ist ein unabhängiger, autorisierter Zeitgeber erforderlich; keine neue kostenpflichtige Infrastruktur eingerichtet.
- Kein Nachweis profitabler Handelssignale. Brokerkurs, Spread und Risiko bleiben vor einer Order zu prüfen.
- Historische Ergebnisfelder aus dem alten Logger sind vor statistischen Aussagen zu revalidieren (Zeitfenster, Handelsschluss, Shortformel, Doppelzählungen). Keine erfundenen Trefferquoten.

## Live-Nachweis nach Umsetzung
- Reparatur-Commit 571abdc05458d34b4aa08a97c9c63318708a557b; PR #3 nach bestandener Prüfung in main übernommen; Merge 91566ac32a934fd0658e4ccc44d83f73f9ab625f.
- Reparaturbranch-QA: Lauf 36452578307, alle 23 Regressionstests und explizit synthetischer mobiler Browsertest erfolgreich. Artefakt momentum-repair-qa.
- Echter Datenlauf 36452865940 erfolgreich. Weiterer automatisch durch den abgeschlossenen RSL-Lauf ausgelöster Kandidatencheck ebenfalls erfolgreich; dies ist workflow_run, NICHT schedule.
- Öffentlich ausgelieferte Snapshot-ID: 36453052168-2026-09-28T16:43:53.118284+00:00. Vollscan 16:41 UTC / 18:41 Wien, Kurzcheck 16:43 UTC / 18:43 Wien; 1052/1052 Werte im Vollscan und 60 Kandidatenprüfungen. Diese Zeitangaben belegen die damalige Beobachtung, nicht spätere Aktualität.
- Pages-Lauf 36453155015 hat den exakten veröffentlichten Snapshot nachgewiesen.
- Pages-Lauf 36453449208 erfolgreich inklusive Live-Browsertest auf https://trader2411.github.io/RSL-Scanner/momentum-radar/ (390x844, Laden, Suchfunktion, Aktualisieren-Fehlerfall, Speichern/Wiederöffnen, kein horizontaler Überlauf, keine JavaScript-Fehler). Artefakt momentum-live-mobile-qa, ID10984805519.
- Kleine Startansicht, tatsächlicher Abrufzeitpunkt statt bloßer Render-Zeit, automatische Seitenaktualisierung bei sichtbarer Seite. Keine fingierte Depotperformance mehr.

## Verbleibende externe Blockade – NICHT als fertiger Dauerbetrieb freigeben
- Direkte Laufzeitdiagnose 36454418274 bestätigt: alle relevanten Workflows stehen auf active. Eine bloß deaktivierte Aufgabe ist daher nicht die Erklärung.
- Die Diagnosedatei vom 28.09.2026 16:54 UTC zeigt weiterhin den letzten schedule-Lauf um13:52 UTC (abgebrochen) und davor05:22 UTC (erfolgreich). Kein erfolgreicher zeitplanbasierter Kandidatencheck nach der Reparatur nachgewiesen.
- Erneute API-Abfrage nach schedule-Läufen ab16:41 UTC ergab0. Die genaue Ursache innerhalb von GitHub ist nicht belegt; kein weiterer kosmetischer Cron-Minutenwechsel.
- Datenberechnung, Validierung und Veröffentlichung funktionieren, sobald sie gestartet werden. Für verlässliche automatische Versorgung ist die zeitliche Auslösung weiterhin nicht abgenommen.
- Vorgesehene kleinste Ergänzung: externer Zeitgeber startet den bestehenden Kandidatenworkflow per authentifiziertem workflow_dispatch. Keine neue App und kein Wechsel der Kursquelle nötig.
- Render ist als Integration verfügbar, aber noch NICHT verbunden. Cron-Dienst laut Hersteller mindestens1 US-Dollar pro Monat, weitere Abrechnung nach Nutzung. Keine kostenpflichtige Ressource erstellt. Vor Einrichtung benötigt: ausdrückliche Kostenfreigabe, verbundener Render-Zugang sowie dort sicher hinterlegte, auf dieses Repository begrenzte GitHub-Authentifizierung für den Start des Workflows. Keine Zugangsschlüssel im Chat oder Repository speichern.
- Ein erfolgreicher einzelner Datenlauf oder eine grüne technische Ampel ist kein Nachweis risikoloser oder profitabler Handelbarkeit.
- Mittwoch-Wochenbericht unverändert terminiert; Auswertung berücksichtigt neue Einzeldateien und darf Legacy-Nachlaufwerte nicht ungeprüft als Treffer-/Renditezahlen verwenden.

## Quellen
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow
https://docs.github.com/en/actions/how-tos/troubleshoot-workflows
https://render.com/docs/cronjobs

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

## Quellen
https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow

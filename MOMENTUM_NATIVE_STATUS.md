# MomentumRadar – ausschließlich bestehendes GitHub-Setup

Stand: 28.09.2026, 18:38 UTC / 20:38 Europe/Vienna.

## Verbindliche Vorgabe
Der Nutzer lehnt Render und zusätzliche Dienste ab. Keine neue kostenpflichtige Infrastruktur, keine neue Plattform und keine neue Handelsstrategie einführen. Die frühere Aussage, Render sei zwingend erforderlich, ist kein belegter technischer Befund. Bewertungsregeln und Frischeprüfungen nicht lockern, um funktionierende Versorgung vorzutäuschen.

## Neuer, begrenzter Reparaturschritt
Der bereits aktive Workflow `update-momentum-watch.yml` wurde einmal über die dokumentierte GitHub-API deaktiviert und unmittelbar wieder aktiviert. Kein manuell gestarteter Markt-Datenlauf, keine Änderung der Cronzeiten, keine Änderung am RSL-Scanner und keine dauernde Neustartkette.

Nachweis: Commit `60161d167572f57c1a94b08957b4afaf9a79294a`, Reparaturlauf `36463958577`, Job `109069204992`; Prüfen, Deaktivieren, Reaktivieren und Speichern des Nachweises erfolgreich. Artefakt `momentum-schedule-reactivation`, ID `10988680776`. Vorher `state=active`; nachher `state=active`, `updated_at=2026-09-28T18:15:57Z`; Abschluss 18:16 UTC.

Die Hilfsdatei `.github/workflows/momentum-schedule-repair.yml` hat KEINEN Zeitplan. Sie verändert keine Marktdaten und startet sich nicht selbst. Sie reaktiviert niemals einen bereits zuvor deaktivierten Workflow.

## Beobachtung nach Neuaktivierung
- Vorhandener Cron: `7,22,37,52 8-21 * * 1-5` (UTC).
- Erste planmäßige Termine nach der Neuaktivierung: 18:22 und 18:37 UTC / 20:22 und 20:37 Wien.
- API-Abfragen um 18:24, 18:28, 18:33 und 18:38 UTC nach `event=schedule`, erstellt seit 18:15:58 UTC, ergaben jeweils `total_count=0`, `workflow_runs=[]`.
- Die letzte Kontrolle erfolgte nur etwa eine Minute nach dem zweiten Termin. Sie beweist nicht, dass nie mehr ein Lauf starten wird. Sie belegt aber KEINE wiederhergestellte automatische Versorgung.
- Kein neuer Datenstand und kein verlässlicher Dauerbetrieb darf aus der erfolgreichen Konfigurationsänderung abgeleitet werden. Keine manuelle Datenauffrischung als automatischen Erfolg ausgeben.

Nächste Abnahme: neue echte schedule-Läufe → Datenberechnung → erfolgreiche Pages-Veröffentlichung → passender, frischer Snapshot. Die bereits dokumentierten Tests im Reparaturprotokoll bleiben historische Belege, keine Zusicherung aktueller Kurse.

## Verbleibender Blocker
Die zeitgesteuerte Auslösung in GitHub ist weiterhin nicht nachgewiesen. Innerhalb des freigegebenen Setups wurde die Workflow-Aktivierung erfolgreich erneuert; die genaue Ursache ausbleibender Ereignisse ist weiterhin unbekannt. Weder der native GitHub-Cron noch ein alternativ vorgeschlagener Dienst darf ohne erfolgreiche Folgeprüfung als zuverlässig bezeichnet werden. Kein zusätzlicher Dienst eingerichtet.

## Vorbereitete Diagnose für GitHub – nicht abgesendet
Betreff: Aktiver Zeitplan auf main erzeugt keine neuen schedule-Läufe.

Repository: Trader2411/RSL-Scanner, öffentlich, ID 1222400682. Default-Branch: main. Workflow: .github/workflows/update-momentum-watch.yml, ID 369201340, Name Update MomentumRadar candidate watch. Cron wie oben. Der Workflow ist vorhanden und aktiv. Erfolgreiche Push-/workflow_run-Datenläufe sind im Reparaturprotokoll dokumentiert, insbesondere 36452865940 und 36453062457. Die erneute Aktivierung um 18:15:57 UTC ist durch Lauf 36463958577 und sein Artefakt belegt. Dennoch ergab die Abfrage /repos/Trader2411/RSL-Scanner/actions/runs?event=schedule&created=>=2026-09-28T18:15:58Z bei der letzten Prüfung um 18:38 UTC keine neuen Läufe. Bitte die Registrierung und Erzeugung der Schedule-Ereignisse für dieses Repository prüfen. Es wird kein dauerhaftes oder GitHub-weites Ausfallereignis unterstellt; gesucht ist die konkrete Ursache im betroffenen Repository.

## Quellen und Grenzen
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://github.com/Trader2411/RSL-Scanner/actions/runs/36463958577

GitHub dokumentiert mögliche Verzögerungen und ausfallende Schedule-Ereignisse. Weitere Änderungen nur bei neuer Erkenntnis; kein weiterer kosmetischer Minutenwechsel und keine unbelegte Fertigmeldung.

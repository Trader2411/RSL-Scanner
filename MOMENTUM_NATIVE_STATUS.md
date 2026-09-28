# MomentumRadar – ausschließlich bestehendes GitHub-Setup

Stand: 28.09.2026, 18:24 UTC / 20:24 Europe/Vienna.

## Verbindliche Vorgabe
Der Nutzer lehnt Render und zusätzliche Dienste ab. Keine neue kostenpflichtige Infrastruktur, keine neue Plattform und keine neue Handelsstrategie einführen. Die frühere Aussage, Render sei zwingend erforderlich, ist kein belegter technischer Befund. Bewertungsregeln und Frischeprüfungen nicht lockern, um funktionierende Versorgung vorzutäuschen.

## Neuer, begrenzter Reparaturschritt
Der bereits aktive Workflow `update-momentum-watch.yml` wurde einmal über die dokumentierte GitHub-API deaktiviert und unmittelbar wieder aktiviert. Kein manuell gestarteter Markt-Datenlauf, keine Änderung der Cronzeiten, keine Änderung am RSL-Scanner und keine dauernde Neustartkette.

Nachweis: Commit `60161d167572f57c1a94b08957b4afaf9a79294a`, Reparaturlauf `36463958577`, Job `109069204992`; Prüfen, Deaktivieren, Reaktivieren und Speichern des Nachweises erfolgreich. Artefakt `momentum-schedule-reactivation`, ID `10988680776`. Vorher `state=active`; nachher `state=active`, `updated_at=2026-09-28T18:15:57Z`; Abschluss 18:16 UTC.

Die Hilfsdatei `.github/workflows/momentum-schedule-repair.yml` hat KEINEN Zeitplan. Sie verändert keine Marktdaten und startet sich nicht selbst. Sie reaktiviert niemals einen bereits zuvor deaktivierten Workflow.

## Noch NICHT bestätigt
Der erste planmäßige Kurzcheck nach diesem Schritt wäre am 28.09. um 18:22 UTC / 20:22 Wien fällig. Die Abfrage nach `event=schedule`, erstellt seit 18:15:58 UTC, ergab bei Prüfung um 18:24 UTC weiterhin 0 Läufe. Eine Verzögerung von zwei Minuten allein ist kein endgültiger Fehlschlagsnachweis. Kein zuverlässiger Dauerbetrieb oder neuer Datenstand darf aus der erfolgreichen Konfigurationsänderung abgeleitet werden.

Nächste Abnahme: neue echte schedule-Läufe → Datenberechnung → erfolgreiche Pages-Veröffentlichung → passender, frischer Snapshot. Die bereits dokumentierten Tests im Reparaturprotokoll bleiben historische Belege, keine Zusicherung aktueller Kurse.

## Quellen und Grenzen
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
- https://github.com/Trader2411/RSL-Scanner/actions/runs/36463958577

GitHub dokumentiert mögliche Verzögerungen und ausfallende Schedule-Ereignisse. Die genaue Ursache der in diesem Repository fehlenden Starts ist weiterhin nicht belegt. Weitere Änderungen nur bei neuer Erkenntnis; kein weiterer kosmetischer Minutenwechsel und keine unbelegte Fertigmeldung.

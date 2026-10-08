# RSL-Schreibkonflikt: Prüfung am 8. Oktober 2026

## Umgesetzt
Commit 9270de4ee24cd220b4f93b475d65c91aaf3238ef ändert nur zwei Workflows: update-rsl-data.yml und rsl-hourly-watchdog.yml. Beide verwenden nun concurrency.group=rsl-data-update mit cancel-in-progress=false. Checkout, Berechnung und Speicherung laufen dadurch nacheinander. Beide Speicherblöcke wiederholen fetch/rebase/push höchstens dreimal, um Änderungen anderer Dateien durch MomentumRadar zwischen fetch und push abzufangen. Echte Konflikte brechen weiterhin sichtbar ab; kein Force-Push. Handelsstrategien, Sicherheitsregeln, Datenanbieter und Zeitpläne unverändert.

## Getestet
YAML-Struktur und gemeinsame Sperre geprüft, beide Shell-Blöcke mit bash -n geprüft, git diff --check erfolgreich. Zehn echte lokale Git-Integrationstests: je Workflow fremde Remote-Dateiänderung, Remote-Änderung zwischen fetch/push, echter Konflikt derselben Datei, keine Datenänderung und drei erfolglose Push-Versuche. Alle erfolgreich; fremde Änderungen bleiben erhalten, echte Konflikte werden nicht verschluckt. Vier bestehende Tests in tests/test_crypto_history.py erfolgreich.

## Live bestätigt
- Update RSL data: https://github.com/Trader2411/RSL-Scanner/actions/runs/37749936564 — erfolgreich einschließlich Berechnung und Speicherung; Datencommit 3301c3c.
- RSL hourly watchdog: https://github.com/Trader2411/RSL-Scanner/actions/runs/37749936666 — wartete zunächst auf denselben Lock, anschließend erfolgreich einschließlich Berechnung und Push; Datencommit cf7ff0e, Push am 08:30:31 UTC (10:30:31 Wien).
- Reale Gleichzeitigkeit der beiden Writer wurde verhindert. Langfristige Zuverlässigkeit über weitere geplante Läufe noch nicht bewiesen.

## Veröffentlichung blockiert
Ein älterer Pages-Lauf wartet seit 6. Oktober an der Umgebung github-pages und hält die Workflow-Sperre: https://github.com/Trader2411/RSL-Scanner/actions/runs/37440940896 . Job 112194253979 status=waiting. pending_deployments zeigt die Umgebung, current_user_can_approve=false, reviewers=[], wait_timer=0. Der genaue Grund der Umgebungsprüfung ist mit dem verbundenen Zugang nicht erkennbar. Keine Freigabe- oder Schutzregel geändert.

Neuere Pages-Läufe bleiben pending, ältere wartende Nachfolger werden durch neuere ersetzt. Letztgeprüfter neuer Lauf: https://github.com/Trader2411/RSL-Scanner/actions/runs/37750336846 . Kein Nachweis einer erfolgreichen Veröffentlichung der Reparatur.

Direkter öffentlicher Abruf von https://trader2411.github.io/RSL-Scanner/data.json ergab generated_at=2026-10-06T07:38:46.675476+00:00 (6. Oktober 09:38 Wien). Der öffentliche Datenstand ist damit nachweislich älter als die neuen Repository-Daten. Das ist ein separater Veröffentlichungsblocker, nicht ein Fehler der neuen Berechnung.

## Kleinster nächster Schritt
Repository-Eigentümer muss beim wartenden Pages-Lauf die Umgebungsprüfung prüfen und, sofern zulässig, freigeben. Der verbundene Zugang bietet weder diese Freigabe noch das Abbrechen des blockierenden Laufs. Danach neuesten Pages-Lauf und öffentliche data.json mit dem tatsächlich veröffentlichten Repository-Snapshot vergleichen. Nicht als veröffentlicht oder vollständig live bestätigt ausgeben, bevor dieser Vergleich erfolgreich ist.

## Nachprüfung am 8. Oktober, ca. 12:57 Wien
Der Eigentümer hat den festhängenden Lauf 37440940896 abgebrochen; Screenshot bestätigt Cancelled. Die gezeigten Umgebungseinstellungen haben Required reviewers und Wait timer deaktiviert und erlauben main. Eine aktuell aktive manuelle Freigaberegel ist daher nicht belegt; der ursprüngliche Wartegrund bleibt ungeklärt. Keine Schutzregeln geändert.

Pages-Lauf https://github.com/Trader2411/RSL-Scanner/actions/runs/37750391080 ist erfolgreich abgeschlossen. Direkter Abruf und vollständiger JSON-Vergleich bestätigen: öffentliche data.json entspricht der aktuellen Repository-Datei. generated_at=2026-10-08T08:29:18.614011+00:00, also 8. Oktober 10:29:18 Wien. Dieser Zeitpunkt bezeichnet die Erzeugung der Datei, nicht die Aktualität jeder Kurskerze. Der zuvor dokumentierte Veröffentlichungsblocker ist aufgehoben. Berechnung, Speicherung und Veröffentlichung dieser Reparaturläufe sind jetzt live bestätigt. Dauerhafte Zuverlässigkeit über spätere automatische Läufe bleibt eine noch nicht abgeschlossene Beobachtung.

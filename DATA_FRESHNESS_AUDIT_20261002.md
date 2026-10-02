# Datenversorgung – 02.10.2026

Auftrag: alle Kompass-Scanner auf laufende Versorgung prüfen und belegte Lücken beheben.
Ausgang: main f10d40663225a3bdcd32b0973cc43eff23eb5233, sauber.

- Öffentlicher RSL-Export 06:40 UTC vorhanden. Momentum-Snapshot am 02.10. morgens weiterhin Vollscan 01.10.19:42 UTC/Kurzcheck 19:56 UTC. Ursache: momentum_delivery.scan_window verwirft alle schedule/workflow_run vor 10:00 Wien, nachts und am Wochenende, obwohl Krypto/Futures im Universum enthalten sind.
- Globale Zeitfenstersperre entfernt. Bestehende RSL-Workflow-Verknüpfung liefert weiterhin stündliche Auslöser rund um die Uhr; bestehender 15-Minuten-Zeitplan unverändert. Individuelle Marktzeiten, Kursalter, Datenlücken, fehlende Kurse und Einstiegsregeln bleiben unverändert. GitHub kann zeitgesteuerte Läufe verzögern; keine garantierte Echtzeit.
- RSL-Browser lädt nun beim Öffnen, alle fünf Minuten bei sichtbarer Nutzung und bei Rückkehr. Anfrage mit Zeitlimit, HTTP-/Formprüfung, Überlappungsschutz und Schutz gegen rückwärts laufende Exportzeit. Fehler und Quelldaten älter als zwei Stunden ausdrücklich markiert; neuer Browserabruf setzt den Kurszeitpunkt nicht neu.
- 13 Python-Regressionstests bestanden, darunter Morgen/Nacht/Wochenende sowie weiterhin Datenlücken/Signal-Upgrade-Sperren. JS-Syntaxprüfung bestanden. Neuer Workflow-/Publikationsnachweis folgt nach Push.
- Keine Orders, neuen Anbieter oder Abos. Tagesbasierte RSL-Ränge sind keine Echtzeit-Einstiegsbestätigung. Geo/Trendfolge/Gegenbewegung werden in ihren separaten Sites bearbeitet; EventPilot bereits mit automatischem 15-Minuten-Abruf.

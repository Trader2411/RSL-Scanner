# Rohstoff-/Krypto-Tachos · 2. Oktober 2026

Auftrag: Datenlücke und Aktualisierung reparieren, ohne die Kompass-Bewertung aufzuweichen. Am 02.10. fehlte der 01.10. in allen 55 exportierten Kryptoreihen. Yahoo lieferte im direkten Tagesabruf ebenfalls null; BTC-Stundenabruf enthielt alle 24 abgeschlossenen UTC-Stunden.

Krypto-Tageslücken der letzten sieben abgeschlossenen Tage werden gezielt aus derselben Yahoo-Quelle nachgefragt. Nur exakt 24 eindeutige UTC-Stunden mit positiven endlichen Schlusskursen, passendem Symbol, USD, Intervall 1h und mindestens 20 Minuten Abstand zum Tagesende werden akzeptiert. Der Schlusskurs der letzten Stunde ersetzt ausschließlich fehlende Tageswerte. Kein Überschreiben vorhandener Tageswerte, keine Interpolation, kein Vortagsfortschreiben. Protokolliert als chart_recovered_days und chart_recovery_source. Fehler lassen die Lücke offen. Maximal sechs parallele Anfragen, zwölf Sekunden Timeout.

RSL-Hauptlauf und Wiederholungsversuch jetzt stündlich an allen sieben Tagen, damit 24/7-Krypto auch am Wochenende zur Zweistunden-Frischeprüfung des Kompasses passt. Bestehenden Watchdog, Momentum-Workflows, Strategien und Risikoregeln nicht verändert. Keine neue Automatisierung angelegt.

Vier gezielte Python-Tests bestanden: vollständiger Schlusskurs, fehlende/duplizierte/null/falsche/future Daten blockiert, nur Lücken ergänzt, erfolgloser Nachabruf lässt Lücke bestehen. BTC-Liveabruf vom 01.10. mit 24 Stunden positiv geprüft (Schlusskurs 84848.7265625 USD). Veröffentlichung und vollständiger neuer Export anschließend prüfen.

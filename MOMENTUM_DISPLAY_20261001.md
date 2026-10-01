# MomentumRadar · 1. Oktober 2026

Nutzerauftrag: dieselbe Long-/Short-Prozentdarstellung wie EventPilot und Trendfolge.

Die Oberfläche zeigt den vorhandenen Score (0–100) als Prozentsatz der Signalpunkte, keine Gewinnwahrscheinlichkeit. Bestehende Empfehlungen, Reihenfolge, Scan-Zeiten, Risikogrenzen und Daten bleiben unverändert. Die Gegenrichtung wird nur bei eigener Kandidatenauswertung angezeigt, nie als 100 minus Score. Fehlende/ungültige/veraltete Angaben sowie gescheiterte Abrufe ergeben —. Ein gültiger hoher Score kann bei negativem Kurzcheck weiterhin Kein Einstieg bedeuten.

Zwei kompakte Übersichtskarten zeigen den stärksten aktuell auswertbaren Kandidaten je Richtung. Kandidaten zeigen Richtungsprozente neben Empfehlung/Begründung. Ein direkter Link führt zum StrategieKompass.

Prüfung: 26 Node-Tests bestanden, JavaScript-Syntax geprüft. Mobile Playwright-Prüfung um Score, fehlende Gegenrichtung und Ausblendung nach Abruffehler ergänzt. Lokaler Browserlauf nicht möglich, Python-Playwright fehlt. Bestehender Pages-Workflow führt nach Veröffentlichung seinen Live-Mobiltest aus; dessen Ergebnis separat prüfen. Keine neuen Anbieter-/Nutzerdatenzugriffe, keine echte Handelsausführung bestätigt.

Im alten Checkout lagen fremde uncommittete Workflowänderungen. Diese wurden nicht angefasst; neuer sauberer Checkout der aktuellen Hauptversion verwendet.

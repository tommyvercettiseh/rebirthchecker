# Changelog

## 0.5.0

### Android release fix

- De actuele `android/` module is de enige bron voor de APK-build.
- Package-id blijft vast op `nl.hes.rebirthchecker`.
- Android-versie verhoogd naar `versionCode 5` / `0.5.0`.
- Workflow voert eerst een smoke-build uit en bouwt daarna een ondertekende release-APK.
- Release signing komt uitsluitend uit GitHub Secrets zodat toekomstige APK's over dezelfde installatie heen kunnen worden bijgewerkt.
- APK-artifact heet voortaan `Rebirth-Checker-v0.5.0.apk`.

### Nog eenmalig nodig

- GitHub Actions signing-secrets instellen voor de vaste Rebirth release key.
- De huidige debug-geïnstalleerde versie kan één laatste uninstall nodig hebben. Vanaf de eerste vaste release-key kunnen volgende versies normaal als update worden geïnstalleerd.

## 0.1.0

### Toegevoegd

- Instelbare Resurgence-maprotatie
- Rebirth Island groen gemarkeerd wanneer actief
- Start, pauze, vorige en volgende map
- Maps toevoegen, verwijderen en herschikken
- Always-on-top en compacte modus
- System tray
- Mobiele ntfy-push bij start van Rebirth
- One-click Windows launcher
- Lokale en automatische EXE-build
- Automatische configuratieopslag en logging

### Tests

- Rotatieberekening
- Instellingen laden en opslaan
- GitHub Actions smoke test

### Handmatige controle

- ntfy-topic koppelen op telefoon
- Windows system tray en always-on-top controleren

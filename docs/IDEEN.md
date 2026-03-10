# Ideen / Feature Backlog

## Commands (aus README + Teamideen)
- `/help`: Befehlsübersicht
- `/msg [name, ..]`: private Nachricht(en)
- `/join [servername]`: Server beitreten
- `/leave`: aktuellen Server verlassen
- `/list`: Teilnehmer oder Serverliste
- `/new host [username / ip & port]`: Hostübergabe (Host-only)
- `/myColor [blue/yellow/etc./HEX]`: Username-Farbe setzen
- `/rename`: Name ändern (mit Cooldown-Regel)
- `/info [name/servername]`: Metadaten anzeigen
- `/testserver`: Testserver auf den niemand von außerhalb joinen kann
- `/send file [path/to/file]`: Datei senden
- `/save chat [filename]`: Chatverlauf speichern
- `/ping [name/server]`: Latenz messen
- `/version`: Version anzeigen
- `/uptime`: Serverlaufzeit anzeigen
- `/broadcast`: Nachricht an alle User im Netzwerk
- `/new servername`: Servername ändern (Host-only)
- `/new Passwort`: Serverpasswort ändern (Host-only)
- `/kick [name]`: Nutzer entfernen (Host-only)
- `/ban [name]`: Nutzer vom Server bannen (Host-only)
- `/whoami`: eigene Infos anzeigen
- `/game [gamename] [opponent]`: Minigame anfragen
- `/gameaccept [challenger]`: Minigame annehmen
- `/vote <text> [option1, option2, ...]`: eine Abstimmung starten.

## UI/UX Ideen
- Autocomplete für Namen/Befehle (`prompt_toolkit` optional)
- Bessere CLI-Feedbacks und Recovery-Hinweise
- Klarer Modus-Status: "nicht verbunden", "verbunden", "host"
- Farben für Usernames und auch andere farbe für private messages

## Netzwerk / Protokoll
- Join-Handshake bereits implementiert (ACK/NACK) -> weiter ausbauen:
  - klarere Join-NACK-Codes für Passwort/Lock/Ban
  - optionales Protokoll-Versioning pro TCP-Verbindung
- Keepalive/Heartbeat für schnellere Verbindungsfehler-Erkennung
- Reconnect-Strategie (optional)

## Sicherheit
- Serverpasswort-End-to-End einführen (nicht nur State-Feld)
- Optionale Verschlüsselung/TLS später
- Rate-Limits gegen Spam/Flood

## Persistenz
- Lokale User-Settings (Name, Farbe, etc.)
- Chat-Export als stabiles Format
- Settings-UI ausbauen (Theme/Color-Mode, Export-Pfad, Suggestions ein/aus)

## Moderation / Server-Features
- Ban-Liste verwalten (anzeigen, unban per Command)
- Lock-Status steuern und sichtbar machen
- Host-Migration robuster gestalten

## Minigames (Ideen)
- `tictactoe`
- `rockpaperscissors`
- `battleship`
- `hangman`
- `connectfour`
- `categories` (Stadt, Land, Fluss)
- `highestnumber`
- `headortails`

## nächste Schritte
1. Zentrales Command-System ausbauen
2. `/list`, `/whoami`, `/uptime`, `/version`

# localchat
just another stupid Lan Chat

Bitte in Editor Format anschauen:

localchat/
│
├─ localchat/
│   ├─ __init__.py
│   ├─ __main__.py                # CLI-Einstiegspunkt für `localchat start`
│   │
│   ├─ core/                      # Zentrale Logik, unabhängig von CLI
│   │   ├─ __init__.py
│   │   ├─ network.py             # TCP/UDP-Verbindungen, Socket-Wrapper
│   │   ├─ protocol.py            # Nachrichtenformate, Serialisierung, Pakettypen
│   │   ├─ storage.py             # lokale Dateien, Usernamen, Chatverlauf
│   │   ├─ security.py            # Passwortprüfung, Verschlüsselung (später)
│   │   └─ utils.py               # Hilfsfunktionen, Farben, Zeitstempel
│   │
│   ├─ client/
│   │   ├─ __init__.py
│   │   ├─ client.py              # Hauptklasse Client
│   │   ├─ commands.py            # /msg, /join, /leave usw.
│   │   ├─ discovery.py           # empfängt UDP-Broadcasts
│   │   ├─ handlers.py            # Verarbeitung eingehender Pakete
│   │   └─ interface.py           # Terminal-Ein/Ausgabe
│   │
│   ├─ server/
│   │   ├─ __init__.py
│   │   ├─ server.py              # Hauptklasse Server
│   │   ├─ broadcast.py           # UDP-Serveranzeige
│   │   ├─ session.py             # Verbundene Clients, Hostwechsel
│   │   └─ commands.py            # Serverbefehle (/kick, /ban, /info server)
│   │
│   ├─ config/
│   │   ├─ __init__.py
│   │   ├─ defaults.py            # Ports, Pfade, Zeitlimits
│   │   └─ colors.py              # ANSI-Farbcodes
│   │
│   └─ logging/
│       ├─ __init__.py
│       ├─ logger.py              # zentraler Logger
│       └─ formatter.py           # Logformat, Rotation
│
├─ tests/                         # Unit- und Integrationstests
│   ├─ test_client.py
│   ├─ test_server.py
│   └─ test_protocol.py
│
├─ installer_windows.py
│
├─ setup.py
│
├─ setup.cfg
│
├─ scripts/                       # Entwicklungs- oder Wartungsskripte
│   ├─ build_wheel.sh
│   └─ run_local.sh
│
├─ pyproject.toml                 # Projektmetadaten, CLI-Entry Point  
├─ README.md
└─ LICENSE



Ablaufidee beim Start
Nutzer tippt:
localchat start
__main__.py prüft lokale Konfigurationsdatei für Usernamen
Client sendet UDP-Broadcast, fragt verfügbare Server ab
Option eigenen Server starten (mit passwort) 


Befehle:

- localchat start				     soll das program starten (möglich über .whl oder so)
- /help							     Liste und Erklärung der Befehle
- /msg [name, ..]				     privat Nachricht(en)
- /join [servername]			     server beitreten
- /leave						     verlässt den aktuellen server
- /list							     Teilnehmer oder (Server anzeigen wenn nicht in aktivem chat)
- /new host [username / ip & port]	 Hostübergabe (only Host)
- /myColor [blue/yellow/etc./HEX]    Username Farbe (evlt. wenn möglich)
- /rename							 Name ändern (alle 7 Tage)
- /info [name/servername]			 metadaten wie ip, Port und ehemalige Namen
- /test server						 Lokaler Testserver (nicht broadcasten)
- /send file [path/to/file]			 Datein senden
- /save chat [filename]				 speichert chatverlauf
- /ping [name/server]				 misst Latenz 
- /version							 zeigt Programmversion 
- /uptime							 zeigt Laufzeit des Servers 
- /broadcast 						 Nachricht an alle user im Netzwerk
- /new servername					 Neuen Servernamen (only Host)
- /new Passwort					     Neues Passwort für den server setzen (only Host)
- /kick [name]						 entfernt Nutzer (only Host)
- /whoami							 zeigt Name, Farbe, Ip, etc an



Namensfarben und auch Text autocomplet für z.B. [/msg Ma] und der schlägt schon vor [/msg Maximilian] mit Tap bestätigen
das geht über promt_toolkit
mit: pip install prompt_toolkit
könnte man ja user optional fragen, ob sie dieses feature haben wollen, weil sie wollen evlt nicht das wir einfach so
automatisch so etwas herrunterladen.



Phase 1 – Fundament (unabhängig von Chatlogik)
Ziel: stabile Basis, auf die du Client und Server setzen kannst.
core/network.py
Baue eine minimalistische TCP/UDP-Kommunikationsschicht.
Klassen: TCPConnection, UDPBroadcast.
Nur Funktionen für connect, send, receive, close.
Keine Chatlogik. Nur Datenfluss.
core/protocol.py
Lege ein einheitliches Datenformat fest (z. B. JSON).
Definiere Pakettypen:
"public", "private", "join", "leave", "info", "server_list".
Stelle Funktionen bereit: encode_packet(data: dict) -> bytes, decode_packet(bytes) -> dict.
core/utils.py
Zeitstempel, zufällige IDs, einfache Farbformate.
Nichts Netzspezifisches.

Phase 2 – Serverbasis
Ziel: lauffähiger Chat-Server ohne Befehle, nur öffentliche Nachrichten.
server/server.py
Startet TCP-Listener.
Akzeptiert Clients, verwaltet aktive Verbindungen.
Sendet eingehende Nachrichten an alle verbundenen Clients.
server/broadcast.py
Regelmäßige UDP-Broadcasts mit Servername + Port.
Antwortet auf Discovery-Anfragen von Clients.
server/session.py
Verwaltung der verbundenen Nutzer (Name, IP, Farbe).
Methoden: add_user(), remove_user(), get_user_by_name().

Phase 3 – Clientbasis
Ziel: Verbindung, Nachrichtenempfang, Terminal-Ein/Ausgabe.
client/client.py
Verbindet sich mit Server.
Sendet Eingaben.
Thread für Empfang → Ausgabe im Terminal.
client/interface.py
Kümmert sich nur um Text-I/O.
Trennt Anzeige-Logik von Netzwerk.
Später Basis für Farben, Formatierungen, Prompt.

Phase 4 – Kommandosystem
Ziel: erweiterbare Chatsteuerung.
client/commands.py
Map von Befehlsnamen zu Funktionen.
Zentrale execute_command(cmd_str)-Funktion.
Erst einfache Befehle: /msg, /list, /leave.
Später /info, /myColor, /new host.
server/commands.py
Nur Host-Kommandos: /kick, /ban, /lock.

Phase 5 – Persistenz und Feinschliff
Ziel: Komfort, Wiederverwendung, Stabilität.
core/storage.py
Speichert Username, Verlauf, Zeitlimits für Namensänderung.
core/security.py
Passwortprüfung, Hashing.
Später TLS/Encryption optional.
logging/logger.py
Standardisierte Logs für Fehler und Nachrichten.
Phase 6 – Integration
Ziel: Komplettes CLI-Tool.
__main__.py
Liest CLI-Argumente (localchat start, localchat test server).
Ruft Client oder Server je nach Modus auf.
Verwendet argparse.
pyproject.toml
Definiere [project.scripts] localchat = "localchat.__main__:main".
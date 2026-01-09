# localchat
just another stupid Lan Chat

Ablaufidee beim Start
Nutzer tippt:
localchat start
__main__.py prüft lokale Konfigurationsdatei für Usernamen
Client sendet UDP-Broadcast, fragt verfügbare Server ab
Option eigenen Server starten (mit passwort) 


Befehle:

- localchat start				     soll das program starten (möglich über .whl oder so)   ✅
- /help							     Liste und Erklärung der Befehle (auch: --help/ -h )
- /msg [name, ..]				     privat Nachricht(en)
- /join [servername]			     server beitreten
- /leave						     verlässt den aktuellen server
- /list							     Teilnehmer oder (Server anzeigen wenn nicht in aktivem chat)
- /newhost [username / ip & port]	 Hostübergabe (only Host)
- /myColor [blue/yellow/etc./HEX]    Username Farbe (evlt. wenn möglich)
- /rename							 Name ändern (alle 7 Tage)
- /info [name/servername]			 metadaten wie ip, Port und ehemalige Namen
- /test server						 Lokaler Testserver (nicht broadcasten)
- /send file [path/to/file]			 Datein senden (automatic path with drag and drop)
- /save chat [filename]				 speichert chatverlauf
- /ping [name/server]				 misst Latenz (ohne weitere Angaben, wird der server host gepingt)
- /version							 zeigt Programmversion 
- /uptime							 zeigt Laufzeit des Servers 
- /broadcast 						 Nachricht an alle user im Netzwerk
- /new servername					 Neuen Servernamen (only Host)
- /new Passwort					     Neues Passwort für den server setzen (only Host)
- /kick [name]						 entfernt Nutzer (only Host)
- /whoami							 zeigt Name, Farbe, Ip, etc an
- /game <gamename> <opponent>        minigames anfragen
- /gameaccept <challenger>           minigames akzeptieren


Namensfarben und auch Text autocomplet für z.B. [/msg Ma] und der schlägt schon vor [/msg Maximilian] mit Tap bestätigen
das geht über promt_toolkit
mit: pip install prompt_toolkit
könnte man ja user optional fragen, ob sie dieses feature haben wollen, weil sie wollen evlt nicht das wir einfach so
automatisch so etwas herrunterladen.

curses python bibliothek
Um Fenster cooler da zu stellen.
Und man könnte damit brauchte man evlt kein promt_toolkit mehr. Zudem ist es schon Python standard bibliothek.
Allerdings könnte es sein, dass man das autocomplete damit nicht implementieren kann.

Command system überarbeiten, das ist grotten schlecht aktuell. wir brauchen einen zentralen command Ort.

Minigames:
tictactoe                           tik tak toe
rockpaperscissors                   schere stein papier
battleship                          schiffe versenken
hangman                             galgenmännchen
connectfour                         4 gewinnt
Cctegories                          stadt, land, fluss
highestnumber                       genneriert zufällige zahl zwischen 1 und 100000000
headortails                         Kopf oder Zahl

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
Verwendet argparse.
pyproject.toml
Definiere [project.scripts] localchat = "localchat.__main__:main".


This application optionally uses 'prompt_toolkit'(BSD License) for improved interactive terminal input.
See https://github.com/prompt-toolkit/python-prompt-toolkit for details.

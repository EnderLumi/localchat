# Localchat Architektur (Ist-Stand)

## 1. Verzeichnisstruktur
- `localchat/__main__.py`: Programmeinstieg (`localchat start`), startet `UI` + `TcpClientLogic`.
- `localchat/client/UI*`: UI-Interfaces und Implementierungen (z.B.: `CLI`, `simple`).
- `localchat/client/logic*`: Client-Logik-Interfaces und Implementierungen (`TcpClientLogic`, `TcpChat`, `TestLogic`).
- `localchat/server/logic*`: Server-Logik-Interfaces und Implementierungen (`InMemoryLogic`, `TcpServerLogic`).
- `localchat/net/*`: TCP-Protokoll, Serialisierung, Discovery (UDP).
- `localchat/util/*`: Domain-Basisklassen (`User`, `Chat`, `UserMessage`, `ChatInformation`) und Event-System.
- `test/localchatTest/*`: Unit-, Integrations- und E2E-Tests.

## 2. Laufzeitmodell
### Client
- Main-Thread: UI (`CLIMenuUI` oder `SimpleUI`).
- Logic-Thread: über `AbstractLogic.start()`.
- Pro Chat ein eigener TCP-Receive-Thread in `TcpChat`.

### Server
- Main-Thread: `TcpServerLogic.start()`.
- Accept-Thread: nimmt TCP-Clients an.
- Pro Client ein eigener Session-Thread (`_client_loop`).
- Discovery-Responder-Thread (UDP).

## 3. Kernkomponenten
### Client
- `TcpClientLogic`: erstellt/sucht Chats, hält bekannte Chats, bietet `connect_direct`.
- `TcpChat`: Join/Leave, Public/Private Messages, Connection-Events.
- `CLIMenuUI`: Menüführung, Serverstart, Direktverbindung, Settings.

### Server
- `AbstractLogic` (serverseitig): State-Verwaltung (Members, Rollen, Lock/Ban, Chatlog).
- `TcpServerLogic`: TCP-Protokoll, Session-Management, Broadcast/Private Routing.
- `InMemoryLogic`: transportfreie Referenzimplementierung.

### Netzwerk
- `tcp_protocol.py`: Pakettypen + Encoder/Decoder.
- Serialisierung: `Serializable*`-Klassen.
- Discovery: UDP Broadcast Request/Response.

## 4. Join-Handshake (ACK/NACK)
Der Join ist explizit synchronisiert:
1. Client sendet `PT_C_JOIN`.
2. Server registriert Member-State.
3. Erfolg: `PT_S_JOIN_ACK`.
4. Fehler: `PT_S_JOIN_NACK` mit `code + message`.
5. Client setzt `joined=True` erst nach ACK.

Das verhindert "halb-joined" Zustände.

## 5. TCP-Pakettypen (aktuell)
### Client -> Server
- `PT_C_JOIN = 1`
- `PT_C_PUBLIC = 2`
- `PT_C_PRIVATE = 3`
- `PT_C_LEAVE = 4`

### Server -> Client
- `PT_S_USER_JOINED = 100`
- `PT_S_USER_LEFT = 101`
- `PT_S_USER_BECAME_HOST = 102`
- `PT_S_JOIN_ACK = 105`
- `PT_S_JOIN_NACK = 106`
- `PT_S_PUBLIC = 110`
- `PT_S_PRIVATE = 111`
- `PT_S_ERROR = 120`

## 6. Structured Error Codes
Fehler werden maschinenlesbar als `(code, message)` übertragen.
Wichtige Codes:
- `join_first`
- `already_joined`
- `user_id_in_use`
- `unknown_recipient`
- `unknown_packet_type`
- `join_rejected`
- `join_failed`
- `disconnected`
- `generic`

## 7. Discovery (UDP)
- Scanner sendet Broadcast Request mit `nonce` + `reply_port`.
- Responder antwortet mit Server-Snapshot (`server_id`, `name`, `host`, `port`, `requires_password`).
- Bei `port=0` wird der tatsächlich gebundene Socket-Port verwendet.

## 8. Port-Verhalten im CLI
Beim Serverstart über `CLIMenuUI`:
- `1-1023`: blockiert.
- `1024-49151`: erlaubt, aber Warnung.
- `49152-65535`: empfohlen.

## 9. Event-System
- `EventHandler[T]` verwaltet Listener thread-safe.
- Wichtige Chat-Events:
  - User joined/left/became host
  - Public/private message
  - Connection problem/failure

## 10. Wichtig für Änderungen
- Protokolländerungen immer in vier Schritten:
  1. `localchat/net/tcp_protocol.py`
  2. `localchat/server/logicImpl/TcpServerLogic.py`
  3. `localchat/client/logicImpl/TcpChat.py`
  4. passende Tests in `test/localchatTest/net/*` + ggf. E2E
- Architekturdatei bei relevanten Änderungen direkt mitpflegen.

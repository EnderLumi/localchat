# Localchat Protokoll (TCP + Discovery)

Diese Datei beschreibt die konkreten Wire-Details.

## 1. Transportrahmen (TCP)
- Jedes TCP-Paket ist framed als:
  - `length` (4 Byte, big-endian, payload length)
  - `payload` (`length` Bytes)
- `payload[0]` ist immer der Pakettyp (`PT_*`), der Rest ist der Paket-Body.

## 2. Pakettypen
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

## 3. Bodies pro Pakettyp
### Client -> Server
- `PT_C_JOIN`:
  - `SerializableUser`
- `PT_C_PUBLIC`:
  - `SerializableString(message)`
- `PT_C_PRIVATE`:
  - `SerializableUUID(recipient_id)`
  - `SerializableString(message)`
- `PT_C_LEAVE`:
  - kein Body

### Server -> Client
- `PT_S_USER_JOINED` / `PT_S_USER_LEFT` / `PT_S_USER_BECAME_HOST`:
  - `SerializableUser`
- `PT_S_JOIN_ACK`:
  - `SerializableUser` (vom Server vergebene Session-Identität)
- `PT_S_JOIN_NACK`:
  - `SerializableString(code)`
  - `SerializableString(message)`
- `PT_S_PUBLIC` / `PT_S_PRIVATE`:
  - `SerializableUserMessage`
- `PT_S_ERROR`:
  - strukturiert: `SerializableString(code)` + `SerializableString(message)`
  - Legacy-Fallback wird clientseitig weiter unterstützt (`message` only -> `code=generic`)

## 4. Join-Handshake
1. Client sendet `PT_C_JOIN`.
2. Server antwortet mit:
  - `PT_S_JOIN_ACK` bei Erfolg, oder
  - `PT_S_JOIN_NACK` bei Ablehnung/Fehler.
3. Client gilt erst nach `JOIN_ACK` als joined.
4. Membership-Broadcasts (`PT_S_USER_JOINED`) sind fachliche Events und ersetzen nicht den ACK.

## 5. Fehlercodes
Aktuell genutzte Codes:
- `generic`
- `join_first`
- `already_joined`
- `user_id_in_use`
- `user_name_in_use`
- `unknown_recipient`
- `unknown_packet_type`
- `join_rejected`
- `join_failed`
- `disconnected`
- `server_full`

## 6. Discovery (UDP)
- Request/Response als JSON-Objekt (`utf-8`).
- Request enthält:
  - `v`, `kind`, `nonce`, `reply_port`
- Response enthält:
  - `v`, `kind`, `nonce`, `server_id`, `server_name`, `host`, `port`, `requires_password`
- Scanner akzeptiert nur Responses mit passender `nonce`.

## 7. Limits und Validierung
- Größen-/Längenlimits liegen in `localchat/config/limits.py`.
- TCP-Payload-Limit wird bei `recv_packet` validiert.
- Strings werden beim Deserialisieren gegen Maximalgröße und Encoding validiert.

## 8. Änderungsprozess für das Protokoll
Bei jeder Protokolländerung:
1. `localchat/net/tcp_protocol.py` ändern.
2. Serverpfad (`TcpServerLogic`) anpassen.
3. Clientpfad (`TcpChat`) anpassen.
4. Tests ergänzen:
  - Codec-Test
  - Fehlerpfad-/Integrations-Test
  - bei Bedarf E2E-Test

## 9. Kompatibilitätsregel
- Rückwärtskompatibilität bewusst entscheiden:
  - Entweder explizit erhalten (wie bei `PT_S_ERROR` Legacy-Decode),
  - oder als Breaking Change kennzeichnen und alle Gegenstellen im selben Schritt migrieren.

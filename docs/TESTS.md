# Teststrategie

## 1. Testarten im Projekt
- Unit-Tests:
  - Serialisierung (`Serializable*`)
  - Protokoll-Codec (`tcp_protocol`)
  - Parsing (`join_target`)
  - Settings-Modell/Store (`localchat/settings/*`)
  - UI-Logik in isolierten Dummies
- Integrationstests:
  - TCP-Client/Server-Flows
  - Error-Pfade (duplicate ID, unknown recipient, join rejection)
  - Discovery-Protokoll und UDP-Responder/Scanner
- E2E-ähnliche Flows:
  - Server + zwei Clients + Message/Leave-Ablauf

## 2. Testordner
- `test/localchatTest/client/*`
- `test/localchatTest/server/*`
- `test/localchatTest/net/*`
- `test/localchatTest/net/discovery/*`

## 3. Run Tests
- Ganze Suite:
  - `pytest -q`
- Nur ein Bereich:
  - `pytest -q test/localchatTest/net`
  - `pytest -q test/localchatTest/client`
  - `pytest -q test/localchatTest/server`
- Einzeltest:
  - `pytest -q path/to/test_file.py::TestClass::test_name`

## 4. Umgebungsabhängige Skips
Ein Teil der Netzwerktests kann skippen, wenn lokale Sockets in der Umgebung nicht verfügbar sind.
Das ist erwartetes Verhalten in restriktiven Umgebungen.

## 5. Qualitätsregeln für neue Features
- Bei Protokolländerungen immer:
  1. Codec-Test ergänzen
  2. Server-Error/Flow-Test ergänzen
  3. Client-Integrations- oder E2E-Test ergänzen
- Bei UI-Verhalten:
  - `CLIMenuUI`/`CLIChatUI`-Tests mit `_Reader`/`_Output` ergänzen
- Bei Server-State-Änderungen:
  - `server/test_ServerLogic*.py` erweitern

## 6. Spezifische Regressionen (bereits abgesichert)
- Join-Race/Host-Eindeutigkeit
- Join-Rejection mit wiederverwendbarer TCP-Connection
- Join-ACK/NACK-Handshake
- Structured Error Codes `(code, message)`
- Dynamic-Port-Reporting bei `port=0`
- Port-Policy im CLI (privileged block, registered warning)
- Settings-Laden/Speichern und Fallback-Verhalten

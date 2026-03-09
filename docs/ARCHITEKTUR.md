# Localchat Architektur (Leitlinien)

## 1. Architekturprinzipien
- Strikte Trennung zwischen UI, Client-Logik, Server-Logik und Netzwerk/Protokoll.
- Interfaces stabil halten und Implementierungen immer austauschbar gestalten.
- Netzwerk nicht als zuverlässig sehen -> Jeder Pfad braucht klare Fehlermeldungen und Timeout-strategien.
- Transportdetails dürfen nicht in UI oder Domänenmodelle auslaufen.
- Änderungen am Protokoll sind immer kompatibel geplant oder klar versioniert.

## 2. Schichtenmodell
### `config`
- Zentrale, statische Konfiguration (z. B. Defaults, Limits, Farben, Feature-Flags falls vorhanden).
- Darf von allen Schichten gelesen werden, enthält aber selbst keine Laufzeitlogik.
- Keine Seiteneffekte (kein Netzwerk, kein Dateisystemzugriff in `config`-Modulen).

### `settings`
- Persistente User-Präferenzen (laufzeitnahe Konfiguration), getrennt von statischen Defaults.
- `config.defaults.py` liefert nur Fallback-Werte; `settings` enthält nutzerspezifische Overrides.
- Enthält:
    - Modell (`AppSettings`)
    - Persistenz (`SettingsStore`, aktuell JSON-Datei)
- Darf Dateisystem-I/O machen (laden/speichern), aber keine Netzwerklogik.


### `util`
- Enthält domänennahe Basistypen und eventbasierte Hilfsklassen.
- Keine UI- oder transportspezifische Logik.

### `net`
- Zuständig für Protokoll, Kodierung/Validierung, Discovery und Transporthilfen.
- Keine Produktlogik (z. B. Rechte, Hostwechsel, Moderation).

### `client`
- UI und clientseitige Anwendungsschicht.
- Darf Netzwerk nur über Client-Logik-Abstraktionen nutzen.

### `server`
- Autoritative Zustandsverwaltung des Chats (Members, Rollen, Regeln).
- Verantwortlich für Konsistenz und Durchsetzung von Berechtigungen.

## 3. Verantwortlichkeiten
### Client-Logik
- Verbindungen initiieren und verwalten.
- UI-freundliche Commands/Aktionen anbieten.
- Serverereignisse in UI-Events übersetzen.

### Server-Logik
- Join/Leave und Rollenwechsel atomar durchführen.
- Public/Private Nachrichten korrekt routen.
- Fehler immer strukturiert und maschinenlesbar zurückgeben.

### UI
- Nur Benutzerinteraktion und Darstellung.
- Keine direkte Protokoll- oder Socketlogik.
- Darf Settings lesen/schreiben, um User-Präferenzen anzuwenden.

## 4. Verbindungs- und Join-Regeln
- Join wird als expliziter Handshake modelliert (Anfrage + Annahme/Ablehnung).
- Ein Client gilt erst als "joined", wenn der Server den Join bestätigt.
- Join-Ablehnungen müssen den Session-Zustand sauber zurückrollen.
- Mitgliedschafts-Events (z. B. "User joined") sind fachliche Broadcasts, keine Handshake-Antwort.

## 5. Protokollrichtlinien
- Pakettypen sind zentral definiert und dokumentiert.
- Fehlerantworten enthalten mindestens `code` und `message`.
- Neue Pakettypen nur einführen, wenn semantisch nötig.
- Bei Änderungen:
  1. Codec anpassen
  2. Serverpfad anpassen
  3. Clientpfad anpassen
  4. Tests (Unit + Integration) ergänzen

## 6. Threading- und Zustandsregeln
- Gemeinsamer Zustand ist immer explizit synchronisiert.
- Rollen- und Membership-Entscheidungen erfolgen atomar.
- Nebenläufigkeit wird mit Tests abgesichert (insb. Join/Rollenwechsel).
- Keine stillen Zustandsübergänge: immer klar definierte Zustandsänderungen.

## 7. Discovery- und Port-Regeln
- Discovery meldet den tatsächlich erreichbaren Serverendpunkt.
- Dynamische Ports müssen als effektive Runtime-Ports weitergegeben werden.
- Portwahlregeln in der UI dienen der Sicherheit/Usability, nicht der Kernarchitektur.

## 8. Erweiterungsregeln
- Neue Features zuerst als Use-Case + Schnittstellenänderung beschreiben.
- Danach erst Implementierung in allen betroffenen Schichten.
- Cross-Cutting Features (z. B. Passwort, Datei-Transfer) in kleinen, testbaren Schritten einführen.

## 9. Dokumentationsregeln
- Diese Datei bleibt stabil und beschreibt "wie wir bauen".
- Detailstände (konkrete Paket-IDs, konkrete Flows, aktuelle Implementierungsvarianten) gehören in spezialisierte Doku:
  - `docs/IDEEN.md` für Backlog
  - `docs/TESTS.md` für Teststrategie
  - `docs/PROTOKOLL.md` für konkrete Wire-Details

# localchat
just another stupid Lan Chat.

## Status
This project is in early development. It is not ready for production use.
Security features like encryption and password-based auth are planned but not integrated yet.

## What it does today
- Discover servers on the local network via UDP broadcast
- Direct connect by host:port (also supports URL-style join targets)
- Host a server locally from the CLI
- Public and private messages
- Basic server commands: `/help`, `/whoami`, `/list`, `/serverinfo`, `/kick`, `/newhost`
- Persistent local settings (username, name color, timestamps, join/leave notices)

## Not yet
- Encryption/authentication
- File transfer
- GUI client

## Architecture and protocol
The focus is a clean client/server split, a documented protocol, and a codebase that is easy to extend.
- Layering and design rules: [ARCHITEKTUR.md](docs/ARCHITEKTUR.md)
- Wire protocol details: [PROTOKOLL.md](docs/PROTOKOLL.md)
- Test strategy: [TESTS.md](docs/TESTS.md)

## Run (dev)
(The installation and start-up process will be significantly improved in the future!)
- Requires Python 3.9+
- Start via module:
  - `python -m localchat start`
- Or install editable and run the CLI:
  - `pip install -e .`
  - `localchat start`

## Tests
- `pytest -q` (more information in [TESTS.md](docs/TESTS.md#3-run-tests))
- Some network tests may skip if sockets are restricted

## License
GPL-3.0

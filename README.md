# AAL Core

Applied Alchemy Labs — Resonant Runtime v0.1

This repo contains the early-stage implementation of the AAL runtime designed to run on a Particle Tachyon 5 board (Ubuntu) and standard Linux dev environments.

## Architecture

- **AAL Hub** (`aal_core.hub`): message router + module loader.
- **ResonanceFrame** (`aal_core.models`): shared data structure for all modules.
- **Bus** (`aal_core.bus`): thin wrapper over Redis pub/sub (swappable later).
- **Modules** (`modules/*`): eurorack-style processes that subscribe to topics, process frames, and emit new frames.
- **Alignment System** (`aal_core.alignment`): multi-layered containment and governance for AI agents, from LLMs to AGI-adjacent capabilities. See [ALIGNMENT.md](docs/ALIGNMENT.md).

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
redis-server &
python -m aal_core.hub
```

In another terminal, you can start building simple clients to send ResonanceFrames into the system.

## Project Structure

```
aal-core/
├─ README.md
├─ pyproject.toml          # Python project configuration
├─ requirements.txt        # Python dependencies
├─ aal_core/
│  ├─ __init__.py
│  ├─ config.yaml          # routing, modules, env
│  ├─ hub.py               # AAL Hub: message router + process manager
│  ├─ api.py               # FastAPI service for control/introspection
│  ├─ models.py            # ResonanceFrame & shared types
│  ├─ bus.py               # Redis/NATS client wrapper
│  └─ utils.py
├─ modules/
│  ├─ abraxas_basic/
│  │  ├─ __init__.py
│  │  └─ main.py           # basic oracle stub
│  ├─ noctis_stub/
│  │  ├─ __init__.py
│  │  └─ main.py           # dream tagger stub
│  └─ log_sink/
│     ├─ __init__.py
│     └─ main.py           # logs frames to sqlite / stdout
└─ docker/
   ├─ Dockerfile.hub       # optional for later
   └─ Dockerfile.module
```

## Modules

### Abraxas Basic
A simple oracle module that processes text and returns insights. Currently implements a basic text reversal as a placeholder for more sophisticated oracle functionality.

### Noctis Stub
Dream analysis module that scans text for archetypal keywords and tags frames with symbolic states (shadow, anima, trickster).

### Log Sink
A logging module that captures all frames passing through the system and outputs them to stdout. Can be extended to write to SQLite or other storage backends.

## Development

Each module follows a simple pattern:
- Export a `handle_frame(frame: ResonanceFrame, bus: Bus) -> List[ResonanceFrame]` function
- Subscribe to topics via `config.yaml`
- Process incoming frames and emit new frames as needed

To add a new module:
1. Create a new directory under `modules/`
2. Add `__init__.py` and `main.py` with a `handle_frame` function
3. Add the module configuration to `aal_core/config.yaml`

## Future Enhancements

- Docker containerization
- NATS/MQTT bus alternatives
- Persistent storage (SQLite, PostgreSQL)
- Web UI for monitoring and control
- Additional modules (BeatOven, sports analysis, etc.)

## License

TBD
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Pulse is a self-healing MQTT mesh network service. Nodes run `service.py`, connect to an MQTT broker, listen for commands on `insight/$SERIAL/cmd`, and can hot-swap to a different broker via `insight/$SERIAL/jump`. The service is deployed as a Docker container.

## Commands

### Docker (primary workflow)
```sh
make up        # build and start via docker compose (detached)
make down      # stop containers
make logs      # follow compose logs
make clean     # tear down containers, images, and volumes
make build     # build image only (no start)
```

### Running tests
Tests live in `src/helper/test/` and must be run from that directory (they write logs relative to `./logs/` and import helpers via `sys.path` manipulation):
```sh
cd src/helper/test
python3 -m unittest discover -s . -p 'test*.py'   # all tests
python3 -m unittest test_helper                    # single module
```

### Local (no Docker)
```sh
pip install -r requirements.txt
cd src && python service.py
```

## Architecture

```
service.py          # entrypoint — instantiates Service, runs heartbeat loop
client.py           # MQTTClient + @subscribe decorator
helper/
  config.py         # Configuration: maps configuration.json keys to attributes
  helper.py         # Utilities: acquire_lock, elapsed, init_command_set, whoami
  calculation.py    # Arithmetic helpers (add, sub)
src/share/configuration.json   # Runtime config (broker host/port, known broker aliases, log path)
```

### Key design patterns

**`@subscribe` decorator** — attach MQTT topic subscriptions to `Service` methods at definition time. `MQTTClient.bind(service)` scans for these at startup and registers handlers; `_on_connect` re-subscribes after any reconnect.

**`Configuration`** — dynamically sets attributes from `configuration.json`. With `nested_imports: true` (current default), the inner keys of nested dicts are flattened onto the object (e.g. `config.mqtt`, `config.brokers`).

**`switch_broker`** — broker hot-swap runs in a daemon thread to avoid deadlocking the paho callback thread. The `jump` handler accepts either a broker alias (resolved via `config.brokers`) or a raw `host:port` string.

**`init_command_set`** — reflects all public callables off an object into a dict, adding space-separated aliases for underscore names. Used to expose `MQTTClient` methods as a command registry.

### MQTT topic structure
- `insight/$SERIAL/cmd` — text commands (`help`, `status`, `servo`, `prompt`)
- `insight/$SERIAL/jump` — broker-swap trigger (alias or `host:port`)
- `insight/$SERIAL/servo` — servo control (hostname-specific)
- `insight/$SERIAL/status` — outbound status/response channel
- `insight/$SERIAL/alive` — periodic heartbeat (every `delay_main_s` seconds, default 600)

### Configuration (`src/share/configuration.json`)
Notable fields: `mqtt.host`, `mqtt.port`, `mqtt.topic`, `mqtt.client_id`, `brokers` (alias→IP map), `delay_main_s`, `logging_path`, `logging_level`.

### `src/helper` is a git submodule
`src/helper/` has its own `.git` directory and is managed separately (via `myrepos`/`mr`). Run `mr -t checkout` in the repo root after cloning to initialize it.

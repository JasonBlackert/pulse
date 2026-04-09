# pulse

Self-healing MQTT mesh network. Nodes auto-discover each other, elect a primary broker, and hot-swap brokers on failure — all without manual intervention.

## Setup

```sh
git clone <repo>
mr -t checkout          # initialize src/helper submodule
```

## Running

### Docker (recommended)

```sh
make up        # build and start via docker compose (detached)
make down      # stop containers
make logs      # follow logs
make clean     # tear down containers, images, and volumes
make build     # build image only
```

### Local

```sh
pip install -r requirements.txt
cd src && python service.py
```

### Tests

Tests live in `src/helper/test/` and must be run from that directory:

```sh
cd src/helper/test
python3 -m unittest discover -s . -p 'test*.py'   # all tests
python3 -m unittest test_helper                    # single module
```

## Architecture

```
service.py          # entrypoint — Service + Status, heartbeat loop, election logic
client.py           # MQTTClient + @subscribe decorator, broker switching
helper/
  config.py         # Configuration: maps configuration.json keys to attributes
  helper.py         # Utilities: acquire_lock, elapsed, init_command_set, elect
  calculation.py    # Arithmetic helpers
src/share/configuration.json   # Runtime config (broker host/port, known broker aliases, etc.)
```

### Election & discovery

Each node publishes an announcement on connect and tracks peers via `insight/election/announce`. The node with the lowest `start_time` wins and becomes **primary**; the second-oldest becomes **fallback**.

On broker failure, the dead broker's owner is evicted from the peer list and all nodes re-elect and converge on the new primary's broker. If no peers are found within `discovery_timeout_s` (default 15 s), the node cycles through all known brokers until it finds one with peers.

Roles: `candidate` → `primary` | `fallback` | `follower`

### Broker hot-swap

`switch_broker` runs in a daemon thread to avoid deadlocking the paho callback thread. The `jump` handler accepts either a broker alias (resolved via `config.brokers`) or a raw `host:port` string. All subscriptions are automatically re-registered on reconnect.

### `@subscribe` decorator

Attach MQTT subscriptions to `Service` methods at definition time. `MQTTClient.bind(service)` scans for these at startup and re-subscribes after any reconnect.

## Topic structure

| Topic | Direction | Purpose |
|---|---|---|
| `insight/$SERIAL/cmd` | inbound | Text commands (`help`, `status`, `servo`, `prompt`) |
| `insight/$SERIAL/jump` | inbound | Broker-swap trigger (alias or `host:port`) |
| `insight/$SERIAL/servo` | inbound | Servo control (hostname-specific) |
| `insight/$SERIAL/status` | outbound | Status / command responses |
| `insight/$SERIAL/alive` | outbound | Periodic heartbeat (every `delay_main_s` seconds) |
| `insight/election/announce` | both | Peer discovery and election |

## Configuration (`src/share/configuration.json`)

| Key | Default | Description |
|---|---|---|
| `mqtt.host` | `10.0.10.21` | Broker host |
| `mqtt.port` | `1883` | Broker port |
| `mqtt.topic` | `insight` | Topic prefix |
| `mqtt.client_id` | `null` | MQTT client ID (auto-assigned if null) |
| `brokers` | — | Alias → IP map of known brokers |
| `delay_main_s` | `2` | Heartbeat interval (seconds) |
| `primary_timeout_s` | `30` | Seconds of silence before primary is considered dead |
| `broker_failure_timeout_s` | `30` | Seconds before an unexpected disconnect triggers failover |
| `discovery_timeout_s` | `15` | Seconds to wait for peers before scanning other brokers |

## TODO

- [ ] Add more functionality to the driver methods
- [ ] Add important uptime messages to `insight/+/status`

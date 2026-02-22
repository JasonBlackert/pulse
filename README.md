# pulse
Reworked self-healing mesh network.

Foundation laid out to swap client between different brokers

## Setup
- Install paho-mqtt
- Run `mr -t checkout` in working directory

## Tree:
```Shell
.
├── README.md
└── src
    ├── client.py
    ├── helper
    │   ├── calculation.py
    │   ├── config.py
    │   ├── helper.py
    │   ├── README.md
    │   └── test
    │       ├── logs
    │       │   ├── __init__.log
    │       │   └── unittest.log
    │       ├── share
    │       │   └── configuration.json
    │       ├── test_calculation.py
    │       ├── test_config.py
    │       └── test_helper.py
    ├── logs
    │   ├── __init__.log
    │   └── service.log
    ├── service.py
    └── share
        └── configuration.json

8 directories, 16 files
```

### TODO:
- [x] Swap between brokers on `insight/+/jump`
- [ ] Add more functionality to the driver methods
- [ ] Add important uptime messages to `insight/+/status`
- [ ] Make more independent for when brokers go down


## Topic Structure
STATUS: `insight/$SERIAL/status`
JUMP: `insight/$SERIAL/jump`
CMD: `insight/$SERIAL/cmd`


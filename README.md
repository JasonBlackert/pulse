# pulse
Reworked self-healing mesh network.

Foundation laid out to swap client between different brokers

### TODO:
- [x] Swap between brokers on `insight/+/jump`
- [ ] Add more functionality to the driver methods
- [ ] Add important uptime messages to `insight/+/status`
- [ ] Make more independent for when brokers go down


# Topic Structure
[STATUS]: `insight/$SERIAL/status`
[JUMP]: `insight/$SERIAL/jump`
[CMD]: `insight/$SERIAL/cmd`


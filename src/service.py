"""
    developer: Jason E. Blackert

    service.py: "What is my purpose?"
    developer:  "You act as main.py, running whatever service is desired."
    service.py: "Oh my god."
"""
import re
import time
import json
import socket
import logging
from threading import Timer

from client import MQTTClient, subscribe
from helper.config import Configuration, load_json
from helper.helper import init_command_set, elect

hostname = socket.gethostname()

class Status():
    def __init__(self, broker_host: str = "8.8.8.8"):
        self.logger = logging.getLogger(__name__)
        self.available_modes = ["idle", "running", "stopped", "swapping", "discovery"]
        self.mode = "idle"
        self._broker_host = broker_host
        self.ip_addr = self._get_ip_address()
        self.start_time = time.time()
        self.role = "candidate"   # candidate | primary | fallback | follower
        self.peers: dict = {}     # hostname -> {ip, start_time, last_seen}
        self.logger.info(f"{hostname}@{self.ip_addr}")

    def _get_ip_address(self) -> str:
        """Return the IP of the interface used to reach the broker."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self._broker_host, 1883))
            return s.getsockname()[0]
        except Exception:
            self.logger.warning("Could not determine outgoing IP, using fallback")
            return "127.0.0.1"
        finally:
            s.close()

    def report(self, reason: str = "reason"):
        """Generates immutable status report."""

        return {
            "name" : hostname,
            "ip": self.ip_addr,
            "time" : time.time(),
            "mode" : self.mode if self.mode in self.available_modes else "unknown",
            "reason": reason
        }

    def announce(self, broker_host: str = "") -> dict:
        """Generates election announcement payload."""
        return {
            "name": hostname,
            "ip": self.ip_addr,
            "start_time": self.start_time,
            "broker_ip": broker_host,
        }

class Service():
    """Acts as main.py runs whatever services are desired"""

    def __init__(self):
        configuration = load_json("share/configuration.json")
        self.config = Configuration(configuration)

        logging.basicConfig(filename=self.config.logging_path, level=self.config.logging_level)
        self.logger = logging.getLogger(__name__)

        self.logger.info(hostname)
        # Initialize Status Report
        self.status = Status(broker_host=self.config.mqtt["host"])

        # pub-sub client / dispatcher node
        self.client = MQTTClient(
            self.config,
            on_broker_failure=self._handle_broker_failure,
            on_reconnect=self._announce,
        )
        self.client.bind(self)
        self.client.loop_start()

        # command set
        self.valid_commands = ["help", "status", "servo", "prompt" ]

        self._init_command_sets()
        self._last_announce_s: float = 0
        self._discovery_timer: Timer = None
        self._discovery_brokers: list = list(dict.fromkeys(self.config.brokers.values()))
        self._discovery_idx: int = 0

    def _init_command_sets(self):
        self.commands = {}
        self.commands["client"] = init_command_set(self.client)
        self.logger.info(self.commands["client"].keys())
        
    def _all_peers(self) -> dict:
        """Return peers dict including self, for complete election results."""
        all_peers = dict(self.status.peers)
        all_peers[hostname] = {
            "ip": self.status.ip_addr,
            "start_time": self.status.start_time,
        }
        return all_peers

    # -------- Discovery --------
    def _start_discovery_timer(self):
        """(Re)start the discovery watchdog. Fires if no peers found within timeout."""
        if self._discovery_timer:
            self._discovery_timer.cancel()
        timeout = getattr(self.config, 'discovery_timeout_s', 15)
        self._discovery_timer = Timer(timeout, self._do_discovery)
        self._discovery_timer.daemon = True
        self._discovery_timer.start()

    def _do_discovery(self):
        """No peers found — try the next known broker."""
        if self.status.peers:
            return
        self.status.mode = "discovery"
        brokers = self._discovery_brokers
        for _ in range(len(brokers)):
            candidate = brokers[self._discovery_idx % len(brokers)]
            self._discovery_idx += 1
            if candidate != self.client._host:
                self.logger.info(f"[discovery] no peers, trying broker at {candidate}")
                self.client.switch_broker(candidate, int(self.config.mqtt["port"]))
                return
        self.logger.warning("[discovery] exhausted all known brokers, retrying")
        self._start_discovery_timer()

    # -------- Election --------
    def _announce(self):
        """Publish this node's election announcement and reset discovery watchdog."""
        self._last_announce_s = time.time()
        # Reset last_seen so stale timestamps don't trigger immediate peer eviction
        for peer in self.status.peers.values():
            peer["last_seen"] = self._last_announce_s
        self.client.publish(
            f"{self.config.mqtt['topic']}/election/announce",
            json.dumps(self.status.announce(broker_host=self.client._host))
        )
        self._start_discovery_timer()

    def _update_role(self):
        """Recompute this node's role from current peers."""
        primary, fallback = elect(self._all_peers())
        if primary == hostname:
            self.status.role = "primary"
        elif fallback == hostname:
            self.status.role = "fallback"
        else:
            self.status.role = "follower"
        self.logger.info(f"[election] role={self.status.role} primary={primary} fallback={fallback}")

    def _failover_to_primary(self):
        """After a failure event, switch brokers to converge on the new primary."""
        primary, _ = elect(self._all_peers())
        if primary == hostname:
            if self.status.ip_addr != self.client._host:
                self.logger.info(f"[election] becoming primary, switching to own broker at {self.status.ip_addr}")
                self.client.switch_broker(self.status.ip_addr, int(self.config.mqtt["port"]))
        elif primary and primary in self.status.peers:
            target = self.status.peers[primary].get("ip")
            if target and target != self.client._host:
                self.logger.info(f"[election] following primary broker {primary} at {target}")
                self.client.switch_broker(target, int(self.config.mqtt["port"]))
        else:
            self.logger.info("[election] no primary to follow, entering discovery")
            self._start_discovery_timer()

    def _handle_broker_failure(self):
        """Evict the node that owns the dead broker, reset own start_time if it was us, and re-elect."""
        dead_host = self.client._host
        dead_node = next((n for n, p in self.status.peers.items() if p.get("ip") == dead_host), None)
        if dead_node:
            self.logger.warning(f"[election] broker at {dead_host} unreachable, evicting {dead_node}")
            del self.status.peers[dead_node]
        if self.status.ip_addr == dead_host:
            self.status.start_time = time.time()
            self.logger.info("[election] reset start_time after own broker failure — yielding seniority")
        self._update_role()
        self._failover_to_primary()

    @subscribe("insight/election/announce")
    def handle_announce(self, topic, payload):
        try:
            peer = json.loads(payload)
            name = peer["name"]
            if name == hostname:
                return
            self.status.peers[name] = {
                "ip": peer["ip"],
                "start_time": peer["start_time"],
                "last_seen": time.time(),
                "broker_ip": peer.get("broker_ip"),
            }
            # Found peers — stop discovery
            if self.status.mode == "discovery":
                if self._discovery_timer:
                    self._discovery_timer.cancel()
                    self._discovery_timer = None
                self.status.mode = "idle"
                self.logger.info(f"[discovery] found peer {name}, rejoining pack")
            self._update_role()
            if name != hostname and time.time() - self._last_announce_s > 5:
                self._announce()
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.warning(f"[election] bad announce payload: {e}")

    @subscribe("insight/+/alive")
    def handle_alive(self, topic, payload):
        try:
            report = json.loads(payload)
            name = report["name"]
            if name in self.status.peers:
                self.status.peers[name]["last_seen"] = time.time()
            elif name != hostname:
                # Unknown peer is alive — re-announce so they can discover us
                self._announce()
                return
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.warning(f"[election] bad alive payload: {e}")
            return

        # Check if the current primary has gone silent
        primary, _ = elect(self._all_peers())
        if primary is None or primary == hostname:
            return

        timeout_s = getattr(self.config, 'primary_timeout_s', 30)
        primary_last_seen = self.status.peers.get(primary, {}).get("last_seen", 0)
        if time.time() - primary_last_seen > timeout_s:
            self.logger.warning(f"[election] primary {primary} timed out, re-electing")
            del self.status.peers[primary]
            self._update_role()
            self._failover_to_primary()

    # -------- Bound Commands --------
    @subscribe("insight/+/cmd")
    def handle_cmds(self, topic, payload):
        self.logger.info(f"[{topic}]: {payload}")

        command = payload.strip()
        if command not in self.valid_commands:
            self.logger.warning(f"[{topic}]: invalid command received: {command}")
            return

        getattr(self, f"do_{command}")()

    @subscribe(f"insight/{hostname}/servo")
    def servo_handler(self, topic, payload):
        self.logger.info(f"[{topic}] -> {payload}")

    @subscribe(f"insight/{hostname}/jump")
    def jump(self, topic, payload):
        self.logger.debug(f"Received jump request with {payload}")
        
        if payload in self.config.brokers.keys():
            payload = self.config.brokers[payload]

        # Basic sanity (don’t let random strings become a host)
        new_host, new_port = (payload.split(":", 1) + [self.config.mqtt["port"]])[:2]
        if not re.match(r"^[a-zA-Z0-9\.\-]+$", new_host):
            self.logger.warning(f"Rejecting invalid broker host: {new_host}")
            return

        self.client.switch_broker(new_host, new_port)

    # --------- Serving Methods ---------
    def do_status(self):
        report = self.status.report(reason="on_request")
        self.client.unicast([json.dumps(report)], [hostname], "status")

    def do_help(self):
        self.status.mode = "running"
        self.client.unicast([f"valid commands: {self.valid_commands}"], [hostname], "status")
        self.status.mode = "idle"
    
    def do_servo(self):
        # TBD
        pass

    def do_prompt(self):
        self.status.mode = "running"
        self.client.unicast([f"sending prompt..."], [hostname], "status")
        self.status.mode = "idle"

def main():
    srv = Service()
    srv.logger.info("Initialized and running...")

    while True:
        try:
            report = srv.status.report()
            srv.client.unicast([json.dumps(report)], [hostname], "alive")
            if not srv.status.peers and srv.status.mode != "discovery":
                srv.logger.info("[discovery] no peers after heartbeat, starting discovery scan")
                srv._start_discovery_timer()
            time.sleep(srv.config.delay_main_s)
        except KeyboardInterrupt:
            srv.logger.error("Exiting main-loop")
            srv.client.stop()
            break
        
if __name__ == "__main__":
    main()


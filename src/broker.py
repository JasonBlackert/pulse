"""
    Author: Jason E. Blackert

    broker.py: "What is my purpose?"
    developer: "You initialize an MQTT broker and provide methods to listen and publish"
    broker.py: "Oh my god."
"""
import os
import logging
import paho.mqtt.client as mqtt

from itertools import product
from helper.config import Configuration
from helper.helper import elapsed, whoami


class MQTTBroker:
    def __init__(self, configuration: Configuration):
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initializing: MQTTBroker ...")
        self.hostname = os.getlogin()

        self.config = configuration

        base = self.config.mqtt["topic"]
        self.base_topic = base.rstrip("/")

        self.client = mqtt.Client(client_id=self.hostname)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # -------- Callbacks --------
    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info("connected rc=%s", rc)
        # subscribe to all topics under base
        client.subscribe(f"{self.base_topic}/#")

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="replace")
        self.logger.info("rx %s: %s", msg.topic, payload)

        # Example routing:
        # insight/<hostname>/cmd  OR  insight/cmd
        parts = msg.topic.split("/")
        if len(parts) < 2 or parts[0] != self.base_topic:
            return

        # TODO: route by parts[-1], parts[1], etc.

    @elapsed(out=logging.info)
    def start(self):
        self.client.connect(self.config.mqtt["host"], self.config.mqtt["port"])
        self.client.loop_start()

    @elapsed(out=logging.debug)
    def publish(self, *args, **kwargs):
        return getattr(self.client, "publish")(*args, **kwargs)

    @elapsed(out=logging.debug)
    def multicast(
        self,
        cmds: list[str],
        topic: str = "cmd",
        msg: str = "multicasting",
    ) -> None:
        self.logger.info(f"{msg}: {cmds}")
        for cmd in cmds:
            self.publish(f"{self.config.mqtt['topic']}/{topic}", cmd)

    @elapsed(out=logging.debug)
    def unicast(
        self,
        cmds: list[str],
        serials: list[str],
        topic: str = "cmd",
        msg="unicasting",
    ) -> None:
        self.logger.info(f"{msg}: {cmds} to {serials}")
        for cmd, serial in product(cmds, serials):
            self.publish(f"{self.config.mqtt['topic']}/{serial}/{topic}", cmd)


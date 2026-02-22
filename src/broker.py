"""
    Author: Jason E. Blackert

    broker.py: "What is my purpose?"
    developer: "You initialize an MQTT broker and provide methods to listen and publish"
    broker.py: "Oh my god."
"""
import itertools
import logging

import paho.mqtt.client as mqtt

from helper.config import Configuration
from helper.helper import elapsed, whoami



class MQTTBroker:
    def __init__(self, configuration: Configuration):
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initializing: MQTTBroker ...")
        self.config = configuration

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        self.logger.info("client connected with result code " + str(rc))

    def _on_message(self, client, userdata, msg):
        if msg.topic != self.config.mqtt["topic"]:
            return
        self.logger.info(f"{msg.topic}")

    def alive(self):
        msg = "{self.client}: is alive!"
        self.logger.debug(msg)
        return msg

    @elapsed
    def start(self):
        self.client.connect(self.config.mqtt["host"], self.config.mqtt["port"])
        self.client.loop_start()

    @elapsed
    def publish(self, *args, **kwargs):
        return getattr(self.client, "publish")(*args, **kwargs)

    @elapsed
    def multicast(
        self,
        cmds: list[str],
        topic: str = "cmd",
        msg: str = "multicasting",
    ) -> None:
        self.logger.info(f"{msg}: {cmds}")
        for cmd in cmds:
            self.client.publish(f"{self.config.mqtt['topic']}/{topic}", cmd)

    @elapsed
    def unicast(
        self,
        cmds: list[str],
        serials: list[str],
        topic: str = "cmd",
        msg="unicasting",
    ) -> None:
        self.logger.info(f"{msg}: {cmds} to {serials}")
        for cmd, serial in itertools.product(cmds, serials):
            self.client.publish(f"{self.config.mqtt['topic']}/{serial}/{topic}", cmd)


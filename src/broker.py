import itertools
import logging

import paho.mqtt.client as mqtt

from helper.config import parse_args
from helper.src.helper import elapsed

args = parse_args()
config = args.config
log = logging.getLogger(__name__)

MQTT_TOPIC = config["mqtt"]["topic"]


class MqttBroker:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        log.info("client connected with result code " + str(rc))

    def on_message(self, client, userdata, msg):
        if msg.topic != MQTT_TOPIC:
            return
        log.info(f"{msg.topic}")

    @elapsed
    def start(self):
        self.client.connect(config["mqtt"]["host"], config["mqtt"]["port"])
        self.client.loop_start()

    def publish(self, *args, **kwargs):
        return getattr(self.client, "publish")(*args, **kwargs)

    def multicast(
        self,
        cmds: list[str],
        topic: str = "cmd",
        msg: str = "Multicasting",
    ) -> None:
        log.info(f"{msg}: {cmds}")
        for cmd in cmds:
            self.client.publish("Insight/{topic}", cmd)

    def unicast(
        self,
        cmds: list[str],
        serials: list[str],
        topic: str = "cmd",
        msg="Unicasting",
    ) -> None:
        log.info(f"{msg}: {cmds} to {serials}")
        for cmd, serial in itertools.product(cmds, serials):
            self.client.publish(f"Insight/{serial}/{topic}", cmd)

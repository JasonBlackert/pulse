"""
    Author: Jason E. Blackert

    service.py: "What is my purpose?"
    developer:  "You act as main.py, running whatever service is desired."
    service.py: "Oh my god."
"""
import os
import re
import time
import json
import logging

from broker import MQTTBroker
from client import MQTTClient
from decorators import subscribe

from helper.config import Configuration, load_json
from helper.helper import init_command_set

CONFIGURATION_PATH = "share/configuration.json"
LOGGING_PATH = "logs/service.log"

MAIN_DELAY_S = 60

hostname = os.getlogin()
PAYLOAD_ALIVE = f"{hostname} is alive"

class Service():
    """Acts as main.py runs whatever services are desired"""
    def __init__(self):
        configuration = load_json(CONFIGURATION_PATH)

        logging.basicConfig(filename=LOGGING_PATH, level=configuration["logging_level"])
        self.logger = logging.getLogger(__name__)

        self.config = Configuration(configuration)
        # publish-only node
        self.broker = MQTTBroker(self.config)
        self.broker.start()

        # client / dispatcher node
        self.client = MQTTClient(self.config.mqtt["host"])
        self.client.bind(self)
        self.client.loop_start()

        # command set
        self.commands = {}
        self._init_command_sets()

    def _registster_handlers(self, cli: MQTTClient):
        pass

    def _init_command_sets(self):
        self.commands["broker"] = init_command_set(self.broker)
        self.logger.info(self.commands["broker"].keys())
        
    def run(self):
        main(self)

    @subscribe(f"insight/commands/#")
    def handle_cmds(self, topic, payload):
        logging.info(f"[CMD {topic}]: {payload}")

    @subscribe(f"insight/{hostname}/servo")
    def server_handler(topic, payload):
        print(f"[SERVO] {topic} -> {payload}")

    @subscribe(f"insight/{hostname}/jump")
    def jump(self, topic, payload):
        logging.debug(f"Received jump request with {payload}")
        
        # Basic sanity (don’t let random strings become a host)
        new_host = payload.strip()
        new_port = 1883
        if not re.match(r"^[a-zA-Z0-9\.\-]+$", new_host):
            logging.warning(f"Rejecting invalid broker host: {new_host}")
            return

        self.client.switch_broker(new_host, new_port)

def main(srv: Service):
    srv.logger.info(f"Initialized and running...")

    # Begin Main Loop
    while True:
        try:
            srv.broker.unicast([PAYLOAD_ALIVE], [f"{os.getlogin()}"], "alive")
            time.sleep(0.25)
        
            time.sleep(MAIN_DELAY_S)
        except KeyboardInterrupt as ke:
            srv.logger.error(f"Exiting main-loop: {ke}")
            break
        
if __name__ == "__main__":
    srv = Service()
    srv.run()

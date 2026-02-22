"""
    Author: Jason E. Blackert

    service.py: "What is my purpose?"
    developer:  "You act as main.py, running whatever service is desired."
    service.py: "Oh my god."
"""
import os
import time
import json
import logging

from socket import gethostname

from broker import MQTTBroker
from helper.config import Configuration, load_json
from helper.helper import init_command_set

CONFIGURATION_PATH = "share/configuration.json"
LOGGING_PATH = "logs/service.log"

MAIN_DELAY_S = 15


class Service():
    """Acts as main.py runs whatever services are desired"""
    def __init__(self):
        configuration = load_json(CONFIGURATION_PATH)

        logging.basicConfig(filename=LOGGING_PATH, level=configuration["logging_level"])
        self.logger = logging.getLogger(__name__)

        self.config = Configuration(configuration)
        # publish-only node
        self.broker = MQTTBroker(self.config, subscribe=False)
        self.broker.start()

        # controller / listener node
        # self.client = MQTTBroker(self.config, subscribe=True)
        # self.client.start()

        self.commands = {}

        self._init_command_sets()

    def _init_command_sets(self):
        self.commands["broker"] = init_command_set(self.broker)
        self.logger.info(self.commands["broker"].keys())
        
    def run(self):
        main(self)

def main(srv: Service):
    srv.logger.info(f"Initialized and running...")

    # Begin Main Loop
    while True:
        try:
            srv.broker.unicast(["hello"], [f"{os.getlogin()}"], "cmd")
            time.sleep(0.25)
        
            time.sleep(MAIN_DELAY_S)
        except KeyboardInterrupt as ke:
            srv.logger.error(f"Exiting main-loop: {ke}")
            break
        
if __name__ == "__main__":
    srv = Service()
    srv.run()

"""
    Author: Jason E. Blackert

    service.py: "What is my purpose?"
    developer:  "You act as main.py, running whatever service is desired."
    service.py: "Oh my god."
"""
import time
import json
import logging

from socket import gethostname()

from broker import MQTTBroker
from helper.config import Configuration, load_json
from helper.helper import init_command_set

CONFIGURATION_PATH = "share/configuration.json"
LOGGING_PATH = "logs/service.log"

MAIN_DELAY_S = 2


class Service():
    """Acts as main.py runs whatever services are desired"""
    def __init__(self):
        configuration = load_json(CONFIGURATION_PATH)

        logging.basicConfig(filename=LOGGING_PATH, level=configuration["logging_level"])
        self.logger = logging.getLogger(__name__)

        self.config = Configuration(configuration)
        self.broker = MQTTBroker(self.config)
        self.commands = {}

        self._init_command_sets()

    def _init_command_sets(self):
        self.commands["broker"] = init_command_set(self.broker)
        self.logger.info(self.commands["broker"].keys())
        
    def run(self):
        main(self)

def main(srv: Service):
    srv.broker.start()
    srv.logger.info(f"Initialized and running...")

    # Begin Main Loop
    while True:
        try:
            srv.broker.unicast(["hello"], [f"{gethostname()}"], "cmd")
            time.sleep(MAIN_DELAY_S)
        except KeyboardInterrupt as ke:
            srv.logger.error(f"Exiting main-loop: {ke}")
            break
        
if __name__ == "__main__":
    srv = Service()
    srv.run()

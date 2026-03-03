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
import socket
import logging

from client import MQTTClient, subscribe
from helper.config import Configuration, load_json
from helper.helper import init_command_set

hostname = os.getlogin()

class Status():
    def __init__(self):
        self.available_modes = ["idle", "running", "stopped", "swapping"]
        self.mode = "idle"
        
        self.report_dict = {
            "name" : hostname,
            "ip": socket.gethostbyname(hostname),
            "time" : time.time(),
            "mode" : self.mode,
            "reason": None
        }

    def report(self, reason: str = "reason"):
        """Generates status report."""
        self.report_dict["time"] = time.time()
        
        if self.mode in self.available_modes:
            self.report_dict["mode"] = self.mode
            
        self.report_dict["reason"] = reason
        return self.report_dict


class Service():
    """Acts as main.py runs whatever services are desired"""
    def __init__(self):
        configuration = load_json("share/configuration.json")
        self.config = Configuration(configuration)

        logging.basicConfig(filename=self.config.logging_path, level=self.config.logging_level)
        self.logger = logging.getLogger(__name__)

        # Initialize Status Report
        self.status = Status()

        # pub-sub client / dispatcher node
        self.client = MQTTClient(self.config)
        self.client.bind(self)
        self.client.loop_start()

        # command set
        self._init_command_sets()

    def _init_command_sets(self):
        self.commands = {}
        self.commands["client"] = init_command_set(self.client)
        self.logger.info(self.commands["client"].keys())
        
    # -------- Bound Commoands --------
    @subscribe("insight/+/cmd")
    def handle_cmds(self, topic, payload):
        self.logger.info(f"[{topic}]: {payload}")
        if payload.strip() == "status":
            self.provide_status()

    @subscribe(f"insight/{hostname}/servo")
    def servo_handler(topic, payload):
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
    def provide_status(self):
        self.client.unicast([f"{self.status.report()}"], [f"{os.getlogin()}"], "status")

def main():
    srv = Service()
    srv.logger.info(f"Initialized and running...")

    while True:
        try:
            report = srv.status.report()
            srv.client.unicast([f"{report}"], [f"{os.getlogin()}"], "alive")
            time.sleep(srv.config.delay_main_s)
        except KeyboardInterrupt as ke:
            srv.logger.error(f"Exiting main-loop: {ke}")
            srv.client.stop()
            break
        
if __name__ == "__main__":
    main()


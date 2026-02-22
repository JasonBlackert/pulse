

import paho.mqtt.client as mqtt

from typing import Callable, Dict, List


class MQTTClient:
    def __init__(self, host="localhost", port=1883):
        self._handlers: Dict[str, List[callable]] = {}
        self._client = mqtt.Client()
        self._client.on_message = self._on_message
        self._client.connect(host, port)
        print(f"Initialized on {host}:{port}")

    def subscribe(self, topic: str):
        """Decorator: register handler for topic"""
        def decorator(func: Callable):
            self._handlers.setdefault(topic, []).append(func)
            self._client.subscribe(topic)
            return func
        return decorator
    
    def _on_message(self, client, userdata, msg):
        print(f"message received")
        payload = msg.payload.decode()
        topic = msg.topic

        for subscribed_topic, handlers in self._handlers.items():
            if mqtt.topic_matches_sub(subscribed_topic, topic):
                for handler in handlers:
                    handler(topic, payload)

    def loop_start(self):
        self._client.loop_start()

    def loop_forever(self):
        self._client.loop_forever()


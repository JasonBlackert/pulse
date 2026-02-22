"""
    Author: Jason E. Blackert

    client.py: "What is my purpose?"
    developer: "You initialize an MQTT client and provide methods to listen and swap
                to other brokers."
    client.py: "Oh my god."
"""
# client.py
import logging
import paho.mqtt.client as mqtt

from itertools import product
from threading import Lock, Thread
from typing import Callable, Dict, List, Tuple, Any

from dataclasses import dataclass

from helper.helper import acquire_lock, elapsed
from helper.config import Configuration

Handler = Callable[[str, str], None]

@dataclass(frozen=True)
class Subscription:
    topic: str
    qos: int = 0

def subscribe(topic: str, qos: int = 0):
    """Decorator: attach MQTT subscription metadata to a method."""
    def deco(func: Callable[..., Any]):
        subs = getattr(func, "__mqtt_subscriptions__", [])
        subs.append(Subscription(topic=topic, qos=qos))
        setattr(func, "__mqtt_subscriptions__", subs)
        return func
    return deco

class MQTTClient:
    def __init__(self, configuration: Configuration = None):
        self.config = configuration
        self._host = self.config.mqtt["host"]
        self._port = self.config.mqtt["port"]
        self._client_id = self.config.mqtt["client_id"]
        self._lock = Lock()

        self.logger = logging.getLogger(__name__)

        # topic -> list[handler]
        self._handlers: Dict[str, List[Handler]] = {}
        # topic -> qos
        self._subs: Dict[str, int] = {}

        # client instantiation
        self._client = mqtt.Client(client_id=self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._client.connect(self._host, self._port)
        print(f"[MQTTClient] initialized on {self._host}:{self._port}")

    def loop_start(self):
        self._client.loop_start()

    def loop_forever(self):
        self._client.loop_forever()

    def stop(self):
        with acquire_lock(self._lock, timeout=1) as acquired:
            if not acquired:
                self.logger.warning(f"Could not acquire {self._lock}") 
                return  

            try:
                self._client.loop_stop()
            finally:
                try:
                    self._client.disconnect()
                except Exception:
                    pass

    # -------- Binding (one-time) --------
    def bind(self, service_obj: Any):
        """
        Scan service_obj for methods decorated with @subscribe and register them once.
        """
        for name in dir(service_obj):
            meth = getattr(service_obj, name, None)
            subs = getattr(meth, "__mqtt_subscriptions__", None)
            if not subs:
                continue

            for sub in subs:
                self._handlers.setdefault(sub.topic, []).append( lambda topic, payload, m=meth: m(topic, payload))
                # keep highest qos if same topic appears multiple times
                self._subs[sub.topic] = max(self._subs.get(sub.topic, 0), sub.qos)

        # If already connected, subscribe immediately; otherwise on_connect will do it.
        with acquire_lock(self._lock, timeout=1) as acquired:
            if not acquired:
                self.logger.warning(f"Could not acquire {self._lock}") 
                return

            for topic, qos in self._subs.items():
                self._client.subscribe(topic, qos=qos)

     # -------- Broker switching (no rebind needed) --------
    def switch_broker(self, new_host: str, new_port: int = 1883):
        """
        Switch brokers while keeping handlers/subscriptions.
        Runs the reconnect sequence in a separate thread to avoid callback-thread deadlocks.
        """
        def _do_switch():
            with acquire_lock(self._lock, timeout=1) as acquired:
                if not acquired:
                    self.logger.warning(f"Could not acquire {self._lock}") 
                    return

                print(f"[MQTT] Switching broker {self._host}:{self._port} -> {new_host}:{new_port}")
                try:
                    self._client.disconnect()
                except Exception:
                    pass

                # Update target
                self._host = new_host
                self._port = new_port

                # TODO Add reconnect ability
                # Reconnect; on_connect will re-subscribe
                # self._client.reconnect()  # uses same socket params? safest to do connect again
                # If reconnect() misbehaves in your environment, replace with:
                self._client.connect(self._host, self._port)

        Thread(target=_do_switch, daemon=True).start()

    # -------- Callbacks ---------
    def _on_connect(self, client, userdata, flags, rc):
        print(f"[MQTT] Connected rc={rc} to {self._host}:{self._port}")
        if rc != 0:
            return

        # Always re-subscribe on connect/reconnect
        with acquire_lock(self._lock, timeout=1) as acquired:
            if not acquired:
                self.logger.warning(f"Could not acquire {self._lock}") 
                return
            
            for topic, qos in self._subs.items():
                client.subscribe(topic, qos=qos)
                print(f"[MQTT] Subscribed {topic} qos={qos}")

    def _on_message(self, client, userdata, msg):
        print(f"message received")
        payload = msg.payload.decode()
        topic = msg.topic

        for subscribed_topic, handlers in self._handlers.items():
            if mqtt.topic_matches_sub(subscribed_topic, topic):
                for handler in handlers:
                    handler(topic, payload)

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"[MQTT] Unexpected disconnect rc={rc}")
            return 

        print("[MQTT] Clean disconnect")

    # -------- Publish Methods --------
    @elapsed(out=logging.debug)
    def publish(self, *args, **kwargs):
        return getattr(self._client, "publish")(*args, **kwargs)

    @elapsed(out=logging.debug)
    def multicast(self, cmds: list[str], topic: str = "cmd", msg: str = "multicasting",) -> None:
        self.logger.info(f"{msg}: {cmds}")
        for cmd in cmds:
            self.publish(f"{self.config.mqtt['topic']}/{topic}", cmd)

    @elapsed(out=logging.debug)
    def unicast(self, cmds: list[str], serials: list[str], topic: str = "cmd", msg="unicasting") -> None:
        self.logger.info(f"{msg}: {cmds} to {serials}")
        for cmd, serial in product(cmds, serials):
            self.publish(f"{self.config.mqtt['topic']}/{serial}/{topic}", cmd)


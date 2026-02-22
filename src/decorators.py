# decorators.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

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

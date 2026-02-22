"""
    Author: Jason E. Blackert

    decorators.py: "What is my purpose?"
    developer: "Provide a decorator for other modules to use, not quite a helper."
    decorators.py: "Oh my god."
"""

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

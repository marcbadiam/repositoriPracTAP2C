# Comunicació asíncrona basada en missatges JSON
import json
import logging
from datetime import datetime
from typing import Any, Dict

class MessageProtocol:
    @staticmethod
    def create_message(msg_type: str, source: str, target: str, payload: dict, status: str = "SUCCESS", context: dict = None) -> dict:
        return {
            "type": msg_type,
            "source": source,
            "target": target,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload,
            "status": status,
            "context": context or {}
        }

    @staticmethod
    def validate_message(msg: dict) -> bool:
        # Validació mínima segons specs.md
        required = ["type", "source", "target", "timestamp", "payload", "status", "context"]
        return all(k in msg for k in required)

    @staticmethod
    def to_json(msg: dict) -> str:
        return json.dumps(msg)

    @staticmethod
    def from_json(msg_str: str) -> dict:
        return json.loads(msg_str)

class MessageBus:
    def __init__(self):
        self.subscribers = {}
        self.log = logging.getLogger("MessageBus")

    def subscribe(self, agent_name: str, callback):
        self.subscribers[agent_name] = callback
        self.log.debug(f"{agent_name} subscrit al MessageBus")

    def publish(self, msg: dict):
        target = msg.get("target")
        if target in self.subscribers:
            self.log.debug(f"Entregant missatge a {target}: {msg['type']}")
            self.subscribers[target](msg)
        else:
            self.log.warning(f"Cap subscriptor per a: {target}")

# Comunicació asíncrona basada en missatges JSON
import json
import logging
from datetime import datetime


class MessageProtocol:
    """
    Protocol per a la creació i validació de missatges JSON
    """

    @staticmethod
    def create_message(
        msg_type: str,
        source: str,
        target: str,
        payload: dict,
        status: str = "SUCCESS",
        context: dict = None,
    ) -> dict:
        """
        Crea un missatge estructurat seguint el protocol definit.

        Args:
            msg_type (str): Tipus de missatge.
            source (str): Origen del missatge.
            target (str): Destí del missatge.
            payload (dict): Dades del missatge.
            status (str, opcional): Estat del missatge. Per defecte "SUCCESS".
            context (dict, opcional): Context addicional. Per defecte None.

        Returns:
            dict: Diccionari amb l'estructura del missatge.
        """
        return {
            "type": msg_type,
            "source": source,
            "target": target,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload,
            "status": status,
            "context": context or {},
        }

    @staticmethod
    def validate_message(msg: dict) -> bool:
        """
        Valida que un missatge contingui tots els camps requerits.

        Args:
            msg (dict): Missatge a validar.

        Returns:
            bool: True si el missatge és vàlid, False sino.
        """
        required = [
            "type",
            "source",
            "target",
            "timestamp",
            "payload",
            "status",
            "context",
        ]
        return all(k in msg for k in required)

    @staticmethod
    def to_json(msg: dict) -> str:
        """
        Converteix un diccionari de missatge a una cadena JSON.

        Args:
            msg (dict): Missatge a convertir.

        Returns:
            str: Cadena JSON representant el missatge.
        """
        return json.dumps(msg)

    @staticmethod
    def from_json(msg_str: str) -> dict:
        """
        Converteix una cadena JSON a un diccionari de missatge.

        Args:
            msg_str (str): Cadena JSON a convertir.

        Returns:
            dict: Diccionari del missatge.
        """
        return json.loads(msg_str)


class MessageBus:
    """
    Bus de missatges simple per a la comunicació publicador-subscriptor
    """

    def __init__(self):
        """
        Inicialitza el bus de missatges amb llista de subscriptors buida.
        """
        self.subscribers = []
        self.log = logging.getLogger("MessageBus")

    def subscribe(self, callback):
        """
        Afegeix un callback a la llista de subscriptors.

        Args:
            callback (callable): Funció a cridar quan es rep un missatge.
        """
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            self.log.debug("Subscriptor afegit al MessageBus")

    def publish(self, msg: dict):
        """
        Envia un missatge a tots els subscriptors registrats.

        Args:
            msg (dict): Missatge a enviar.
        """
        # Broadcast a tots els subscriptors
        msg_type = msg.get("type", "unknown")
        target = msg.get("target", "all")
        self.log.debug(f"Broadcasting missatge {msg_type} (target: {target})")

        for callback in self.subscribers:
            try:
                callback(msg)
            except Exception as e:
                self.log.error(f"Error enviant missatge a subscriptor: {e}")

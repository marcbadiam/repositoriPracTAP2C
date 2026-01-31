# Comunicació asíncrona basada en missatges JSON
import json
import logging
from datetime import datetime, timezone


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
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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




class MessageBus:
    """
    Bus de missatges asíncron (Producer-Consumer) amb cues i validació
    Implementa:
    - processament asíncron non-blocking (amb Queue)
    - validació de missatges
    - traçabilitat completa
    """

    def __init__(self):
        """
        Inicialitza el bus amb una cua i un thread de treball en background.
        """
        import queue
        import threading
        
        self.subscribers = []
        self.log = logging.getLogger("MessageBus")
        
        # Cua thread-safe per a comunicació asíncrona
        self.queue = queue.Queue()
        self.running = True
        
        # Thread worker que processa els missatges
        self._worker_thread = threading.Thread(
            target=self._process_queue, 
            name="MessageBus-Worker", 
            daemon=True
        )
        self._worker_thread.start()
        self.log.info("Bus de missatges asíncron iniciat.")

    def subscribe(self, callback):
        """
        Afegeix un callback a la llista de subscriptors.

        Args:
            callback (callable): Funció a cridar quan es rep un missatge.
        """
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            self.log.debug("Subscriptor registrat al MessageBus")

    def publish(self, msg: dict):
        """
        Envia un missatge a la cua de processament (no bloquejant).
        
        Realitza validació i garanteix traçabilitat abans d'encuar.
        L'emissor recupera el control immediatament després d'encuar (asíncron).

        Args:
            msg (dict): Missatge a enviar.
        """
        import uuid
        
        # validacio de format    
        if not MessageProtocol.validate_message(msg):
            self.log.error(f"MessageBus REBUTJAT: Format invàlid: {msg}")
            return

        # si no en te li donem id unic
        if "id" not in msg:
            msg["id"] = str(uuid.uuid4())

        # encuar asíncron
        self.queue.put(msg)
        
        msg_type = msg.get("type", "unknown")
        # self.log.debug(

    def _process_queue(self):
        """
        bucle infinit del worker que processa missatges de la cua
        """
        while self.running:
            try:
                # bloqueja fins que hi ha un missatge
                msg = self.queue.get(timeout=1.0)
                
                # log de processament
                # self.log.debug(
                
                # broadcast a tots els subscriptors
                for callback in self.subscribers:
                    self._deliver_with_retry(callback, msg)
                
                self.queue.task_done()
                
            except Exception:
                # timeout de la cua (normal) o error inesperat
                continue

    def _deliver_with_retry(self, callback, msg):
        """
        Entrega un missatge a un subscriptor
        Args:
            callback: Funció del subscriptor
            msg: Missatge a entregar
        """
        try:
            callback(msg)
        except Exception as e:
            self.log.error(
                f"ERROR: Error entregant missatge {msg.get('id')} a {callback}: {e}"
            )

    def stop(self):
        """Atura el bus."""
        self.running = False
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)
        self.log.info("MessageBus aturat.")

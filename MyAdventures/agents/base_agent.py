from enum import Enum, auto
import logging
from abc import ABC, abstractmethod
import json
from datetime import datetime, timezone
import threading


class AgentState(Enum):
    IDLE = auto()  # Estat d'espera inicial o inactiu
    RUNNING = auto()  # Agent executant-se activament
    PAUSED = auto()  # Agent pausat temporalment
    WAITING = auto()  # Esperant una condició externa
    STOPPED = auto()  # Aturat permanentment
    ERROR = auto()  # S'ha produït un error


class BaseAgent(ABC):
    """Classe base abstracta per a tots els agents."""

    def __init__(self, name, system_flags=None):
        # Inicialitza l'agent amb un nom i configura el logger
        self.name = name
        self.state = AgentState.IDLE
        self.log = logging.getLogger(self.name)  # Logger específic per a l'agent
        self.checkpoint = {}  # Per guardar l'estat en pausa o repòs
        self.system_flags = system_flags if system_flags is not None else {}
        self.log.info(f"{self.name} inicialitzat en estat {self.state.name}")
        self._stop_event = threading.Event()
        self._thread = None
        self._tick_interval = 0.2
        self.wait_quietly = False

    def set_state(self, new_state, reason=""):
        """Canvia l'estat de l'agent amb registre de transició."""
        old_state = self.state
        self.state = new_state  # Actualització de l'estat
        timestamp = datetime.now(timezone.utc).isoformat()

        log_entry = {
            "agent": self.name,
            "timestamp": timestamp,
            "from_state": old_state.name,  # Registre de l'estat anterior
            "to_state": new_state.name,  # Registre del nou estat
            "reason": reason,  # Motiu del canvi
        }
        self.log.debug(f"Transició d'estat: {json.dumps(log_entry)}")
        self.log.info(
            f"[STATE TRANSITION] {old_state.name} -> {new_state.name} ({reason})"
        )
        self.log.debug(f"Transició estructurada: {json.dumps(log_entry)}")

        if new_state in (AgentState.STOPPED, AgentState.ERROR):
            self._release_locks()  # Alliberar recursos si l'agent s'atura
            self._stop_event.set()

    def _release_locks(self):
        pass

    def save_checkpoint(self):
        # Guarda l'estat actual per poder recuperar-lo més tard
        self.checkpoint = {
            "state": self.state.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.log.debug(f"Checkpoint guardat: {self.checkpoint}")

    def restore_checkpoint(self):
        """Restaura l'estat guardat al checkpoint anterior."""
        if self.checkpoint:
            self.log.info(f"Restaurant des del punt de control: {self.checkpoint}")
        else:
            self.log.warning("No checkpoint per restaurar")

    def handle_command(self, command: str, args: dict):
        """Gestiona les comandes de control (pausa, reprendre, aturar, actualitzar)."""
        if hasattr(self, command):
            method_to_call = getattr(self, command)
            method_to_call()
            self.log.info(f"Comanda '{command}' executada a {self.name}")
        else:
            self.log.warning(f"Comanda desconeguda '{command}' per a {self.name}")

    @abstractmethod
    def perceive(self):
        """percepció de l'entorn"""
        pass

    @abstractmethod
    def decide(self):
        """presa de decisions"""
        pass

    @abstractmethod
    def act(self):
        """execució d'accions"""
        pass

    def run_once(self):
        """Executa un sol cicle percepció-decisió-acció si l'estat és RUNNING."""
        if self.state != AgentState.RUNNING:
            return

        self.perceive()
        self.decide()
        self.act()

    # Thread-based execution
    def start_loop(self, tick_interval: float = 0.2):
        """Inicia un fil que executa `tick` periòdicament. (0,2s)"""
        self._tick_interval = tick_interval
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name=f"{self.name}-thread", daemon=True
        )
        self._thread.start()
        self.log.debug(f"Fil d'execució iniciat per {self.name}")

    def _loop(self):
        """Bucle del fil: executa cicles fins que es demana parada."""
        while not self._stop_event.is_set():
            try:
                if self.state in (AgentState.RUNNING, AgentState.WAITING):
                    self.run_once()
            finally:
                # Espera cooperativa per reduir ús de CPU i permetre parada ràpida
                self._stop_event.wait(self._tick_interval)

    def pause(self):
        """Pausa l'agent."""
        if self.state == AgentState.RUNNING:
            self.set_state(AgentState.PAUSED, "Pausat per comanda")

    def resume(self):
        """Repren l'agent."""
        if self.state == AgentState.PAUSED:
            self.set_state(AgentState.RUNNING, "Repres per comanda")

    def stop_loop(self):
        """Atura el fil de l'agent i espera la seva finalització."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

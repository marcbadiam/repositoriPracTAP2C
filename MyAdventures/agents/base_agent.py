from enum import Enum, auto
import logging
from abc import ABC, abstractmethod
import json
from datetime import datetime, timezone


class AgentState(Enum):
    IDLE = auto()     # Estat d'espera inicial o inactiu
    RUNNING = auto()  # Agent executant-se activament
    PAUSED = auto()   # Agent pausat temporalment
    WAITING = auto()  # Esperant una condició externa
    STOPPED = auto()  # Aturat permanentment
    ERROR = auto()    # S'ha produït un error 


class BaseAgent(ABC):
    """Classe base abstracta per a tots els agents."""
    
    def __init__(self, name):
        # Inicialitza l'agent amb un nom i configura el logger
        self.name = name
        self.state = AgentState.IDLE
        self.log = logging.getLogger(self.name) # Logger específic per a l'agent
        self.checkpoint = {}  # Per guardar l'estat en pausa o repòs
        self.log.info(f"{self.name} inicialitzat en estat {self.state.name}")

    def set_state(self, new_state, reason=""):  
        """Canvia l'estat de l'agent amb registre de transició."""
        old_state = self.state
        self.state = new_state # Actualització de l'estat
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            "agent": self.name,
            "timestamp": timestamp,
            "from_state": old_state.name, # Registre de l'estat anterior
            "to_state": new_state.name,   # Registre del nou estat
            "reason": reason              # Motiu del canvi
        }
        self.log.debug(f"Transició d'estat: {json.dumps(log_entry)}")
        self.log.info(f"[STATE TRANSITION] {old_state.name} -> {new_state.name} ({reason})")
        self.log.debug(f"Transició estructurada: {json.dumps(log_entry)}")
        
        if new_state in (AgentState.STOPPED, AgentState.ERROR):
            self._release_locks() # Alliberar recursos si l'agent s'atura

    def _release_locks(self):
        pass

    def save_checkpoint(self):
        # Guarda l'estat actual per poder recuperar-lo més tard
        self.checkpoint = {
            "state": self.state.name,
            "timestamp": datetime.now(timezone.utc).isoformat()
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
        if command == "pause":
            if self.state == AgentState.RUNNING:
                self.save_checkpoint() # Guardar estat abans de pausar
                self.set_state(AgentState.PAUSED, reason="User command")
                self.log.info(f"{self.name} paused")
            else:
                self.log.warning(f"No es pot pausar des de l'estat {self.state.name}")
        
        elif command == "resume":
            if self.state == AgentState.PAUSED:
                self.restore_checkpoint() # Recuperar estat anterior
                self.set_state(AgentState.RUNNING, reason="User command")
                self.log.info(f"{self.name} resumed")
            else:
                self.log.warning(f"No es pot reprendre des de l'estat {self.state.name}")
        
        elif command == "stop":
            self.save_checkpoint()
            self.set_state(AgentState.STOPPED, reason="User command")
            self.log.info(f"{self.name} stopped")
        
        elif command == "update":
            self.log.info(f"{self.name} ha rebut comanda d'actualització amb arguments: {args}")

    @abstractmethod
    def perceive(self):
        pass

    @abstractmethod
    def decide(self):
        pass

    @abstractmethod
    def act(self):
        pass

    def tick(self):
        """Executa un cicle de percepció, decisió i acció."""
        if self.state == AgentState.STOPPED:
            return # No fer res si està aturat
        
        if self.state == AgentState.PAUSED:
            self.log.debug(f"{self.name} està pausat, saltant tick")
            return # Saltar cicle si està pausat
            
        try:
            if self.state != AgentState.RUNNING:
                self.set_state(AgentState.RUNNING, reason="Iniciant cicle tick")
            self.perceive() # 1. Recollir dades
            self.decide()   # 2. Prendre decisions
            self.act()      # 3. Executar accions
        except Exception as e:
            self.set_state(AgentState.ERROR, reason=f"Excepció: {e}")
            self.log.error(f"Error en el tick: {e}", exc_info=True)

    def run(self):
        # Bucle principal d'execució contínua
        try:
            self.set_state(AgentState.RUNNING, reason="Iniciant bucle principal")
            while self.state == AgentState.RUNNING:
                self.perceive()
                self.decide()
                self.act()
        except Exception as e:
            self.set_state(AgentState.ERROR, reason=f"Excepció: {e}")
            self.log.error(f"Error en l'execució: {e}", exc_info=True)

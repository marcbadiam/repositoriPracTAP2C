from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.visuals import mark_bot
import logging

logger = logging.getLogger(__name__)

class ExplorerBot(BaseAgent):
    """Agent que descobreix zones planes del terreny prop del jugador."""
    def __init__(self, name, message_bus, mc, mc_lock=None, system_flags=None):
        super().__init__(name, system_flags)
        self.message_bus = message_bus
        self.mc = mc  # Instància de Minecraft
        self.mc_lock = mc_lock  # Lock per sincronitzar accés a mc
        self.current_task = None
        self.terrain_map = {}
        self.target_zone = None
        self.map_sent = False  # Evita enviar el mapa múltiples cops per workflow
        
        # Subscripció als missatges importants
        self.message_bus.subscribe(self.on_message)

    def on_message(self, message):
        """Gestiona missatges rebuts pel bus."""
        msg_type = message.get("type")
        if msg_type == "workflow.reset":
            self.reset()
        # Altres missatges específics per a ExplorerBot si cal

    def perceive(self):
        """Analitza el terreny prop del jugador real si està en mode RUNNING."""
        if self.state != AgentState.RUNNING:
            return

        try:
            if self.mc_lock:
                self.mc_lock.acquire()
            try:
                p = self.mc.player.getTilePos()
                base_x, base_z = int(p.x) + 2, int(p.z) + 2
                y = self.mc.getHeight(base_x, base_z)
                # es simula que es troba la zona plana a x+2 z+2
                self.terrain_map = {"flat_zones": [(base_x, base_z, y)]}
                self.log.debug(f"Terreny percebut: {self.terrain_map}")
            finally:
                if self.mc_lock:
                    self.mc_lock.release()
        except Exception as e:
            self.set_state(AgentState.ERROR, reason=f"Error al percebre: {e}")
            self.log.error(f"Error en perceive: {e}", exc_info=True)

    def decide(self):
        """Selecciona la zona objectiu si està en mode RUNNING."""
        if self.state != AgentState.RUNNING or self.map_sent:
            return
            
        if self.terrain_map.get("flat_zones"):
            # Lògica de decisió: agafem la primera zona trobada
            self.target_zone = self.terrain_map["flat_zones"][0]
            self.log.debug(f"Zona objectiu seleccionada: {self.target_zone}")


    def act(self):
        """Marca la zona i publica el mapa."""
        if self.state != AgentState.RUNNING or not self.target_zone or self.map_sent:
            return

        x, z, y = self.target_zone
        
        # Col·loca un marcador visible (blau) a la zona objectiu amb lock
        if self.mc_lock:
            self.mc_lock.acquire()
        try:
            mark_bot(self.mc, x, y, z, wool_color=11, label=self.name)
        finally:
            if self.mc_lock:
                self.mc_lock.release()
        
        # Crea i publica el missatge amb les coordenades del mapa
        msg = MessageProtocol.create_message(
            msg_type="map.v1",
            source=self.name,
            target="BuilderBot",
            payload={"zone": {"x": x, "y": y, "z": z}},
            context={"state": self.state.name}
        )
        self.message_bus.publish(msg)
        self.log.info(f"Mapa publicat per a BuilderBot: {x}, {y}, {z}")
        self.map_sent = True
        # Un cop publicat, quedem en WAITING
        self.set_state(AgentState.WAITING, reason="Mapa publicat, esperant instruccions")

    def start(self):
        """Inicia l'exploració."""
        self.map_sent = False
        self.set_state(AgentState.RUNNING, reason="Iniciant exploració")
        self.log.info("ExplorerBot iniciat")

    def stop(self):
        """Atura l'exploració."""
        self.set_state(AgentState.STOPPED, reason="Aturat per comanda")
        self.log.info("ExplorerBot aturat")

    def reset(self):
        """Reseteja l'estat per a un nou workflow."""
        self.map_sent = False
        self.target_zone = None
        self.set_state(AgentState.IDLE, reason="Resetejat per a nou workflow")
        self.log.info("ExplorerBot resetejat")


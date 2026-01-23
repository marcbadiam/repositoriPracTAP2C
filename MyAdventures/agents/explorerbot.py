from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.visuals import mark_bot
import logging

logger = logging.getLogger(__name__)

class ExplorerBot(BaseAgent):
    """Agent que descobreix zones planes del terreny prop del jugador."""
    def __init__(self, name, message_bus, mc):
        super().__init__(name)
        self.message_bus = message_bus
        self.mc = mc  # Instància de Minecraft
        self.current_task = None
        self.terrain_map = {}
        self.target_zone = None
        self.map_sent = False  # Evita enviar el mapa múltiples cops per workflow

    def perceive(self):
        """Analitza el terreny prop del jugador real."""
        if self.state == AgentState.STOPPED:
            return
        # Si ja hem enviat el mapa i estem esperant, no cal recalcular
        if self.map_sent and self.state == AgentState.WAITING:
            return
            
        p = self.mc.player.getTilePos()
        base_x, base_z = int(p.x) + 2, int(p.z) + 2
        y = self.mc.getHeight(base_x, base_z)
        self.terrain_map = {"flat_zones": [(base_x, base_z, y)]}
        
        self.log.debug(f"Terreny percebut: {self.terrain_map}")

    def decide(self):
        """Selecciona la zona plana objectiu."""
        if self.state == AgentState.STOPPED:
            return
        if self.map_sent and self.state == AgentState.WAITING:
            return
            
        if self.terrain_map.get("flat_zones"):
            self.target_zone = self.terrain_map["flat_zones"][0]
            self.log.debug(f"Zona objectiu seleccionada: {self.target_zone}")

    def act(self):
        """Marca la zona i publica el mapa."""
        if self.state == AgentState.STOPPED:
            return
            
        if not self.target_zone:
            return

        # Si ja hem publicat el mapa en aquest workflow, no tornem a enviar-lo
        if self.map_sent:
            self.set_state(AgentState.WAITING, reason="Mapa ja publicat")
            return
            
        x, z, y = self.target_zone
        
        # Col·loca un marcador visible (blau) a la zona objectiu
        mark_bot(self.mc, x, y, z, wool_color=11, label=self.name)
        
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
        # Un cop publicat, quedem en WAITING sense retickar fins nou workflow
        self.set_state(AgentState.WAITING, reason="Mapa publicat, esperant instruccions")

    def tick(self):
        """Evita loops contínuos després d'enviar el mapa."""
        # Si ja hem enviat el mapa i estem en WAITING, no fem res fins nou workflow
        if self.map_sent and self.state == AgentState.WAITING:
            return
        super().tick()

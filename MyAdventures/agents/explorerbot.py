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

        # Rangs de exploració
        self.exploration_ranges = [40, 20, 80]
        self.current_range_index = 0

        # Subscripció als missatges importants
        self.message_bus.subscribe(self.on_message)

    def cycle_range(self):
        """Cicle al següent rang d exploració."""
        self.current_range_index = (self.current_range_index + 1) % len(
            self.exploration_ranges
        )
        new_range = self.exploration_ranges[self.current_range_index]
        self.log.info(f"Rang d'exploració canviat a: {new_range}")
        return new_range

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
                base_x, base_z = int(p.x), int(p.z)

                # Cerca de zona plana en 4 direccions: (+x, +z, -x, -z)
                directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
                found_zone = None

                from utils.visuals import mark_bot

                current_range = self.exploration_ranges[self.current_range_index]

                for dx, dz in directions:
                    consecutive_count = 0
                    last_y = None

                    # Recorre 'current_range' blocs en la direcció actual
                    for i in range(1, current_range + 1):
                        check_x = base_x + (dx * i)
                        check_z = base_z + (dz * i)
                        y = self.mc.getHeight(check_x, check_z)

                        # Marquem cada bloc inspeccionat
                        mark_bot(self.mc, check_x, y, check_z, wool_color=11)

                        if last_y is not None and y == last_y:
                            consecutive_count += 1
                        else:
                            consecutive_count = 1
                            last_y = y

                        # Si trobem 7 blocs seguits al mateix nivell
                        if consecutive_count >= 7:
                            # Calculem el centre de la zona (retrocedim 3 posicions). 7 blocs -> el 4t és el centre (i-3)
                            center_offset = i - 3
                            center_x = base_x + (dx * center_offset)
                            center_z = base_z + (dz * center_offset)

                            # Ara comprovem els eixos perpendiculars
                            # Si ens movem en X (dx!=0), comprovem Z. Si ens movem en Z (dz!=0), comprovem X.
                            perp_dx, perp_dz = (0, 1) if abs(dx) > 0 else (1, 0)

                            is_valid_cross = True
                            for k in range(-3, 4):
                                if k == 0:
                                    continue  # El centre ja sabem que esta a l'altura

                                px = center_x + (k * perp_dx)
                                pz = center_z + (k * perp_dz)
                                py = self.mc.getHeight(px, pz)

                                # Marcatge visual de la comprovació extra
                                mark_bot(self.mc, px, py, pz, wool_color=11)

                                if py != y:
                                    is_valid_cross = False
                                    break

                            if is_valid_cross:
                                found_zone = (center_x, center_z, y)
                                # Si finalment la zona es valida la marquem amb un bloc extra
                                mark_bot(
                                    self.mc, center_x, y + 1, center_z, wool_color=11
                                )
                                break
                            else:
                                # Si falla la comprovació lateral, resetegem el comptador
                                consecutive_count = 0

                    if found_zone:
                        break

                if found_zone:
                    self.terrain_map = {"flat_zones": [found_zone]}
                    self.log.debug(f"Terreny percebut: {self.terrain_map}")
                else:
                    msg = "No s'ha trobat cap zona plana en les direccions explorades."
                    self.log.info(msg)
                    self.mc.postToChat(f"[{self.name}] {msg}")
                    # Aturem el workflow ja que no s'ha trobat zona
                    self.set_state(AgentState.STOPPED, reason="Zona plana no trobada")

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
            context={"state": self.state.name},
        )
        self.message_bus.publish(msg)
        self.log.info(f"Mapa publicat per a BuilderBot: {x}, {y}, {z}")
        self.map_sent = True
        # Un cop publicat, quedem en WAITING
        self.set_state(
            AgentState.WAITING, reason="Mapa publicat, esperant instruccions"
        )

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

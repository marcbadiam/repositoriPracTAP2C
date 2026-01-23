from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.visuals import mark_bot
from mcpi import block as mcblock
import time
import logging

logger = logging.getLogger(__name__)

class BuilderBot(BaseAgent):
    """Agent que construeix plataformes 4x4 amb terra i pedra."""
    def __init__(self, name, message_bus, mc):
        super().__init__(name)
        self.message_bus = message_bus
        self.mc = mc
        self.materials_needed = {"dirt": 8, "stone": 8}  # BOM per 4x4 (2 de terra, 2 de pedra)
        self.materials_received = {"dirt": 0}  # Materials rebuts fins ara
        self.target_zone = None                # Zona objectiu on construir
        self.completed = False                 # Estat de finalització de la tasca
        self.build_blocks = []                 # Llista de blocs a construir
        self.build_index = 0                   # Índex del bloc actual
        self.last_block_time = 0               # Temps de l'últim bloc col·locat
        self.ready = False                     # Bandera de readiness
        self.materials_received = {"dirt": 0, "stone": 0}  # Multi-material inventory
        self.last_request_time = 0             # Per evitar spam de demandes

    def perceive(self):
        """Percep l'inventari disponible via inventory.v1"""
        self.log.debug(f"Materials disponibles: {self.materials_received}")

    def decide(self):
        """Comprova si s'han rebut tots els materials necesaris."""
        have_materials = all(self.materials_received.get(k, 0) >= v for k, v in self.materials_needed.items())
        # Si ja estem construint (build_blocks no buit), mantenim ready per continuar
        if self.build_blocks:
            self.ready = True
        else:
            self.ready = have_materials and self.target_zone is not None

    def act(self):
        """Executa la construcció o espera materials."""
        if self.completed:
            self.log.info("Construcció ja completada")
            self.set_state(AgentState.STOPPED, reason="Construcció completada")
            return

        building_in_progress = bool(self.build_blocks)

        # Si no estem llestos i tampoc hem començat a construir, demanem materials i sortim
        if not self.ready and not building_in_progress:
            current_time = time.time()
            if current_time - self.last_request_time > 2.0:
                msg = MessageProtocol.create_message(
                    msg_type="materials.requirements.v1",
                    source=self.name,
                    target="MinerBot",
                    payload={"needs": self.materials_needed, "zone": self.target_zone},
                    context={"state": self.state.name}
                )
                self.message_bus.publish(msg)
                self.log.info(f"Demanda de materials: {self.materials_needed}")
                self.last_request_time = current_time
            self.set_state(AgentState.WAITING, reason="Esperant materials")
            return

        # Temps disponible: construir
        x, y, z = self.target_zone["x"], self.target_zone["y"], self.target_zone["z"]

        # Primera vegada: preparar llista de blocs 4x4 (2 terra, 2 pedra)
        if not self.build_blocks:
            mark_bot(self.mc, x, y + 2, z, wool_color=5, label=self.name)
            platform_y = y + 1
            
            # Plataforma 4x4 amb patró:
            # 2 columnes de terra (dx=0,1) + 2 columnes de pedra (dx=2,3)
            for dx in range(4):
                for dz in range(4):
                    material_type = "dirt" if dx < 2 else "stone"
                    self.build_blocks.append((x + dx, platform_y, z + dz, material_type))
            
            self.log.info(f"Pla de construcció 4x4 creat: {len(self.build_blocks)} blocs")
            self.build_index = 0
            self.last_block_time = time.time()
            self.set_state(AgentState.RUNNING, reason="Iniciant construcció 4x4")
            return

        # Construir blocs amb interval
        current_time = time.time()
        if current_time - self.last_block_time < 1.0:
            return

        if self.build_index < len(self.build_blocks):
            bx, by, bz, material_type = self.build_blocks[self.build_index]

            # Verificar disponibilitat
            if self.materials_received.get(material_type, 0) <= 0:
                self.log.warning(f"Manca de {material_type}")
                self.set_state(AgentState.WAITING, reason=f"Manca de {material_type}")
                return

            # Col·locar bloc
            if material_type == "dirt":
                block_id = getattr(mcblock, "DIRT", None)
            else:
                block_id = getattr(mcblock, "STONE", None)

            material_id = block_id.id if block_id else (3 if material_type == "dirt" else 1)
            self.mc.setBlock(bx, by, bz, material_id)
            self.materials_received[material_type] -= 1

            self.log.debug(f"Bloc {material_type} col·locat a ({bx},{by},{bz})")
            self.build_index += 1
            self.last_block_time = current_time
        else:
            # Construcció finalitzada
            self.log.info(f"Plataforma 4x4 completada a ({x},{y},{z})")
            
            # Notificar al MinerBot
            complete_msg = MessageProtocol.create_message(
                msg_type="build.complete.v1",
                source=self.name,
                target="MinerBot",
                payload={"zone": {"x": x, "y": y, "z": z}},
                context={"state": self.state.name}
            )
            self.message_bus.publish(complete_msg)

            self.completed = True
            self.build_blocks = []
            self.build_index = 0
            self.set_state(AgentState.STOPPED, reason="Construcció completada")
    def on_message(self, msg):
        """Gestiona els missatges rebuts del bus de comunicació."""
        if msg["type"] == "map.v1":
            zone = msg.get("payload", {}).get("zone")
            if zone and all(k in zone for k in ("x", "y", "z")):
                self.target_zone = zone
                # Reiniciar estat per a nova tasca de construcció
                self.completed = False
                self.build_blocks = []
                self.build_index = 0
                # Reiniciar inventari rebut
                self.materials_received = {k: 0 for k in self.materials_needed}
                self.ready = False
                self.set_state(AgentState.IDLE, reason="Nova zona rebuda")
                self.mc.postToChat("[BuilderBot] Zona rebuda. Usa '-builder build' per iniciar construcció.")
                self.log.info(f"Zona rebuda: {zone}")

        elif msg["type"] == "inventory.v1":
            """Rebre actualitzacions d'inventari del MinerBot."""
            payload = msg.get("payload", {})
            inventory = payload.get("inventory", {})
            self.materials_received = inventory.copy()
            self.log.debug(f"Inventari actualitzat: {self.materials_received}")
        elif msg["type"] == "materials.location.v1":
            payload = msg.get("payload", {})
            chest = payload.get("chest", {})
            contents = payload.get("contents", {})
            if all(k in chest for k in ("x", "y", "z")):
                self.chest = chest
                self.mc.postToChat(f"[BuilderBot] Materials disponibles. Usa '-builder build' per construir.")
            # Actualitzar comptador de materials rebuts
            self.materials_received["dirt"] += int(contents.get("dirt", 0))
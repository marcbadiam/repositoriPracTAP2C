from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.visuals import mark_bot
from mcpi import block as mcblock
import time
import logging

logger = logging.getLogger(__name__)

class BuilderBot(BaseAgent):
    """Agent que construeix plataformes 4x4 amb terra i pedra."""
    def __init__(self, name, message_bus, mc, mc_lock=None):
        super().__init__(name)
        self.message_bus = message_bus
        self.mc = mc
        self.mc_lock = mc_lock
        self.bom = {"dirt": 8, "stone": 8}
        self.inventory = {"dirt": 0, "stone": 0}
        self.target_zone = None
        self.build_plan = []
        self.build_index = 0
        self.last_request_time = 0

        self.message_bus.subscribe(self.on_message)
        self.set_state(AgentState.IDLE)

    def on_message(self, msg):
        """Gestiona missatges rebuts."""
        # Filtrar missatges propis
        if msg.get("source") == self.name:
            return

        msg_type = msg.get("type")
        target = msg.get("target")
        
        # Acceptar missatges específics
        if target and target not in ["all", self.name] and msg_type != "workflow.reset":
            return

        if msg_type == "map.v1":
            self._handle_map_v1(msg)
        elif msg_type == "inventory.v1":
            self._handle_inventory_v1(msg)
        elif msg_type == "workflow.reset":
            self.reset()

    def _handle_map_v1(self, msg):
        self.target_zone = msg.get("payload", {}).get("zone")
        self.log.info(f"Nova zona de construcció rebuda: {self.target_zone}")
        self.set_state(AgentState.WAITING, "Zona rebuda, esperant materials")
        self._request_materials()

    def _handle_inventory_v1(self, msg):
        self.inventory = msg.get("payload", {}).get("inventory", {})
        self.log.info(f"Inventari actualitzat: {self.inventory}")
        self._check_readiness()

    def _request_materials(self):
        """Envia una petició de materials al MinerBot."""
        current_time = time.time()
        if current_time - self.last_request_time > 5.0:  # Evita spam
            msg = MessageProtocol.create_message(
                msg_type="materials.requirements.v1",
                source=self.name,
                target="MinerBot",
                payload={"needs": self.bom}
            )
            self.message_bus.publish(msg)
            self.log.info(f"Petició de materials enviada: {self.bom}")
            self.last_request_time = current_time

    def _check_readiness(self):
        """Comprova si té tot el necessari per començar a construir."""
        if self.state == AgentState.WAITING and self.target_zone:
            if all(self.inventory.get(k, 0) >= v for k, v in self.bom.items()):
                self.log.info("Materials suficients. Iniciant construcció.")
                self.set_state(AgentState.RUNNING, "Materials disponibles")
            else:
                self.log.info("Encara falten materials. Esperant...")
                self._request_materials()

    def perceive(self):
        """Percepció"""
        pass

    def decide(self):
        """Decisió"""
        pass

    def act(self):
        """Executa la construcció si l'estat és RUNNING."""
        if self.state != AgentState.RUNNING:
            return

        if not self.build_plan:
            self._create_build_plan()

        if self.build_index < len(self.build_plan):
            self._build_next_block()
        else:
            self._finalize_build()

    def _create_build_plan(self):
        """Crea el pla de construcció per a una plataforma 4x4."""
        if not self.target_zone:
            return
        x, y, z = self.target_zone['x'], self.target_zone['y'], self.target_zone['z']
        
        if self.mc_lock: self.mc_lock.acquire()
        try:
            mark_bot(self.mc, x, y + 2, z, wool_color=5, label=self.name)
        finally:
            if self.mc_lock: self.mc_lock.release()

        platform_y = y + 1
        for dx in range(4):
            for dz in range(4):
                material = "dirt" if dx < 2 else "stone"
                self.build_plan.append((x + dx, platform_y, z + dz, material))
        
        self.log.info(f"Pla de construcció creat amb {len(self.build_plan)} blocs.")
        self.build_index = 0

    def _build_next_block(self):
        """Construeix el següent bloc del pla."""
        bx, by, bz, material = self.build_plan[self.build_index]
        
        if self.inventory.get(material, 0) > 0:
            if self.mc_lock: self.mc_lock.acquire()
            try:
                block_id = mcblock.DIRT.id if material == "dirt" else mcblock.STONE.id
                self.mc.setBlock(bx, by, bz, block_id)
            finally:
                if self.mc_lock: self.mc_lock.release()

            self.inventory[material] -= 1
            self.log.debug(f"Bloc de {material} col·locat a ({bx},{by},{bz}). Restants: {self.inventory[material]}")
            
            # Publicar progrés
            progress_msg = MessageProtocol.create_message(
                "build.v1", self.name, "Monitor", 
                {"progress": (self.build_index + 1) / len(self.build_plan) * 100}
            )
            self.message_bus.publish(progress_msg)
            
            self.build_index += 1
        else:
            self.log.warning(f"Material insuficient '{material}'. Pausant construcció.")
            self.set_state(AgentState.WAITING, f"Falta {material}")
            self._request_materials()

    def _finalize_build(self):
        """Finalitza el procés de construcció."""
        self.log.info(f"Construcció completada a la zona {self.target_zone}")
        
        # Notificar finalització
        complete_msg = MessageProtocol.create_message("build.complete.v1", self.name, "MinerBot", {})
        self.message_bus.publish(complete_msg)
        
        self.set_state(AgentState.WAITING, "Construcció completada, esperant nova tasca")
        # No resetejem l'estat intern aquí per si es vol inspeccionar

    def reset(self):
        """Reseteja l'estat del BuilderBot per a un nou workflow."""
        self.log.info("Resetejant BuilderBot...")
        self.inventory = {k: 0 for k in self.bom}
        self.target_zone = None
        self.build_plan = []
        self.build_index = 0
        self.set_state(AgentState.IDLE, "Resetejat per a nou workflow")

    def start(self):
        """Inicia el bot (en aquest cas, simplement el posa a IDLE esperant un mapa)."""
        self.reset()
        self.log.info("BuilderBot iniciat i esperant zona de construcció.")

    def stop(self):
        """Atura el bot."""
        self.set_state(AgentState.STOPPED, "Aturat per comanda")
        self.log.info("BuilderBot aturat.")
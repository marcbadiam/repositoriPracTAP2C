from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.visuals import mark_bot
from mcpi import block as mcblock
import time
import logging
from utils.discovery import discover_build_plans

logger = logging.getLogger(__name__)


class BuilderBot(BaseAgent):
    """Agent que construeix qualsevol dels planols generats."""

    def __init__(self, name, message_bus, mc, mc_lock=None, system_flags=None):
        super().__init__(name, system_flags)
        self.message_bus = message_bus
        self.mc = mc
        self.mc_lock = mc_lock

        # Carreguem els plans dinamicament
        self.plans = {}
        self._load_plans()

        self.current_plan_name = next(iter(self.plans)) if self.plans else None
        self.current_plan = self.plans.get(self.current_plan_name)

        self.bom = self.current_plan.bom

        self.inventory = {"dirt": 0, "stone": 0, "sandstone": 0}
        self.target_zone = None
        self.build_plan = []
        self.build_index = 0
        self.last_request_time = 0

        self.message_bus.subscribe(self.on_message)
        self.set_state(AgentState.IDLE)

    def _load_plans(self):
        """Descobreix i carrega els plans dinàmicament."""
        plan_classes = discover_build_plans()
        for name, cls in plan_classes.items():
            try:
                plan_instance = cls()
                # Utilitza el nom definit en la propietat de la classe
                self.plans[plan_instance.name] = plan_instance
                self.log.info(f"Pla carregat: {plan_instance.name}")
            except Exception as e:
                self.log.error(f"Error carregant pla {name}: {e}")

    def switch_plan(self, plan_name):
        """Canvia el pla de construcció actiu."""
        with self.state_lock:
            if plan_name not in self.plans:
                self.log.error(f"Pla desconegut: {plan_name}")
                return False

            self.current_plan_name = plan_name
            self.current_plan = self.plans[plan_name]
            self.bom = self.current_plan.bom

            for mat in self.bom:
                if mat not in self.inventory:
                    self.inventory[mat] = 0

            self.log.info(f"Pla canviat a '{plan_name}'. Nous requisits: {self.bom}")
            return True

    def cycle_plan(self):
        """Rota al següent pla disponible."""
        plan_names = list(self.plans.keys())
        try:
            current_index = plan_names.index(self.current_plan_name)
            next_index = (current_index + 1) % len(plan_names)
        except ValueError:
            next_index = 0

        next_plan_name = plan_names[next_index]
        self.switch_plan(next_plan_name)
        return next_plan_name, self.plans[next_plan_name].bom

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
        with self.state_lock:
            self.target_zone = msg.get("payload", {}).get("zone")
            self.log.info(f"Zona de construcció rebuda: {self.target_zone}")

            # Reseteja l'estat del builder per a la nova tasca
            self.build_plan = []
            self.build_index = 0

            # Comprova el flag del workflow
            if self.system_flags.get("workflow_mode", False):
                self.set_state(
                    AgentState.WAITING, "Zona rebuda, esperant materials (Workflow)"
                )
                self._request_materials()
            else:
                self.set_state(
                    AgentState.WAITING,
                    "Zona rebuda (Manual). Esperant comanda -builder build.",
                )
                self.log.info("Mode Manual: No es demanen materials automàticament.")

    def _handle_inventory_v1(self, msg):
        with self.state_lock:
            received_inventory = msg.get("payload", {}).get("inventory", {})

            for k, v in received_inventory.items():
                self.inventory[k] = v
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
                payload={"needs": self.bom},
            )
            self.message_bus.publish(msg)
            self.log.info(f"Petició de materials enviada: {self.bom}")
            self.last_request_time = current_time

    def _check_readiness(self):
        """Comprova si té tot el necessari per començar a construir."""
        if self.state == AgentState.WAITING and self.target_zone:
            if all(self.inventory.get(k, 0) >= v for k, v in self.bom.items()):
                # Nomes auto-start si esta en mode workflow
                if self.system_flags.get("workflow_mode", False):
                    self.log.info(
                        "Materials suficients. Iniciant construcció (Workflow)."
                    )
                    self.set_state(AgentState.RUNNING, "Materials disponibles")
                else:
                    self.log.info(
                        "Materials suficients. Esperant comanda -builder build (Manual)."
                    )
            else:
                # Nomes auto-retry si esta en mode workflow
                if self.system_flags.get("workflow_mode", False):
                    self.log.info("Encara falten materials. Esperant...")
                    self._request_materials()
                else:
                    self.log.info("Falten materials (Manual).")

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

        with self.state_lock:
            if not self.build_plan:
                self._create_build_plan()

            if self.build_index < len(self.build_plan):
                self._build_next_block()
            else:
                self._finalize_build()

    def _create_build_plan(self):
        """Crea el pla de construcció basat en el pla seleccionat."""
        if not self.target_zone:
            return

        x, y, z = self.target_zone["x"], self.target_zone["y"], self.target_zone["z"]

        if self.mc_lock:
            self.mc_lock.acquire()
        try:
            mark_bot(self.mc, x, y + 5, z, wool_color=5, label=self.name)
        finally:
            if self.mc_lock:
                self.mc_lock.release()

        if not self.current_plan:
            self.log.error("No hi ha cap pla seleccionat!")
            return

        self.build_plan = self.current_plan.generate(x, y, z)

        self.log.info(
            f"Pla de construcció '{self.current_plan_name}' creat amb {len(self.build_plan)} blocs."
        )
        self.build_index = 0

    def _build_next_block(self):
        """Construeix el següent bloc del pla."""
        bx, by, bz, material = self.build_plan[self.build_index]

        if self.inventory.get(material, 0) > 0:
            if self.mc_lock:
                self.mc_lock.acquire()
            try:
                block_id = mcblock.DIRT.id
                if material == "stone":
                    block_id = mcblock.STONE.id
                elif material == "sandstone":
                    block_id = mcblock.SANDSTONE.id

                self.mc.setBlock(bx, by, bz, block_id)
            finally:
                if self.mc_lock:
                    self.mc_lock.release()

            self.inventory[material] -= 1
            self.log.debug(
                f"Bloc de {material} col·locat a ({bx},{by},{bz}). Restants: {self.inventory[material]}"
            )

            # Publicar progrés
            progress_msg = MessageProtocol.create_message(
                "build.v1",
                self.name,
                "Monitor",
                {"progress": (self.build_index + 1) / len(self.build_plan) * 100},
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
        complete_msg = MessageProtocol.create_message(
            "build.complete.v1", self.name, "MinerBot", {}
        )
        self.message_bus.publish(complete_msg)

        self.set_state(
            AgentState.WAITING, "Construcció completada, esperant nova tasca"
        )
        # No resetejem l'estat intern aquí per si es vol inspeccionar

    def reset(self):
        """Reseteja l'estat del BuilderBot per a un nou workflow."""
        self.log.info("Resetejant BuilderBot...")
        
        with self.state_lock:
            if self.current_plan:
                self.bom = self.current_plan.bom
                self.inventory = {k: 0 for k in self.bom}
            else:
                self.inventory = {}
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

from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from strategies.grid_search import GridSearchStrategy
from strategies.vertical_search import VerticalSearchStrategy
from utils.visuals import mark_bot
from mcpi import block as mcblock
import logging

logger = logging.getLogger(__name__)

class MinerBot(BaseAgent):
    """Agent que mina blocs de terra i pedra, recolectant recursos."""
    def __init__(self, name, message_bus, mc, mc_lock=None):
        super().__init__(name)
        self.message_bus = message_bus
        self.mc = mc
        self.mc_lock = mc_lock
        self.strategies = [GridSearchStrategy(grid_spacing=1, grid_size=4), VerticalSearchStrategy()]
        self.inventory = {"dirt": 0, "stone": 0}
        self.requirements = None
        self.anchor_pos = None

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

        if msg_type == "materials.requirements.v1":
            self._handle_requirements(msg)
        elif msg_type == "build.complete.v1":
            self.stop()
        elif msg_type == "workflow.reset":
            self.reset()

    def _handle_requirements(self, msg):
        self.requirements = msg.get("payload", {}).get("needs")
        self.log.info(f"Requeriments de materials rebuts: {self.requirements}")
        # Inicialitzar l'inventari per a nous requeriments si no existeix, pero no esborrar stock existent
        for req in self.requirements:
            if req not in self.inventory:
                self.inventory[req] = 0
        self.start()

    def perceive(self):
        """Percepció"""
        pass

    def decide(self):
        """Decisió"""
        pass

    def act(self):
        """Executa la mineria si l'estat és RUNNING."""
        if self.state != AgentState.RUNNING:
            return

        if not self.anchor_pos:
            self._set_anchor_pos()

        if self._check_requirements_fulfilled():
            self._finalize_mining()
            return

        self._mine_resources()

    def _set_anchor_pos(self):
        """Estableix la posició anchor_pos per a la mineria."""
        if not self.mc: return
        if self.mc_lock: self.mc_lock.acquire()
        try:
            p = self.mc.player.getTilePos()
            self.anchor_pos = (p.x, p.y - 1, p.z)
            mark_bot(self.mc, p.x - 2, p.y + 1, p.z - 2, wool_color=1, label=self.name)
            self.log.info(f"Posició d'ancoratge establerta a {self.anchor_pos}")
        finally:
            if self.mc_lock: self.mc_lock.release()

    def _check_requirements_fulfilled(self):
        """Comprova si s'han complert els requeriments."""
        if self.requirements:
            return all(self.inventory.get(k, 0) >= v for k, v in self.requirements.items())
        return False

    def _finalize_mining(self):
        """Finalitza la mineria i envia l'inventari."""
        self.log.info(f"Mineria completada. Requeriments complerts: {self.inventory}")
        self._publish_inventory(final=True)
        self.set_state(AgentState.WAITING, "Requeriments complerts, esperant noves tasques")

    def _mine_resources(self):
        """Executa una passada de mineria amb una estratègia."""
        strategy = self.strategies[0]  # GridSearch
        
        # Capturar inventari abans de minar per detectar progrés
        before_inventory = self.inventory.copy()
        
        # Bloc a bloc i no bloquejem per tota l'estratègia
        collected = strategy.mine(self.mc, self.anchor_pos, self.inventory, self.requirements, mc_lock=self.mc_lock)

        progress_made = False
        if collected:
            for k, v in collected.items():
                if v > 0: progress_made = True
                self.inventory[k] = self.inventory.get(k, 0) + v
            if progress_made:
                self.log.info(f"Recol·lectat: {collected}. Inventari actual: {self.inventory}")
                self._publish_inventory()
        
        # Si no s'ha fet progrés, o s'ha acabat la passada pero encara falten coses -> Baixar
        if not self._check_requirements_fulfilled():
             # Moure anchor cap baix
             self.log.info("Passada de mineria completada sense cobrir requeriments. Baixant nivell de mineria...")
             # Baixar segons la mida del strategy grid  - 4 de moment !!
             descent_step = getattr(strategy, 'grid_size', 4)
             new_y = self.anchor_pos[1] - descent_step
             


             self.anchor_pos = (self.anchor_pos[0], new_y, self.anchor_pos[2])
             self.log.info(f"Nova posició d'ancoratge: {self.anchor_pos}")
             # El bucle torna a cridar _mine_resources en el següent cicle act() des de la nova posicio

    def _publish_inventory(self, final=False):
        """Publica l'estat actual de l'inventari."""
        payload = {"inventory": self.inventory}
        if final:
            # En el missatge final, enviem només el que es necessita
            payload["inventory"] = {k: min(self.inventory.get(k, 0), v) for k, v in self.requirements.items()}

        inv_msg = MessageProtocol.create_message("inventory.v1", self.name, "BuilderBot", payload)
        self.message_bus.publish(inv_msg)
        self.log.debug(f"Inventari publicat: {payload['inventory']}")

    def start(self):
        """Inicia la mineria si hi ha requeriments."""
        if self.requirements:
            self.set_state(AgentState.RUNNING, "Iniciant mineria")
            self.log.info(f"Mineria iniciada amb requeriments: {self.requirements}")
        else:
            self.log.warning("No es pot iniciar la mineria sense requeriments.")
            self.set_state(AgentState.IDLE)

    def stop(self):
        """Atura la mineria."""
        self.set_state(AgentState.STOPPED, "Aturat per comanda")
        self.log.info("Mineria aturada.")
        
    def reset(self):
        """Reseteja l'estat del MinerBot."""
        self.log.info("Resetejant MinerBot...")
        self.inventory = {}
        self.requirements = None
        self.anchor_pos = None
        self.set_state(AgentState.IDLE, "Resetejat per a nou workflow")

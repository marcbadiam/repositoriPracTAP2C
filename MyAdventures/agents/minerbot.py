from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from strategies.grid_search import GridSearchStrategy
from strategies.vertical_search import VerticalSearchStrategy
from utils.visuals import mark_bot
from mcpi import block as mcblock
import logging

logger = logging.getLogger(__name__)

class MinerBot(BaseAgent):
    """Agent que mina blocs de terra i pedra, col·lectant recursos."""
    def __init__(self, name, message_bus, mc):
        super().__init__(name)
        self.message_bus = message_bus
        self.mc = mc
        # Grid 4x4x4 per mineria compacta
        self.strategies = [GridSearchStrategy(grid_spacing=1, grid_size=4), VerticalSearchStrategy()]
        self.inventory = {"dirt": 0, "stone": 0}
        self.mining_active = False
        self.anchor_pos = None
        self.requirements = None
        self.collected_this_round = {}
        self.last_requirements = None  # Guarda l'últim paquet per reusar-lo

    def perceive(self):
        """Percep l'inventari actual i comprova si hi ha requeriments pendents."""
        if self.state == AgentState.STOPPED:
            self.set_state(AgentState.STOPPED, reason="Aturada sol·licitada")
            return
        self.log.debug(f"Inventari actual: {self.inventory}")

    def decide(self):
        """Decideix si continuar minant."""
        if self.state == AgentState.STOPPED:
            self.set_state(AgentState.STOPPED, reason="Aturada sol·licitada")
            return
        if self.mining_active:
            self.selected_strategy = self.strategies[0]  # GridSearch simple

    def act(self):
        """Executa la mineria i col·lecció de recursos."""
        if self.state == AgentState.STOPPED or not self.mining_active:
            return

        # Si ja tenim tot el que s'ha demanat, parem de minar i entreguem només el necessari
        if self.requirements and all(self.inventory.get(k, 0) >= v for k, v in self.requirements.items()):
            provided = {k: min(self.inventory.get(k, 0), v) for k, v in self.requirements.items()}
            self.mining_active = False
            self.set_state(AgentState.WAITING, reason="Requeriments complerts")
            self.log.info(f"Mineria aturada: requeriments complerts {provided}")

            # Notificar inventari final (sense sobrants)
            inv_msg = MessageProtocol.create_message(
                msg_type="inventory.v1",
                source=self.name,
                target="BuilderBot",
                payload={"inventory": provided},
                context={"state": self.state.name}
            )
            self.message_bus.publish(inv_msg)

            # Discard sobrants i netejar inventari local
            self.inventory = {k: 0 for k in self.inventory}
            self.anchor_pos = None
            return

        # Ancorar la posició de mineria a la primera execució i no seguir el jugador
        if not self.anchor_pos:
            p = self.mc.player.getTilePos()
            px, pz = int(p.x), int(p.z)
            y = self.mc.getHeight(px, pz)
            self.anchor_pos = (px, y - 1, pz)
            self.log.info(f"Posició d'ancoratge del MinerBot establerta a {self.anchor_pos}")

        ax, ay, az = self.anchor_pos
        mark_bot(self.mc, ax - 2, ay + 1, az - 2, wool_color=1, label=self.name)

        # Mineria amb graella 4x4x4 al voltant de la posició d'ancoratge
        start_pos = self.anchor_pos
        collected_this_tick = self.selected_strategy.mine(
            mc=self.mc,
            start_pos=start_pos,
            inventory=self.inventory,
            requirements=self.requirements,
        ) or {}

        for k, v in collected_this_tick.items():
            if v:
                self.inventory[k] = self.inventory.get(k, 0) + v

        if collected_this_tick:
            self.log.info(f"Mineria: recol·lectats {collected_this_tick}")

        # Publish inventory update (si no hem acabat encara, s'envia l'estoc actual)
        inv_msg = MessageProtocol.create_message(
            msg_type="inventory.v1",
            source=self.name,
            target="BuilderBot",
            payload={"inventory": self.inventory},
            context={"state": self.state.name}
        )
        self.message_bus.publish(inv_msg)
        self.log.debug(f"Inventari publicat: {self.inventory}")

        # Si hem complert requeriments després d'aquest tick, aturem i entreguem només el necessari
        if self.requirements and all(self.inventory.get(k, 0) >= v for k, v in self.requirements.items()):
            provided = {k: min(self.inventory.get(k, 0), v) for k, v in self.requirements.items()}
            self.mining_active = False
            self.set_state(AgentState.WAITING, reason="Requeriments complerts")
            self.log.info(f"Mineria completada: requeriments assolits {provided}")

            final_msg = MessageProtocol.create_message(
                msg_type="inventory.v1",
                source=self.name,
                target="BuilderBot",
                payload={"inventory": provided},
                context={"state": self.state.name}
            )
            self.message_bus.publish(final_msg)

            # Discard sobrants i netejar inventari local
            self.inventory = {k: 0 for k in self.inventory}
            self.anchor_pos = None

    def on_message(self, msg):
        """Gestiona els missatges rebuts del bus de comunicació."""
        if msg.get("type") == "materials.requirements.v1":
            payload = msg.get("payload", {})
            needs = payload.get("needs", {})
            self.requirements = needs
            self.last_requirements = needs.copy()
            self.log.info(f"Requeriments rebuts: {needs}")
            # Reancorar per a un nou workflow
            self.anchor_pos = None
            
            if self.state not in (AgentState.RUNNING, AgentState.PAUSED):
                self.set_state(AgentState.IDLE, reason="Nous requeriments rebuts")

        elif msg.get("type") == "build.complete.v1":
            self.log.info("Construcció completada. Mineria aturada.")
            self.mining_active = False
            self.set_state(AgentState.STOPPED, reason="Construcció finalitzada")

    def start_mining(self):
        """Inicia la mineria si hi ha requeriments."""
        if self.requirements:
            self.mining_active = True
            self.set_state(AgentState.RUNNING, reason="Mineria iniciada per comanda")
            self.log.info(f"Mineria iniciada amb requeriments: {self.requirements}")
            if not self.anchor_pos and self.mc:
                p = self.mc.player.getTilePos()
                px, pz = int(p.x), int(p.z)
                y = self.mc.getHeight(px, pz)
                self.anchor_pos = (px, y - 1, pz)
                self.log.info(f"Posició d'ancoratge del MinerBot establerta a {self.anchor_pos}")
        else:
            self.log.warning("No hi ha requeriments. Usa /workflow run o /miner start després de /explorer start")

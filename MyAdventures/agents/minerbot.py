from .base_agent import BaseAgent, AgentState
from utils.communication import MessageProtocol
from utils.discovery import discover_strategies
from utils.visuals import mark_bot
import logging

logger = logging.getLogger(__name__)


class MinerBot(BaseAgent):
    """Agent que mina blocs de terra i pedra, recolectant recursos."""

    def __init__(self, name, message_bus, mc, mc_lock=None, system_flags=None):
        super().__init__(name, system_flags)
        self.message_bus = message_bus
        self.mc = mc
        self.mc_lock = mc_lock

        self.color = 1

        # Carrega les estratègies dinàmicament
        self.strategies = []
        self._load_strategies()
        self.current_strategy_index = 0

        self.inventory = {"dirt": 0, "stone": 0}
        self.requirements = None
        self.anchor_pos = None

        self.message_bus.subscribe(self.on_message)
        self.set_state(AgentState.IDLE)

    def _load_strategies(self):
        """Carrega les estratègies dinàmicament ."""
        strategy_classes = discover_strategies()
        # Ordenem les estratègies
        sorted_names = sorted(strategy_classes.keys())

        for name in sorted_names:
            cls = strategy_classes[name]
            instance = cls()
            self.strategies.append(instance)
            self.log.info(f"Estratègia carregada: {name}")

    def set_strategy(self, index: int):
        """S'estableix l'estratègia segons l'índex."""
        if 0 <= index < len(self.strategies):
            self.current_strategy_index = index
            strategy_name = self.strategies[index].__class__.__name__
            self.log.info(f"Estratègia canviada a l'índex {index}: {strategy_name}")
            return True, strategy_name
        else:
            self.log.warning("Índex d'estratègia invàlid.")
            return False, None

    def cycle_strategy(self):
        """Ciclem a la següent estratègia."""
        next_index = (self.current_strategy_index + 1) % len(self.strategies)
        return self.set_strategy(next_index)

    def switch_strategy_by_name(self, name: str) -> bool:
        """Canvia l'estratègia buscant-la pel nom de la classe."""
        for i, strategy in enumerate(self.strategies):
            if strategy.__class__.__name__ == name:
                return self.set_strategy(i)
        self.log.warning(f"Estratègia no trobada: {name}")
        return False, None

    def _release_locks(self):
        """Allibera bloquejos espacials (anchor_pos)."""
        if self.anchor_pos:
            self.log.info(f"Alliberant lock espacial a {self.anchor_pos}")
            self.anchor_pos = None

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
            self.log.info("Construcció completada. Resetejant estat del MinerBot.")
            self.reset()
            # self.reset() posa estat en IDLE, no cal stop() a menys que vulguem STOPPED
        elif msg_type == "workflow.reset":
            self.reset()

    def _handle_requirements(self, msg):
        with self.state_lock:
            self.requirements = msg.get("payload", {}).get("needs")
            self.log.info(f"Requeriments de materials rebuts: {self.requirements}")
            for req in self.requirements:
                if req not in self.inventory:
                    self.inventory[req] = 0

            # Comprova el flag del workflow
            if self.system_flags.get("workflow_mode", False):
                self.start()
            else:
                self.set_state(
                    AgentState.WAITING,
                    "Requeriments rebuts (Manual). Esperant comanda -miner start.",
                )
                self.log.info("Mode Manual: No s'inicia la mineria automàticament.")

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

        with self.state_lock:
            if not self.anchor_pos:
                self._set_anchor_pos()

            if self._check_requirements_fulfilled():
                self._finalize_mining()
                return

            self._mine_resources()

    def _set_anchor_pos(self):
        """Estableix la posició anchor_pos per a la mineria."""
        if not self.mc:
            return
        if self.mc_lock:
            self.mc_lock.acquire()
        try:
            p = self.mc.player.getTilePos()
            self.anchor_pos = (p.x, p.y - 1, p.z)
            mark_bot(
                self.mc,
                self.anchor_pos[0],
                self.anchor_pos[1] + 4,
                self.anchor_pos[2],
                wool_color=self.color,
                label=f"{self.name}_Anchor",
            )
            self.log.info(f"Posició d'anchor establerta a {self.anchor_pos}")
        finally:
            if self.mc_lock:
                self.mc_lock.release()

    def _check_requirements_fulfilled(self):
        """Comprova si s'han complert els requeriments."""
        if self.requirements:
            return all(
                self.inventory.get(k, 0) >= v for k, v in self.requirements.items()
            )
        return False

    def _finalize_mining(self):
        """Finalitza la mineria i envia l'inventari."""
        self.log.info(f"Mineria completada. Requeriments complerts: {self.inventory}")
        self._publish_inventory(final=True)
        self.set_state(
            AgentState.WAITING, "Requeriments complerts, esperant noves tasques"
        )

    def _mine_resources(self):
        """Executa una passada de mineria amb una estratègia."""
        if not self.strategies:
            self.log.error("No hi ha estratègies carregades.")
            return

        strategy = self.strategies[self.current_strategy_index]

        # Bloc a bloc i no bloquejem per tota l'estratègia
        collected = strategy.mine(
            self.mc,
            self.anchor_pos,
            self.inventory,
            self.requirements,
            mc_lock=self.mc_lock,
        )

        if strategy.is_stopped:
            self.log.info("Estratègia parada. Parant MinerBot.")
            self.stop()
            return

        progress_made = False
        if collected:
            for k, v in collected.items():
                if v > 0:
                    progress_made = True
                self.inventory[k] = self.inventory.get(k, 0) + v
            if progress_made:
                self.log.info(
                    f"Recol·lectat: {collected}. Inventari actual: {self.inventory}"
                )
                self._publish_inventory()

            # Si s'ha acabat la passada pero encara falten coses -> Baixar
        if not self._check_requirements_fulfilled():
            # Per si anchor deixa de ser valid
            if self.anchor_pos is None:
                self.log.warning(
                    "Ultima posicio d'ancoratge perduda, race condition, abortant."
                )
                return

            # Moure anchor cap baix
            self.log.info(
                "Passada de mineria completada sense cobrir requeriments. Baixant nivell de mineria..."
            )
            # Baixar segons la mida del strategy grid  - 4 de moment !!
            descent_step = getattr(strategy, "grid_size", 4)
            new_y = self.anchor_pos[1] - descent_step

            if new_y <= 6:
                self.log.warning(
                    "S'ha arribat al límit de profunditat (Y=6) sense trobar els materials requerits. Abandonant mineria."
                )
                self.stop()
                return

            self.anchor_pos = (self.anchor_pos[0], new_y, self.anchor_pos[2])
            mark_bot(
                self.mc,
                self.anchor_pos[0],
                self.anchor_pos[1] + 4,
                self.anchor_pos[2],
                wool_color=self.color,
                label=f"{self.name}_Anchor",
            )
            self.log.info(f"Nova posició d'anchor: {self.anchor_pos}")
            # El bucle torna a cridar _mine_resources en el següent cicle act() des de la nova posicio

    def _publish_inventory(self, final=False):
        """Publica l'estat actual de l'inventari."""
        with self.state_lock:
            payload = {"inventory": self.inventory.copy()}
            if final:
                # En el missatge final, enviem només el que es necessita
                payload["inventory"] = {
                    k: min(self.inventory.get(k, 0), v)
                    for k, v in self.requirements.items()
                }

        inv_msg = MessageProtocol.create_message(
            "inventory.v1", self.name, "BuilderBot", payload
        )
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
        if self.strategies and 0 <= self.current_strategy_index < len(self.strategies):
            self.strategies[self.current_strategy_index].handle_stop()
        self.log.info("Mineria aturada.")

    def pause(self):
        """Pausa el MinerBot i la seva estratègia actual."""
        super().pause()
        if self.strategies and 0 <= self.current_strategy_index < len(self.strategies):
            self.strategies[self.current_strategy_index].handle_pause()

    def resume(self):
        """Repren el MinerBot i la seva estratègia actual."""
        super().resume()
        if self.strategies and 0 <= self.current_strategy_index < len(self.strategies):
            self.strategies[self.current_strategy_index].handle_resume()

    def reset(self):
        """Reseteja l'estat del MinerBot."""
        self.log.info("Resetejant MinerBot...")

        with self.state_lock:
            self.inventory = {}
            self.requirements = None
            self.anchor_pos = None

            # Reset estrategies
            if self.strategies:
                for strategy in self.strategies:
                    strategy.reset()

        self.set_state(AgentState.IDLE, "Resetejat per a nou workflow")

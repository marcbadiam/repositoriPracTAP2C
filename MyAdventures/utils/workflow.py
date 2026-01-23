# Sincronització del workflow: coordina Explorer -> Builder -> Miner
import logging
from agents.base_agent import AgentState
from utils.communication import MessageProtocol

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Coordina l'execució del workflow complet entre agents."""
    
    def __init__(self, explorer, builder, miner, message_bus, mc):
        self.explorer = explorer
        self.builder = builder
        self.miner = miner
        self.bus = message_bus
        self.mc = mc
        
        self.stage = 0  # 0: Explorer, 1: Builder, 2: Miner, 3: Build
        self.started = False
    
    def start(self):
        """Inicia el workflow."""
        if self.started:
            logger.warning("Workflow ja en curs")
            return
        
        self.started = True
        self.stage = 0
        logger.info("=" * 60)
        logger.info("WORKFLOW INICIAT: Explorer -> Builder -> Miner -> Build")
        logger.info("=" * 60)
        
        # Stage 0: Explorer analitza terreny
        self._stage_explorer()
    
    def _stage_explorer(self):
        """Stage 1: ExplorerBot analitza terreny."""
        logger.info("[Stage 1/4] EXPLORER - Analitzant terreny...")
        self.explorer.set_state(AgentState.RUNNING, reason="Workflow")
        self.explorer.perceive()
        self.explorer.decide()
        self.explorer.act()
        self.stage = 1
    
    def _stage_builder_bom(self):
        """Stage 2: BuilderBot crea BOM."""
        logger.info("[Stage 2/4] BUILDER - Creant BOM i demandant materials...")
        # Builder rep el mapa via on_message
        self.builder.tick()
        self.stage = 2
    
    def _stage_miner(self):
        """Stage 3: MinerBot inicia mineria."""
        logger.info("[Stage 3/4] MINER - Iniciant mineria...")
        if self.miner.requirements:
            self.miner.start_mining()
            self.stage = 3
        else:
            logger.warning("MinerBot: No hi ha requeriments")
    
    def _stage_build(self):
        """Stage 4: BuilderBot construeix."""
        logger.info("[Stage 4/4] BUILD - Iniciant construcció...")
        # BuilderBot continuarà amb els seus ticks
    
    def tick(self):
        """Executa un pas del workflow."""
        if not self.started:
            return False
        
        if self.stage == 0:
            # Esperar a que explorer publiqui mapa
            if self.builder.target_zone:
                self._stage_builder_bom()
        
        elif self.stage == 1:
            # Esperar a que builder demani materials
            if self.miner.requirements:
                self._stage_miner()
        
        elif self.stage == 2:
            # Esperar a que miner hagi recollit materials
            if self.miner.mining_active:
                # MinerBot està minant
                self.miner.tick()
                # Comprovar si builder pot construir
                can_build = all(self.builder.materials_received.get(k, 0) >= v 
                               for k, v in self.builder.materials_needed.items())
                if can_build:
                    self._stage_build()
        
        elif self.stage == 3:
            # BuilderBot construeix
            self.builder.tick()
            
            if self.builder.completed:
                logger.info("=" * 60)
                logger.info("WORKFLOW COMPLETAT!")
                logger.info("=" * 60)
                self.started = False
                return True
        
        return False
    
    def is_running(self):
        return self.started
    
    def stop(self):
        """Atura el workflow."""
        self.started = False
        self.explorer.set_state(AgentState.STOPPED, reason="Workflow aturat")
        self.builder.set_state(AgentState.STOPPED, reason="Workflow aturat")
        self.miner.set_state(AgentState.STOPPED, reason="Workflow aturat")
        logger.info("Workflow aturat")

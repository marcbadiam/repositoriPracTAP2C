"""
Sistema Multi-Agent Interactiu per a Minecraft
Manté el sistema obert i respon a comandes de xat.
"""
import time
import logging
from agents.explorerbot import ExplorerBot
from agents.minerbot import MinerBot
from agents.builderbot import BuilderBot
from agents.base_agent import AgentState
from utils.communication import MessageBus
from utils.logging_config import setup_logging
from utils.chat_commands import create_default_handlers

logger = logging.getLogger(__name__)


def main():
    """Inicialitza el sistema i manté un bucle esperant comandes."""
    setup_logging()
    logger.info("=" * 60)
    logger.info("Sistema Multi-Agent per Minecraft - Mode Interactiu")
    logger.info("="*60)
    
    # Connectar a Minecraft
    try:
        from mcpi.minecraft import Minecraft
        mc = Minecraft.create()
        logger.info("[OK] Connectat a Minecraft correctament")
    except Exception as e:
        logger.error(f"[ERROR] No s'ha pogut connectar a Minecraft: {e}")
        logger.error("Assegura't que el servidor estigui executant-se")
        raise SystemExit(1)
    
    # Crear bus de missatges
    bus = MessageBus()
    logger.info("[OK] Bus de missatges inicialitzat")
    
    # Crear agents
    explorer = ExplorerBot("ExplorerBot", bus, mc)
    miner = MinerBot("MinerBot", bus, mc)
    builder = BuilderBot("BuilderBot", bus, mc)
    
    agents_dict = {
        "ExplorerBot": explorer,
        "MinerBot": miner,
        "BuilderBot": builder
    }
    logger.info("[OK] Agents creats: ExplorerBot, MinerBot, BuilderBot")
    
    # Subscriure agents al bus
    bus.subscribe("BuilderBot", builder.on_message)
    bus.subscribe("MinerBot", miner.on_message)
    logger.info("[OK] Agents subscrits al bus de missatges")
    
    # Crear gestor de comandes
    cmd_handler = create_default_handlers(agents_dict, mc)
    logger.info("[OK] Sistema de comandes de xat inicialitzat")
    
    # Mostrar missatge de benvinguda a Minecraft
    mc.postToChat("Sistema Multi-Agente iniciado!")
    mc.postToChat("Usa -workflow run per executar el flux complet")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMANDES DISPONIBLES:")
    logger.info("  -workflow run        - Executa flux complet (Explorer->Builder->Miner)")
    logger.info("  -explorer start      - Inicia exploració")
    logger.info("  -builder build       - Inicia construcció")
    logger.info("  -miner start         - Inicia mineria")
    logger.info("  -agent status        - Mostra estat de tots els agents")
    logger.info("  -explorer|miner|builder pause/resume/stop")
    logger.info("="*60)
    logger.info("")
    logger.info("Sistema esperant comandes... (Ctrl+C per sortir)")
    logger.info("")
    
    # Bucle principal: escoltar comandes de xat i executar agents actius
    last_check = time.time()
    check_interval = 0.5  # Revisar cada 0.5 segons
    
    try:
        while True:
            current_time = time.time()
            
            # Revisar comandes de xat periòdicament
            if current_time - last_check >= check_interval:
                try:
                    # Obtenir missatges de xat des de Minecraft
                    chat_posts = mc.events.pollChatPosts()
                    
                    for post in chat_posts:
                        message = post.message
                        logger.info(f"Xat rebut: {message}")
                        
                        # Processar comanda si comença amb -
                        if message.startswith('-'):
                            handled = cmd_handler.handle_command(message)
                            if handled:
                                logger.debug(f"Comanda executada: {message}")
                            else:
                                mc.postToChat("Comanda no reconeguda. Usa -workflow run")
                
                except Exception as e:
                    logger.debug(f"Error al revisar chat: {e}")
                
                last_check = current_time
            
            # Executar cicles dels agents
            # RUNNING: executa perceive->decide->act
            # WAITING: espera a missatges, sense act
            for agent in agents_dict.values():
                # Executem ticks per RUNNING i WAITING per permetre transicions (p.e. quan arriben materials)
                if agent.state not in (AgentState.STOPPED, AgentState.ERROR):
                    try:
                        if agent.state in (AgentState.RUNNING, AgentState.WAITING):
                            agent.tick()
                    except Exception as e:
                        logger.error(f"Error en tick de {agent.name}: {e}", exc_info=True)
            
            # Petita pausa per no saturar la CPU
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("Aturant sistema...")
        logger.info("="*60)
        
        # Aturar tots els agents
        for name, agent in agents_dict.items():
            if hasattr(agent, 'handle_command'):
                try:
                    agent.handle_command('stop', {})
                    logger.info(f"[OK] {name} aturat")
                except Exception as e:
                    logger.error(f"[ERROR] Error en aturar {name}: {e}")
        
        mc.postToChat("Sistema Multi-Agent aturat")
        logger.info("Sistema aturat correctament")
        logger.info("Adeu!")


if __name__ == "__main__":
    main()

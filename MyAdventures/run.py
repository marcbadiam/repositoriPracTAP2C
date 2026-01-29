"""
Sistema Multi-Agent Interactiu per a Minecraft
Manté el sistema obert i respon a comandes de xat.
"""
import time
import logging
import threading
from agents.base_agent import AgentState
from utils.communication import MessageBus
from utils.discovery import discover_agents
from utils.logging_config import setup_logging
from utils.chat_commands import create_default_handlers

logger = logging.getLogger(__name__)


def safe_mc_post(mc, lock, message):
    """Funció auxiliar per publicar de manera segura al xat utilitzant un bloqueig."""
    if lock:
        with lock:
            mc.postToChat(message)
    else:
        mc.postToChat(message)

def main():
    """Inicialitza el sistema i manté un bucle esperant comandes."""
    setup_logging()
    logger.info("=" * 60)
    logger.info("Sistema Multi-Agent per Minecraft - Mode Interactiu")
    logger.info("=" * 60)
    
    # Connectar a Minecraft
    try:
        from mcpi.minecraft import Minecraft
        mc = Minecraft.create()
        logger.info("[OK] Connectat a Minecraft correctament")
    except Exception as e:
        logger.error(f"[ERROR] No s'ha pogut connectar a Minecraft: {e}")
        logger.error("Assegura't que el servidor estigui executant-se")
        raise SystemExit(1)
    
    mc_lock = threading.RLock()
    
    # Inicialitzar Bus de Missatges
    bus = MessageBus()
    logger.info("[OK] Bus de missatges inicialitzat (Mode Broadcast)")
    
    # Inicialitza Flags del Sistema 
    system_flags = {"workflow_mode": False}
    
    # Descobrir i inicialitzar agents
    agents_dict = {}
    agent_classes = discover_agents()
    
    for name, agent_cls in agent_classes.items():
        # inicialitza agent
        agent_instance = agent_cls(name, bus, mc, mc_lock, system_flags)
        agents_dict[name] = agent_instance
        logger.info(f"[OK] Agent inicialitzat: {name}")

    logger.info(f"[OK] Total agents creats: {len(agents_dict)}")

    # Iniciar Threads
    for agent in agents_dict.values():
        agent.start_loop(tick_interval=0.2)
    logger.info("[OK] Fils d'agents en execució")

    # Configurar Gestor de Comandes
    cmd_handler = create_default_handlers(agents_dict, mc, mc_lock, system_flags)
    logger.info("[OK] Sistema de comandes de xat inicialitzat")
    
    safe_mc_post(mc, mc_lock, "Sistema Multi-Agent iniciat! Escriu '-workflow run' o '-explorer start' per començar.")
    
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMANDES DISPONIBLES:")
    logger.info("  -agent status        - Mostra estat de tots els agents")
    logger.info("  -explorer|miner|builder pause/resume/stop")
    logger.info("=" * 60)
    logger.info("Sistema esperant comandes... (Ctrl+C per sortir)")
    
    # Bucle Principal
    last_check = time.time()
    check_interval = 0.5
    
    try:
        while True:
            current_time = time.time()
            if current_time - last_check >= check_interval:
                try:
                    # Llegir xat de forma segura
                    chat_posts = []
                    with mc_lock:
                        chat_posts = mc.events.pollChatPosts()
                    
                    for post in chat_posts:
                        message = post.message
                        logger.info(f"Xat rebut: {message}")
                        
                        if message.startswith('-'):
                            handled = cmd_handler.handle_command(message)
                            if not handled:
                                safe_mc_post(mc, mc_lock, "Comanda no reconeguda.")
                except Exception as e:
                    logger.debug(f"Error al revisar chat: {e}")
                
                last_check = current_time
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("\nAturant sistema...")
        for name, agent in agents_dict.items():
            try:
                agent.stop() # Envia senyal de stop
                agent.stop_loop() # Join thread
                logger.info(f"[OK] {name} aturat")
            except Exception as e:
                logger.error(f"Error aturant {name}: {e}")
        
        safe_mc_post(mc, mc_lock, "Sistema Multi-Agent aturat")
        logger.info("Adeu!")

if __name__ == "__main__":
    main()

"""
Sistema Multi-Agent Interactiu per a Minecraft
Manté el sistema obert i respon a comandes de xat.
"""

import time
import logging
import threading
import argparse
import sys
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

    parser = argparse.ArgumentParser(description="Sistema Multi-Agent per Minecraft")
    parser.add_argument("--workflow", action="store_true", help="Executa en mode workflow automàtic (subprocess)")
    parser.add_argument("--miner-strategy", type=str, help="Nom de l'estratègia de mineria a utilitzar")
    parser.add_argument("--builder-plan", type=str, help="Nom del pla de construcció a utilitzar")
    args = parser.parse_args()

    setup_logging()
    logger.info("=" * 60)
    mode_str = "WORKFLOW AUTOMATITZAT" if args.workflow else "INTERACTIU"
    logger.info(f"Sistema Multi-Agent per Minecraft - Mode {mode_str}")
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
    system_flags = {"workflow_mode": args.workflow}

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

    # Si estem en mode workflow, apliquem configuracions inicials
    if args.workflow:
        # Configurar Miner
        if args.miner_strategy:
            miner = agents_dict.get("MinerBot")
            if miner:
                if miner.switch_strategy_by_name(args.miner_strategy):
                    logger.info(f"WORKFLOW CONFIG: MinerBot estrategia: {args.miner_strategy}")
                else:
                    logger.error(f"WORKFLOW CONFIG: No s'ha pogut posar l'estratègia {args.miner_strategy}")

        # Configurar Builder
        if args.builder_plan:
            builder = agents_dict.get("BuilderBot")
            if builder:
                if builder.switch_plan(args.builder_plan):
                    logger.info(f"WORKFLOW CONFIG: BuilderBot pla: {args.builder_plan}")
                else:
                    logger.error(f"WORKFLOW CONFIG: No s'ha pogut posar el pla {args.builder_plan}")

        # Iniciar Workflow
        logger.info("WORKFLOW: Iniciant seqüència automàtica...")
        explorer = agents_dict.get("ExplorerBot")
        # reset per netejar tot
        from utils.communication import MessageProtocol
        rst_msg = MessageProtocol.create_message("workflow.reset", "System", "all", {})
        bus.publish(rst_msg)
        
        time.sleep(1)

        # Iniciar Explorer
        explorer.start()
        logger.info("WORKFLOW: ExplorerBot iniciat.")

    # Configurar Gestor de Comandes (en workflow no escoltem xat)
    cmd_handler = create_default_handlers(agents_dict, mc, mc_lock, system_flags)
    
    if not args.workflow:
        logger.info("[OK] Sistema de comandes de xat inicialitzat")
        safe_mc_post(
            mc,
            mc_lock,
            "Sistema Multi-Agent iniciat! Escriu '-workflow run' o '-explorer start' per començar.",
        )


    # Bucle Principal
    last_check = time.time()
    check_interval = 0.5

    try:
        while True:
            # MODE WORKFLOW: Monitoritzar finalització
            if args.workflow:
                builder = agents_dict.get("BuilderBot")
                # Comprovar si s'ha completat la construcció (tots els blocs colocats)
                if builder and builder.inventory and builder.build_plan and builder.build_index >= len(builder.build_plan):
                     logger.info("WORKFLOW: Construcció completada. Tancant procés...")
                     time.sleep(2) # Donar temps a logs finals
                     break
                
                time.sleep(1)
                continue

            # MODE INTERACTIU: Escoltar Xat
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

                        if message.startswith("-"):
                            handled = cmd_handler.handle_command(message)
                            if not handled:
                                safe_mc_post(mc, mc_lock, "Comanda no reconeguda.")
                except Exception as e:
                    logger.debug(f"Error al revisar chat: {e}")

                last_check = current_time

            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("\nAturant sistema...")
    finally:
        # neteja final
        for name, agent in agents_dict.items():
            try:
                agent.stop()
                agent.stop_loop()
            except:
                pass
        
        if not args.workflow:
            safe_mc_post(mc, mc_lock, "Sistema Multi-Agent parat")


if __name__ == "__main__":
    main()

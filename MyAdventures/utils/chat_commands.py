import logging
from typing import Callable, Dict, Any
from agents.base_agent import AgentState

logger = logging.getLogger(__name__)


class ChatCommand:
    """Representa una ordre analitzada del xat de Minecraft."""

    def __init__(self, command: str, args: Dict[str, Any] = None):
        self.command = command
        self.args = args or {}

    def __repr__(self):
        return f"ChatCommand({self.command}, {self.args})"


class ChatCommandHandler:
    """Controlador per analitzar i executar ordres del xat."""

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
        self.log = logging.getLogger("ChatCommandHandler")

    def register(self, command: str, handler: Callable):
        """Registra un controlador per a una ordre."""
        self.handlers[command] = handler
        self.log.debug(f"Controlador registrat per a l'ordre: {command}")

    def parse_command(self, message: str) -> ChatCommand:
        """Analitza un missatge i extreu l'ordre i els seus arguments."""
        if not message.startswith("-"):
            return None

        message = message[1:].strip()
        tokens = message.split()
        if not tokens:
            return None

        command_parts = []
        args = {}
        i = 0

        while i < len(tokens):
            token = tokens[i]
            if "=" in token:
                break
            command_parts.append(token)
            i += 1

        while i < len(tokens):
            token = tokens[i]
            if "=" in token:
                key, value = token.split("=", 1)
                try:
                    value = int(value)
                except ValueError:
                    pass
                args[key] = value
            else:
                args[f"arg{len(args)}"] = token
            i += 1

        command = " ".join(command_parts)
        return ChatCommand(command, args)

    def handle_command(self, message: str) -> bool:
        """Executa una ordre si existeix un controlador per a ella."""
        cmd = self.parse_command(message)
        if not cmd:
            return False

        if cmd.command in self.handlers:
            try:
                self.handlers[cmd.command](cmd.args)
                self.log.debug(f"Ordre executada: {cmd.command}")
                return True
            except Exception as e:
                self.log.error(f"Error executant l'ordre {cmd.command}: {e}")
                return False

        for registered_cmd, handler in self.handlers.items():
            if cmd.command.startswith(registered_cmd):
                try:
                    handler(cmd.args)
                    self.log.debug(f"Ordre executada: {registered_cmd}")
                    return True
                except Exception as e:
                    self.log.error(f"Error: {e}")
                    return False

        return False


def create_default_handlers(agents_dict, mc, mc_lock=None, system_flags=None):
    """Crea els gestors de comandes per defecte.

    Args:
        agents_dict: Diccionari d'agents
        mc: Instància de Minecraft
        mc_lock: Lock per sincronitzar accés al socket de Minecraft
    """
    handler = ChatCommandHandler()

    def _safe_post(message: str):
        """Envia missatges al xat de forma segura amb lock opcional."""
        if mc_lock:
            mc_lock.acquire()
        try:
            mc.postToChat(message)
        finally:
            if mc_lock:
                mc_lock.release()

    # Comanda help
    def help_command(args):
        _safe_post("=== COMANDES DISPONIBLES ===")
        for cmd in sorted(handler.handlers.keys()):
            _safe_post(f"-{cmd}")

    handler.register("agent help", help_command)
    handler.register("help", help_command)

    # Comanda status
    def status_command(args):
        _safe_post("=== ESTAT DELS AGENTS ===")
        for name, agent in agents_dict.items():
            _safe_post(f"{name}: {agent.state.name}")

    handler.register("agent status", status_command)

    # Comanda stop (Atura tots els agents)
    def agent_stop_all(args):
        """Pausa completament tots els agents."""
        _safe_post("Aturant tots els agents i finalitzant workflow...")

        # Resetegem el flag de workflow global
        if system_flags is not None:
            system_flags["workflow_mode"] = False

        for name, agent in agents_dict.items():
            try:
                agent.stop()
                _safe_post(f"[{name}] Aturat correctament.")
            except Exception as e:
                logger.error(f"Error aturant {name}: {e}")
                _safe_post(f"[{name}] Error al aturar: {e}")

    handler.register("agent stop", agent_stop_all)

    def agent_pause_all(args):
        """Pausa qualsevol agent que estigui executant-se."""
        count = 0
        for name, agent in agents_dict.items():
            if agent.state == AgentState.RUNNING:
                agent.pause()
                _safe_post(f"[{name}] Pausat automàticament.")
                count += 1
        if count == 0:
            _safe_post("Cap agent actiu per pausar.")

    handler.register("agent pause", agent_pause_all)

    def agent_resume_all(args):
        """Repren qualsevol agent que estigui pausat."""
        count = 0
        for name, agent in agents_dict.items():
            if agent.state == AgentState.PAUSED:
                agent.resume()
                _safe_post(f"[{name}] Repres automàticament.")
                count += 1
        if count == 0:
            _safe_post("Cap agent pausat per reprendre.")

    handler.register("agent resume", agent_resume_all)

    def stop_all_active_agents():
        """Atura i reseteja tots els agents"""
        count = 0
        for name, agent in agents_dict.items():
            # Executem reset en tots els agents per netejar flags i estats
            agent.reset()
            count += 1
        return count

    # Explorer commands
    def explorer_start(args):
        # Aturar i netejar sessió anterior
        stop_all_active_agents()

        explorer = agents_dict.get("ExplorerBot")
        if explorer:
            # Mode Manual: Desactivem flag de workflow
            if system_flags is not None:
                system_flags["workflow_mode"] = False

            # Assegurar que el thread estigui actiu
            if not explorer._thread or not explorer._thread.is_alive():
                explorer.start_loop()

            explorer.map_sent = False
            explorer.set_state(AgentState.RUNNING, reason="Comanda usuari (manual)")
            _safe_post("[ExplorerBot] Exploració iniciada (Mode Manual)")
        else:
            _safe_post("ExplorerBot no trobat")

    handler.register("explorer start", explorer_start)

    def explorer_switch_range(args):
        """Canvia el rang d'exploració de l'ExplorerBot."""
        explorer = agents_dict.get("ExplorerBot")
        if explorer:
            new_range = explorer.cycle_range()
            _safe_post(f"[ExplorerBot] Rang canviat a: {new_range} blocs")
        else:
            _safe_post("ExplorerBot no trobat")

    handler.register("explorer switchrange", explorer_switch_range)

    # Builder commands
    def builder_build(args):
        builder = agents_dict.get("BuilderBot")
        if builder and builder.target_zone:
            # Mode Manual: Desactivem flag de workflow
            if system_flags is not None:
                system_flags["workflow_mode"] = False

            # Assegurar que el thread estigui actiu
            if not builder._thread or not builder._thread.is_alive():
                builder.start_loop()

            builder.set_state(AgentState.RUNNING, reason="User command (manual)")
            _safe_post("[BuilderBot] Construcció iniciada (Mode Manual)")
        else:
            _safe_post("[BuilderBot] Error: Executa -explorer start primer")

    handler.register("builder build", builder_build)

    # Builder switch plan
    def builder_switch(args):
        builder = agents_dict.get("BuilderBot")
        if not builder:
            _safe_post("BuilderBot no trobat")
            return

        # Rotar plan
        new_plan, bom = builder.cycle_plan()
        _safe_post(f"[BuilderBot] Pla canviat a: {new_plan}")
        _safe_post(f"Nous requisits: {bom}")

    handler.register("builder switchplan", builder_switch)

    # Miner commands
    def miner_start(args):
        miner = agents_dict.get("MinerBot")
        if miner:
            # Mode Manual: Desactivem flag de workflow
            if system_flags is not None:
                system_flags["workflow_mode"] = False

            # Assegurar que el thread estigui actiu
            if not miner._thread or not miner._thread.is_alive():
                miner.start_loop()

            miner.start()
            _safe_post("[MinerBot] Mineria iniciada (Mode Manual)")
        else:
            _safe_post("MinerBot no trobat")

    handler.register("miner start", miner_start)

    def miner_switch(args):
        miner = agents_dict.get("MinerBot")
        if not miner:
            _safe_post("MinerBot no trobat")
            return

        success, name = miner.cycle_strategy()
        _safe_post(f"[MinerBot] Estratègia canviada a: {name}")

    handler.register("miner switch", miner_switch)

    # Workflow command - MAIN ENTRY POINT
    def workflow_run(args):
        """Executa el flux complet: Explorer -> Builder -> Miner -> Build"""
        explorer = agents_dict.get("ExplorerBot")

        if not explorer:
            _safe_post("[Workflow] Error: ExplorerBot no trobat")
            return

        _safe_post("")
        _safe_post("=" * 40)
        _safe_post("[Workflow] INICIANT FLUX COMPLET (NOVA SESSIO)")
        _safe_post("=" * 40)

        # Aturar tot el que hi hagi abans
        stop_all_active_agents()

        # Activar flag workflow
        if system_flags is not None:
            system_flags["workflow_mode"] = True
            logger.info("WORKFLOW MODE: ACTIVAT")

        # Potser no cal fer el reset des el bus?
        if explorer and hasattr(explorer, "message_bus"):
            from utils.communication import MessageProtocol

            rst_msg = MessageProtocol.create_message(
                "workflow.reset", "User", "all", {}
            )
            explorer.message_bus.publish(rst_msg)

        import time

        time.sleep(0.5)

        for name, agent in agents_dict.items():
            # Assegurar sempre que el thread s'està executant independentment de l'estat
            if not agent._thread or not agent._thread.is_alive():
                logger.info(f"Reiniciant fil d'execució per a {name}")
                agent.start_loop()

            # Si estava STOPPED manualment, el tornem a IDLE
            if agent.state == AgentState.STOPPED:
                agent.set_state(AgentState.IDLE, reason="Workflow restart")

        # Iniciar Explorer (que iniciarà la cadena)
        _safe_post("Iniciant ExplorerBot per començar la cadena...")
        explorer.handle_command("start", {})

    handler.register("workflow run", workflow_run)

    return handler

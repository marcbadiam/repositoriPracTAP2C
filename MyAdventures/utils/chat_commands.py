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
        if not message.startswith('-'):
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
            if '=' in token:
                break
            command_parts.append(token)
            i += 1
        
        while i < len(tokens):
            token = tokens[i]
            if '=' in token:
                key, value = token.split('=', 1)
                try:
                    value = int(value)
                except ValueError:
                    pass
                args[key] = value
            else:
                args[f'arg{len(args)}'] = token
            i += 1
        
        command = ' '.join(command_parts)
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


def create_default_handlers(agents_dict, mc, mc_lock=None):
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
        _safe_post("-workflow run              Executa flux complet")
        _safe_post("-explorer start            Inicia exploració")
        _safe_post("-builder build             Construeix plataforma")
        _safe_post("-miner start               Inicia mineria")
        _safe_post("-agent status              Mostra estat agents")
    
    handler.register('agent help', help_command)
    handler.register('help', help_command)
    
    # Comanda status
    def status_command(args):
        for name, agent in agents_dict.items():
            _safe_post(f"{name}: {agent.state.name}")
    
    handler.register('agent status', status_command)
    
    # Explorer commands
    def explorer_start(args):
        explorer = agents_dict.get("ExplorerBot")
        if explorer:
            explorer.map_sent = False
            explorer.set_state(AgentState.RUNNING, reason="User command")
            _safe_post("[ExplorerBot] Exploració iniciada")
        else:
            _safe_post("ExplorerBot no trobat")
    
    handler.register('explorer start', explorer_start)
    
    # Builder commands
    def builder_build(args):
        builder = agents_dict.get("BuilderBot")
        if builder and builder.target_zone:
            builder.set_state(AgentState.RUNNING, reason="User command")
            _safe_post("[BuilderBot] Construcció iniciada")
        else:
            _safe_post("[BuilderBot] Error: Executa -explorer start primer")
    
    handler.register('builder build', builder_build)

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

    handler.register('builder switchplan', builder_switch)
    
    # Miner commands
    def miner_start(args):
        miner = agents_dict.get("MinerBot")
        if miner:
            miner.start()
            _safe_post("[MinerBot] Mineria iniciada")
        else:
            _safe_post("MinerBot no trobat")
    
    handler.register('miner start', miner_start)
    
    def miner_switch(args):
        miner = agents_dict.get("MinerBot")
        if not miner:
            _safe_post("MinerBot no trobat")
            return
            
        success, name = miner.cycle_strategy()
        _safe_post(f"[MinerBot] Estratègia canviada a: {name}")


    handler.register('miner switch', miner_switch)
    
    # Workflow command - MAIN ENTRY POINT
    def workflow_run(args):
        """Executa el flux complet: Explorer -> Builder -> Miner -> Build"""
        explorer = agents_dict.get("ExplorerBot")
        
        if not explorer:
            _safe_post("[Workflow] Error: ExplorerBot no trobat")
            return
        
        _safe_post("")
        _safe_post("=" * 40)
        _safe_post("[Workflow] INICIANT FLUX COMPLET")
        _safe_post("=" * 40)
        
        # Global Reset
        _safe_post("Resetejant estat del sistema...")
        # Enviar missatge de reset per assegurar neteja estats interns
        if explorer and hasattr(explorer, "message_bus"):
             from utils.communication import MessageProtocol
             rst_msg = MessageProtocol.create_message("workflow.reset", "User", "all", {})
             explorer.message_bus.publish(rst_msg)
        
        # Cridar explícitament reset en tots els agents per estar segurs
        for name, agent in agents_dict.items():
             if hasattr(agent, 'reset'):
                 agent.reset()
        
        # Validar que tots els agents estan llestos/running (Wait a bit for resets?)
        import time
        time.sleep(0.5)

        for name, agent in agents_dict.items():
             # Assegurar sempre que el thread s'està executant independentment de l'estat
             if not agent._thread or not agent._thread.is_alive():
                 logger.info(f"Reiniciant fil d'execució per a {name}")
                 agent.start_loop()
             
             if agent.state == AgentState.STOPPED:
                 agent.set_state(AgentState.IDLE, reason="Workflow restart")

        # Iniciar Explorer (que iniciarà la cadena)
        _safe_post("Iniciant ExplorerBot per començar la cadena...")
        explorer.handle_command('start', {})
    
    handler.register('workflow run', workflow_run)
    
    # Agent control commands (pause, resume, stop)
    for name, agent in agents_dict.items():
        agent_prefix = name.lower().replace('bot', '')
        
        def make_pause_handler(a, agent_name):
            def pause_cmd(args):
                a.handle_command('pause', args)
                _safe_post(f"[{agent_name}] Pausat")
            return pause_cmd
        
        def make_resume_handler(a, agent_name):
            def resume_cmd(args):
                a.handle_command('resume', args)
                _safe_post(f"[{agent_name}] Repres")
            return resume_cmd
        
        def make_stop_handler(a, agent_name):
            def stop_cmd(args):
                a.handle_command('stop', args)
                _safe_post(f"[{agent_name}] Aturat")
            return stop_cmd
        
        handler.register(f'{agent_prefix} pause', make_pause_handler(agent, name))
        handler.register(f'{agent_prefix} resume', make_resume_handler(agent, name))
        handler.register(f'{agent_prefix} stop', make_stop_handler(agent, name))
    
    return handler

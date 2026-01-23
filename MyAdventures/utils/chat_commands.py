import logging
import re
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


def create_default_handlers(agents_dict, mc):
    """Crea els gestors de comandes per defecte."""
    handler = ChatCommandHandler()
    
    # Comanda help
    def help_command(args):
        mc.postToChat("=== COMANDES DISPONIBLES ===")
        mc.postToChat("-workflow run              Executa flux complet")
        mc.postToChat("-explorer start            Inicia exploració")
        mc.postToChat("-builder build             Construeix plataforma")
        mc.postToChat("-miner start               Inicia mineria")
        mc.postToChat("-agent status              Mostra estat agents")
    
    handler.register('agent help', help_command)
    handler.register('help', help_command)
    
    # Comanda status
    def status_command(args):
        for name, agent in agents_dict.items():
            mc.postToChat(f"{name}: {agent.state.name}")
    
    handler.register('agent status', status_command)
    
    # Explorer commands
    def explorer_start(args):
        explorer = agents_dict.get("ExplorerBot")
        if explorer:
            explorer.map_sent = False
            explorer.set_state(AgentState.RUNNING, reason="User command")
            explorer.perceive()
            explorer.decide()
            explorer.act()
            mc.postToChat("[ExplorerBot] Exploració iniciada")
        else:
            mc.postToChat("ExplorerBot no encontrat")
    
    handler.register('explorer start', explorer_start)
    
    # Builder commands
    def builder_build(args):
        builder = agents_dict.get("BuilderBot")
        if builder and builder.target_zone:
            builder.set_state(AgentState.RUNNING, reason="User command")
            builder.tick()
            mc.postToChat("[BuilderBot] Construcció iniciada")
        else:
            mc.postToChat("[BuilderBot] Error: Executa -explorer start primer")
    
    handler.register('builder build', builder_build)
    
    # Miner commands
    def miner_start(args):
        miner = agents_dict.get("MinerBot")
        if miner:
            miner.start_mining()
            mc.postToChat("[MinerBot] Mineria iniciada")
        else:
            mc.postToChat("MinerBot no encontrat")
    
    handler.register('miner start', miner_start)
    
    # Workflow command - MAIN ENTRY POINT
    def workflow_run(args):
        """Executa el flux complet: Explorer -> Builder -> Miner -> Build"""
        explorer = agents_dict.get("ExplorerBot")
        builder = agents_dict.get("BuilderBot")
        miner = agents_dict.get("MinerBot")
        
        if not (explorer and builder and miner):
            mc.postToChat("[Workflow] Error: Agents no encontrats")
            return
        
        mc.postToChat("")
        mc.postToChat("=" * 40)
        mc.postToChat("[Workflow] INICIANT FLUX COMPLET")
        mc.postToChat("=" * 40)
        
        # Stage 1: Explorer
        mc.postToChat("[1/4] EXPLORER - Analitzant terreny...")
        explorer.map_sent = False
        explorer.set_state(AgentState.RUNNING, reason="Workflow")
        explorer.perceive()
        explorer.decide()
        explorer.act()
        
        # Stage 2: Builder rebut mapa i crea BOM
        mc.postToChat("[2/4] BUILDER - Rebent mapa i creant BOM...")
        builder.tick()
        
        # Stage 3: Miner rebut requeriments i comença mineria
        mc.postToChat("[3/4] MINER - Rebent requeriments i iniciant mineria...")
        if miner.requirements:
            miner.start_mining()
        else:
            mc.postToChat("[Workflow] Estableciendo requerimientos manualmente...")
            miner.requirements = builder.materials_needed.copy()
            miner.start_mining()
        
        # Stage 4: Builder construeix quan té materials
        mc.postToChat("[4/4] BUILDER - Iniciant construcció...")
        mc.postToChat("")
        mc.postToChat("Sistema executant workflow...")
        mc.postToChat("Espera a que es complete la construcció")
    
    handler.register('workflow run', workflow_run)
    
    # Agent control commands (pause, resume, stop)
    for name, agent in agents_dict.items():
        agent_prefix = name.lower().replace('bot', '')
        
        def make_pause_handler(a, agent_name):
            def pause_cmd(args):
                a.handle_command('pause', args)
                mc.postToChat(f"[{agent_name}] Pausat")
            return pause_cmd
        
        def make_resume_handler(a, agent_name):
            def resume_cmd(args):
                a.handle_command('resume', args)
                mc.postToChat(f"[{agent_name}] Repres")
            return resume_cmd
        
        def make_stop_handler(a, agent_name):
            def stop_cmd(args):
                a.handle_command('stop', args)
                mc.postToChat(f"[{agent_name}] Aturat")
            return stop_cmd
        
        handler.register(f'{agent_prefix} pause', make_pause_handler(agent, name))
        handler.register(f'{agent_prefix} resume', make_resume_handler(agent, name))
        handler.register(f'{agent_prefix} stop', make_stop_handler(agent, name))
    
    return handler

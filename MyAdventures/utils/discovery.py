"""
Mòdul de descobriment reflexiu per a registre automàtic d'agents i estratègies.
Utilitza les capacitats de reflexió de Python per descobrir i carregar mòduls dinàmicament.
"""
import importlib
import inspect
import os
import pkgutil
import logging

logger = logging.getLogger(__name__)


def discover_classes(package_name, base_class):
    """
    Descobreix i registra automàticament classes que hereten de base_class.
    
    Args:
        package_name: Nom del paquet a escannejar
        base_class: Classe base que han d'heretar les classes descobertes
        
    Returns:
        dict: Mapa de noms de classes a objectes de classe
    """
    discovered = {}
    
    try:
        # Importa el paquet
        package = importlib.import_module(package_name)
        
        # Itera a través de tots els mòduls del paquet
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if modname.startswith('_'):
                # Salta els mòduls privats
                continue
                
            full_module_name = f"{package_name}.{modname}"
            
            # Importa el mòdul
            module = importlib.import_module(full_module_name)
            
            # Inspecciona el mòdul
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Verifica que la classe es defineix en aquest mòdul i hereta de base_class
                if (obj.__module__ == full_module_name and 
                    issubclass(obj, base_class) and 
                    obj != base_class):
                    discovered[name] = obj
                    logger.info(f"Descoberta {name} de {full_module_name}")
                
    except Exception as e:
        logger.error(f"No s'ha pogut descobrir classes a {package_name}: {e}")
    
    return discovered


def discover_strategies():
    """
    Descobreix totes les estratègies
    
    Returns:
        dict: Mapa d'estratègies
    """
    from strategies.strategy_base import MiningStrategy
    return discover_classes('strategies', MiningStrategy)


def discover_agents():
    """
    Descobreix totes les classes d'agent.
    
    Returns:
        dict: Mapa d'agents
    """
    from agents.base_agent import BaseAgent
    return discover_classes('agents', BaseAgent)


def discover_build_plans():
    """
    Descobreix tots els plans
    
    Returns:
        dict: Mapa de plans
    """
    from strategies.build_plans.base_plan import BuildPlan
    return discover_classes('strategies.build_plans', BuildPlan)

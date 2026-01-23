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


def discover_classes(package_name, base_class, package_path=None):
    """
    Descobreix i registra automàticament classes que hereten de base_class.
    
    Args:
        package_name: Nom del paquet a escannejar (p.ex., 'strategies')
        base_class: Classe base que han d'heretar les classes descobertes
        package_path: Camí opcional al directori del paquet
        
    Returns:
        dict: Mapa de noms de classes a objectes de classe
    """
    discovered = {}
    
    try:
        # Importa el paquet
        package = importlib.import_module(package_name)
        
        # Obté el camí del paquet
        if package_path is None:
            package_path = package.__path__
        
        # Itera a través de tots els mòduls del paquet
        for importer, modname, ispkg in pkgutil.iter_modules(package_path):
            if modname.startswith('_'):
                # Salta els mòduls privats
                continue
                
            full_module_name = f"{package_name}.{modname}"
            
            try:
                # Importa el mòdul
                module = importlib.import_module(full_module_name)
                
                # Inspecció del mòdul per a classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Verifica que la classe es defineix en aquest mòdul i hereta de base_class
                    if (obj.__module__ == full_module_name and 
                        issubclass(obj, base_class) and 
                        obj != base_class):
                        discovered[name] = obj
                        logger.info(f"Descoberta {name} de {full_module_name}")
                        
            except Exception as e:
                logger.warning(f"No s'ha pogut importar {full_module_name}: {e}")
                
    except Exception as e:
        logger.error(f"No s'ha pogut descobrir classes a {package_name}: {e}")
    
    return discovered


def discover_strategies():
    """
    Descobreix totes les classes d'estratègia de mineria.
    
    Returns:
        dict: Mapa de noms d'estratègia a classes d'estratègia
    """
    from strategies.strategy_base import MiningStrategy
    return discover_classes('strategies', MiningStrategy)


def discover_agents():
    """
    Descobreix totes les classes d'agent.
    
    Returns:
        dict: Mapa de noms d'agent a classes d'agent
    """
    from agents.base_agent import BaseAgent
    return discover_classes('agents', BaseAgent)

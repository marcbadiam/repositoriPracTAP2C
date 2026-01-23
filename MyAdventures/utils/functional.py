"""
Utilitats de programació funcional per a transformació i agregació de dades.
Demostra l'ús de decoradors, map, filter, reduce, i funcions d'ordre superior.
"""
from functools import reduce, wraps
import logging
from typing import Callable, List, Dict, Any

logger = logging.getLogger(__name__)


# Exemples de decoradors
def log_execution(func: Callable) -> Callable:
    """
    Decorador que registra l'execució de funcions.
    Exemple del paradigma de programació funcional.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Executant {func.__name__} amb args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} ha retornat {result}")
        return result
    return wrapper


def validate_terrain_data(func: Callable) -> Callable:
    """
    Decorador que valida les dades del terreny abans del processament.
    """
    @wraps(func)
    def wrapper(terrain_data, *args, **kwargs):
        if not terrain_data:
            logger.warning(f"{func.__name__}: Dades de terreny buides")
            return []
        if not isinstance(terrain_data, (list, dict)):
            logger.error(f"{func.__name__}: Tipus de dades de terreny no vàlid")
            return []
        return func(terrain_data, *args, **kwargs)
    return wrapper


# Funcions d'ordre superior per a anàlisi de terreny
@log_execution
@validate_terrain_data
def find_flat_zones(terrain_data: List[Dict], max_variance: float = 2.0) -> List[Dict]:
    """
    Cercar zones planes en dades de terreny usant filter.
    
    Args:
        terrain_data: Llista de punts de terreny amb dades d'elevació
        max_variance: Variació d'elevació màxima permesa
        
    Returns:
        Llista de zones planes
    """
    def is_flat(zone):
        if 'variance' in zone:
            return zone['variance'] <= max_variance
        if 'elevation' in zone:
            return True  # Single point is flat by definition
        return False
    
    return list(filter(is_flat, terrain_data))


@log_execution
def calculate_total_resources(inventories: List[Dict[str, int]]) -> Dict[str, int]:
    """
    Calcular recursos totals a través de múltiples inventaris usant reduce.
    
    Args:
        inventories: Llista de diccionaris d'inventari
        
    Returns:
        Dict amb comptes de recursos agregats
    """
    def merge_inventories(acc, inventory):
        for resource, count in inventory.items():
            acc[resource] = acc.get(resource, 0) + count
        return acc
    
    return reduce(merge_inventories, inventories, {})


@log_execution
def extract_elevations(terrain_data: List[Dict]) -> List[float]:
    """
    Extreure valors d'elevació usant map.
    
    Args:
        terrain_data: Llista de punts de terreny
        
    Returns:
        Llista de valors d'elevació
    """
    return list(map(lambda point: point.get('elevation', 0), terrain_data))


@log_execution
def calculate_terrain_stats(terrain_data: List[Dict]) -> Dict[str, Any]:
    """
    Calcular estadístiques comprehensives del terreny usant composició funcional.
    
    Args:
        terrain_data: Llista de punts de terreny
        
    Returns:
        Dict amb estadístiques del terreny
    """
    if not terrain_data:
        return {
            "count": 0,
            "avg_elevation": 0,
            "min_elevation": 0,
            "max_elevation": 0,
            "flat_zones": []
        }
    
    elevations = extract_elevations(terrain_data)
    
    return {
        "count": len(elevations),
        "avg_elevation": sum(elevations) / len(elevations) if elevations else 0,
        "min_elevation": min(elevations) if elevations else 0,
        "max_elevation": max(elevations) if elevations else 0,
        "flat_zones": find_flat_zones(terrain_data)
    }


def compose(*functions):
    """
    Composar múltiples funcions en una sola funció (de dreta a esquerra).
    Exemple: compose(f, g, h)(x) = f(g(h(x)))
    """
    def inner(arg):
        for func in reversed(functions):
            arg = func(arg)
        return arg
    return inner


def filter_by_resource(resource_type: str) -> Callable:
    """
    Funció d'ordre superior que retorna una funció filter per a recurs específic.
    
    Args:
        resource_type: Tipus de recurs a filtrar
        
    Returns:
        Funció filter
    """
    def filter_func(inventory: Dict[str, int]) -> bool:
        return resource_type in inventory and inventory[resource_type] > 0
    
    return filter_func


@log_execution
def summarize_mining_results(mining_sessions: List[Dict]) -> Dict[str, Any]:
    """
    Resumir resultats de mineria usant patró map/filter/reduce.
    
    Args:
        mining_sessions: Llista de dades de sessió de mineria
        
    Returns:
        Estadístiques de resum
    """
    # Extreure inventaris
    inventories = list(map(lambda s: s.get('inventory', {}), mining_sessions))
    
    # Calcular totals
    total_resources = calculate_total_resources(inventories)
    
    # Cercar sessions exitoses (aquelles amb recursos)
    successful = list(filter(lambda inv: sum(inv.values()) > 0, inventories))
    
    return {
        "total_sessions": len(mining_sessions),
        "successful_sessions": len(successful),
        "total_resources": total_resources,
        "success_rate": len(successful) / len(mining_sessions) if mining_sessions else 0
    }

"""
Utilitats de programació funcional per a l'anàlisi de logs.
"""

from functools import reduce
import logging
import json
import os
from typing import Dict, Any, Iterator, Iterable

logger = logging.getLogger(__name__)


# parse
def parse_log_line(line: str) -> Dict[str, Any]:
    """
    Parseja una línia de log en format JSON.
    Gestionem errors amb try-except.
    """
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"level": "ERROR", "message": "Log line malformed", "raw": line}


# map
def load_logs(file_path: str) -> Iterator[Dict[str, Any]]:
    """
    Generador que llegeix logs d'un fitxer línia per línia (lazy).
    Això és eficient ja que podem tenir molts logs.
    """
    if not os.path.exists(file_path):
        logger.error(f"El fitxer {file_path} no existeix.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        # Map: Transformar cada línia de text en un dict
        yield from map(parse_log_line, f)


# filter
def filter_logs(logs: Iterable[Dict], **criteria) -> Iterator[Dict]:
    """
    Filtra els logs basant-se en criteris clau-valor.
    Exemple: filter_logs(logs, level="ERROR", logger="MinerBot")
    """

    def match_criteria(log_entry):
        for key, value in criteria.items():
            if log_entry.get(key) != value:
                return False
        return True

    return filter(match_criteria, logs)


# reduce
def count_logs_by_level(logs: Iterable[Dict]) -> Dict[str, int]:
    """
    Compta quants logs hi ha de cada nivell usant reduce.
    """

    def reducer(acc, log):
        level = log.get("level", "UNKNOWN")
        acc[level] = acc.get(level, 0) + 1
        return acc

    return reduce(reducer, logs, {})


# reduce
def get_agent_activity(logs: Iterable[Dict]) -> Dict[str, int]:
    """
    Analitza l'activitat per logger amb reduce.
    """

    def reducer(acc, log):
        agent = log.get("logger", "Unknown")
        acc[agent] = acc.get(agent, 0) + 1
        return acc

    return reduce(reducer, logs, {})

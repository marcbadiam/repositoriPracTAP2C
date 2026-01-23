# Estratègia de cerca vertical per a mineria
from .strategy_base import MiningStrategy
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class VerticalSearchStrategy(MiningStrategy):
    """Perfora cap avall a través de capes per extreure recursos a profunditats creixents.
    
    Aquesta estratègia mina blocs verticalment cap avall des de la posició inicial,
    extraient recursos a nivells progressivament més profunds. Els recursos més valuosos
    s'hi troben típicament a major profunditat.
    """
    
    def __init__(self, min_depth: int = -60, max_depth: int = -1):
        """
        Inicialitzar estratègia de cerca vertical.
        
        Args:
            min_depth: Profunditat mínima (coordenada Y) a minar (per defecte: -60 en MC recent)
            max_depth: Profunditat màxima (coordenada Y) a minar (per defecte: -1)
        """
        super().__init__()
        self.min_depth = min_depth
        self.max_depth = max_depth
        self.current_depth = None
    
    def mine(self, mc=None, start_pos: Tuple[int, int, int] = None, 
             inventory: Dict = None, requirements: Dict = None) -> Dict:
        """
        Executar mineria de perforació vertical cap avall a través de capes.
        
        Args:
            mc: Instància de Minecraft
            start_pos: Posició inicial (x, y, z)
            inventory: Diccionari d'inventari actual amb requeriments
            
        Returns:
            dict: Materials col·lectats {material: quantitat}
        """
        if inventory is None:
            inventory = {}
        if requirements is None:
            requirements = {}
        
        collected_materials = {}
        working_inventory = inventory.copy()
        self.materials_collected = {}
        
        if start_pos is None:
            logger.warning("Cap posició inicial proporcionada per a cerca vertical")
            return collected_materials
        
        self.current_position = start_pos
        start_x, start_y, start_z = start_pos
        
        logger.info(f"Iniciando mineria per cerca vertical a {start_pos}")
        
        # Perforar cap avall des de la posició inicial
        current_y = start_y
        block_types = ["stone", "dirt", "sand"]
        
        while current_y >= self.min_depth:
            if self.is_stopped:
                logger.info(f"Cerca vertical aturat a profunditat {current_y}")
                break
            
            while self.is_paused:
                pass
            
            self.current_depth = current_y
            self.current_position = (start_x, current_y, start_z)
            
            # Minar blocs a la profunditat actual
            for block_type in block_types:
                if self.is_stopped:
                    break
                
                if requirements:
                    remaining = requirements.get(block_type, 0) - working_inventory.get(block_type, 0)
                    if remaining <= 0:
                        continue

                materials = self.mine_block(mc, self.current_position, block_type, working_inventory, requirements)
                collected_materials = self._merge_materials(collected_materials, materials)
                working_inventory = self.update_inventory(working_inventory, materials)
            
            self.materials_collected = collected_materials.copy()
            logger.debug(f"Profunditat {current_y}: col·lectat {collected_materials}")

            if requirements and self.validate_requirements(working_inventory, requirements):
                logger.info("Requeriments assolits, aturant cerca vertical")
                return collected_materials
            
            # Moure's al següent nivell de profunditat
            current_y -= 1
        
        logger.info(f"Cerca vertical completada. Blocs minats: {self.blocks_mined}")
        return collected_materials
    
    def _merge_materials(self, dict1: Dict, dict2: Dict) -> Dict:
        """
        Fusionar dos diccionaris de materials.
        
        Args:
            dict1: Primer diccionari de materials
            dict2: Segon diccionari de materials
            
        Returns:
            dict: Diccionari fusionat amb quantitats sumades
        """
        result = dict1.copy()
        for key, value in dict2.items():
            result[key] = result.get(key, 0) + value
        return result

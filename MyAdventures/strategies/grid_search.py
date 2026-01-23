# Estratègia de cerca en graella per a mineria
from .strategy_base import MiningStrategy
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GridSearchStrategy(MiningStrategy):
    """Explora una regió cúbica seguint un patró de graella estructurat per a cobertura uniforme.
    
    Aquesta estratègia mina blocs de forma sistàtica en una graella cúbica, movent-se per la regió
    amb un patró d'espaiament regular per assegurar extracció integral de recursos.
    """
    
    def __init__(self, grid_spacing: int = 2, grid_size: int = 16):
        """
        Inicialitzar estratègia de cerca en graella.
        
        Args:
            grid_spacing: Distància entre blocs minats a la graella (per defecte: 2)
            grid_size: Mida de la regió cúbica a minar (per defecte: 16 blocs)
        """
        super().__init__()
        self.grid_spacing = grid_spacing
        self.grid_size = grid_size
    
    def mine(self, mc=None, start_pos: Tuple[int, int, int] = None, 
             inventory: Dict = None, requirements: Dict = None) -> Dict:
        """
        Executar mineria basada en graella a través d'una regió cúbica.
        
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
            logger.warning("Cap posició inicial proporcionada per a cerca en graella")
            return collected_materials
        
        self.current_position = start_pos
        logger.info(f"Iniciando mineria per cerca en graella a {start_pos}")
        
        start_x, start_y, start_z = start_pos
        block_types = ["stone", "dirt", "sand"]
        
        # Iterar a través dels punts de la graella
        for x_offset in range(0, self.grid_size, self.grid_spacing):
            if self.is_stopped:
                break
            while self.is_paused:
                pass
            
            for z_offset in range(0, self.grid_size, self.grid_spacing):
                if self.is_stopped:
                    break
                
                for y_offset in range(-(self.grid_size - 1), self.grid_size, self.grid_spacing):
                    if self.is_stopped:
                        break
                    
                    current_pos = (
                        start_x + x_offset,
                        start_y + y_offset,
                        start_z + z_offset
                    )
                    self.current_position = current_pos
                    
                    # Minar cada tipus de bloc en aquesta posició
                    for block_type in block_types:
                        # Evita minar si ja hem cobert el requisit per a aquest material
                        if requirements:
                            remaining = requirements.get(block_type, 0) - working_inventory.get(block_type, 0)
                            if remaining <= 0:
                                continue

                        materials = self.mine_block(mc, current_pos, block_type, working_inventory, requirements)
                        collected_materials = self._merge_materials(collected_materials, materials)
                        working_inventory = self.update_inventory(working_inventory, materials)
                    
                    self.materials_collected = collected_materials.copy()
                    logger.debug(f"Punt de graella {current_pos}: total col·lectat {collected_materials}")

                    if requirements and self.validate_requirements(working_inventory, requirements):
                        logger.info("Requeriments assolits, aturant cerca en graella")
                        self.materials_collected = collected_materials.copy()
                        return collected_materials
        
        logger.info(f"Cerca en graella completada. Blocs minats: {self.blocks_mined}")
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

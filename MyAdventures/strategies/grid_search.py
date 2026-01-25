# Estratègia de cerca en graella per a mineria
from .strategy_base import MiningStrategy
from typing import Dict, Tuple, Optional
import logging
import time

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
             inventory: Dict = None, requirements: Dict = None, mc_lock=None) -> Dict:
        """
        Executar mineria basada en graella a través d'una regió cúbica.
        
        Args:
            mc: Instància de Minecraft
            start_pos: Posició inicial (x, y, z)
            inventory: Diccionari d'inventari actual amb requeriments
            mc_lock: Lock per sincronitzar accés a mc (opcional)
            
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
        
        # Mapejar IDs a tipus per a consultar rapidament
        from mcpi import block as mcblock
        id_to_type = {
            mcblock.STONE.id: "stone",
            mcblock.DIRT.id: "dirt",
            mcblock.GRASS.id: "dirt",
            mcblock.SAND.id: "sand"
        }
        
        check_counter = 0

        # Iterar a través dels punts de la graella
        for x_offset in range(0, self.grid_size, self.grid_spacing):
            if self.is_stopped:
                break
            while self.is_paused:
                pass
            
            for z_offset in range(0, self.grid_size, self.grid_spacing):
                if self.is_stopped:
                    break
                
                # Escaneig de baix a dalt: -3, -2, -1, 0, 1, 2, 3
                for y_offset in range(-(self.grid_size - 1), self.grid_size, self.grid_spacing):
                    if self.is_stopped:
                        break
                    
                    current_pos = (
                        start_x + x_offset,
                        start_y + y_offset,
                        start_z + z_offset
                    )
                    self.current_position = current_pos
                    
                    # Agafar ID de block una vegada per pos
                    existing_id = 0
                    if mc:
                        if mc_lock: mc_lock.acquire()
                        try:
                            existing_id = mc.getBlock(current_pos[0], current_pos[1], current_pos[2])
                        finally:
                            if mc_lock: mc_lock.release()

                    # Comprovar salt d'aire
                    # Si trobem aire per sobre del nivell inicial dels peus, assumim cel obert i deixem d'escanejar aquesta columna cap amunt
                    if existing_id == 0:
                        if y_offset >= 0:
                            logger.debug(f"Aire tobat a {current_pos} (Level {y_offset}). Saltant a la següent columna")
                            break # Saltar les Y superiors en aquesta columna
                        else:
                            # Aire trobat sota (cova?), continuar escanejant cap amunt
                            pass
                    
                    # Minar si block coincideix amb requeriments
                    block_type = id_to_type.get(existing_id)
                    
                    if block_type:
                        
                        # Executar mineria (destruir bloc)
                        
                        materials_yield = self.BLOCK_YIELDS.get(block_type, {}).copy()
                        
                        if mc:
                            try:
                                if mc_lock: mc_lock.acquire()
                                try:
                                    mc.setBlock(current_pos[0], current_pos[1], current_pos[2], 0) # Aire
                                    self.blocks_mined += 1
                                    logger.info(f"Minat {block_type} a {current_pos}")
                                finally:
                                    if mc_lock: mc_lock.release()
                            except Exception as e:
                                logger.error(f"Error posant block {current_pos}: {e}")
                                continue
                        
                        # Filtrar materials: només afegim a l'inventari el que REALMENT necessitem
                        useful_materials = {}
                        if requirements:
                            for mat, qty in materials_yield.items():
                                needed = requirements.get(mat, 0)
                                current = working_inventory.get(mat, 0)
                                if current < needed:
                                    useful_materials[mat] = qty
                        else:
                            useful_materials = materials_yield # Si no hi ha requirements, ho guardem tot (o res? assumim mode requirements)

                        collected_materials = self._merge_materials(collected_materials, useful_materials)
                        working_inventory = self.update_inventory(working_inventory, useful_materials)

                    
                    self.materials_collected = collected_materials.copy()
                    
                    # Sleep optimitzat: cedir el control cada 10 comprovacions en lloc de cada 1
                    check_counter += 1
                    if check_counter % 10 == 0:
                        time.sleep(0.01)

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

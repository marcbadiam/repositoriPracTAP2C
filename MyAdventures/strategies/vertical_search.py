# Estratègia de cerca vertical per a mineria
from .strategy_base import MiningStrategy
from typing import Dict, Tuple
import logging
from mcpi import block as mcblock

logger = logging.getLogger(__name__)


class VerticalSearchStrategy(MiningStrategy):
    """
    Des del punt d'anchor, mina verticalment cap avall fins a la profunditat màxima.
    """

    ID_TO_NAME = {
        mcblock.STONE.id: "stone",
        mcblock.DIRT.id: "dirt",
        mcblock.GRASS.id: "grass",
        mcblock.SAND.id: "sand",
        mcblock.GRAVEL.id: "gravel",
        mcblock.WOOD.id: "wood",
        mcblock.WOOD_PLANKS.id: "wood_planks",
        mcblock.COAL_ORE.id: "coal_ore",
        mcblock.IRON_ORE.id: "iron_ore",
        mcblock.GOLD_ORE.id: "gold_ore",
        mcblock.DIAMOND_ORE.id: "diamond_ore",
        mcblock.REDSTONE_ORE.id: "redstone_ore",
        mcblock.LAPIS_LAZULI_ORE.id: "lapis_ore",
        mcblock.COBBLESTONE.id: "cobblestone",
        mcblock.SANDSTONE.id: "sandstone",
    }

    def __init__(self):
        """
        Inicialitzar estratègia de mina vertical.
        """
        super().__init__()
        self.current_depth = None

    def mine(
        self,
        mc=None,
        start_pos: Tuple[int, int, int] = None,
        inventory: Dict = None,
        requirements: Dict = None,
        mc_lock=None,
    ) -> Dict:
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

        logger.info(f"Iniciant mineria per cerca vertical a {start_pos}")

        # Perforar cap avall des de la posició inicial
        current_y = start_y

        # El bucle s'atura si arribem a Y=6 (definit dins del bucle)
        while current_y >= 2:
            if current_y == 6:
                logger.info("Y=6. Aturant cerca vertical i workflow.")
                self.is_stopped = True
                break

            if self.is_stopped:
                logger.info(f"Cerca vertical aturat a profunditat {current_y}")
                break

            while self.is_paused:
                pass

            self.current_depth = current_y
            self.current_position = (start_x, current_y, start_z)

            if mc:
                block_id = 0
                try:
                    if mc_lock:
                        mc_lock.acquire()
                    try:
                        block_id = mc.getBlock(start_x, current_y, start_z)
                    finally:
                        if mc_lock:
                            mc_lock.release()
                except Exception as e:
                    logger.error(f"Error obtenint bloc a {self.current_position}: {e}")
                    block_id = 0

                if block_id != 0:
                    try:
                        if mc_lock:
                            mc_lock.acquire()
                        try:
                            mc.setBlock(start_x, current_y, start_z, 0)  # Posar a AIR
                            self.blocks_mined += 1
                        finally:
                            if mc_lock:
                                mc_lock.release()
                    except Exception as e:
                        logger.error(
                            f"Error minant bloc a {self.current_position}: {e}"
                        )

                    # Identificar i recollir si és útil
                    block_name = self.ID_TO_NAME.get(block_id)

                    if block_name:
                        materials_yield = self.BLOCK_YIELDS.get(block_name, {}).copy()

                        # Filtrar si és necessari segons requeriments
                        useful_materials = {}
                        if requirements:
                            for mat, qty in materials_yield.items():
                                needed = requirements.get(mat, 0)
                                current = working_inventory.get(mat, 0)
                                # Si el necessitem (encara no tenim prous), el recollim
                                if current < needed:
                                    useful_materials[mat] = qty
                        else:
                            useful_materials = materials_yield

                        # Actualitzar inventory i materials recollits
                        if useful_materials:
                            collected_materials = self._merge_materials(
                                collected_materials, useful_materials
                            )
                            working_inventory = self.update_inventory(
                                working_inventory, useful_materials
                            )
                            logger.debug(
                                f"Profunditat {current_y}: Recollit {useful_materials} de {block_name}"
                            )

            self.materials_collected = collected_materials.copy()

            if requirements and self.validate_requirements(
                working_inventory, requirements
            ):
                logger.info("Requeriments assolits, aturant cerca vertical")
                return collected_materials

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

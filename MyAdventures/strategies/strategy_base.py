# Classe base per a estratègies de mineria
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
from mcpi import block as mcblock
import logging

logger = logging.getLogger(__name__)


class MiningStrategy(ABC):
    """Classe base per a totes les estratègies de mineria.

    Gestiona operacions comunes de mineria amb suport per a gestió d'inventari,
    seguiment del progrés i comandes de control (pausa, reprendre, aturar).
    """

    # Blocs minables i els seus rendiments de recursos
    BLOCK_YIELDS = {
        "stone": {"stone": 1},
        "dirt": {"dirt": 1},
        "grass": {"dirt": 1},
        "sand": {"sand": 1},
        "gravel": {"gravel": 1},
        "wood": {"wood": 1},
        "wood_planks": {"wood_planks": 1},
        "coal_ore": {"coal_ore": 1},
        "iron_ore": {"iron_ore": 1},
        "gold_ore": {"gold_ore": 1},
        "diamond_ore": {"diamond_ore": 1},
        "redstone_ore": {"redstone_ore": 1},
        "lapis_ore": {"lapis_ore": 1},
        "cobblestone": {"cobblestone": 1},
        "sandstone": {"sandstone": 1}
    }

    def __init__(self):
        """Inicialitza l'estratègia amb seguiment d'estat."""
        self.is_paused = False
        self.is_stopped = False
        self.current_position = None
        self.materials_collected = {}
        self.blocks_mined = 0
        self.start_time = None

    @abstractmethod
    def mine(
        self,
        mc,
        start_pos: Tuple[int, int, int],
        inventory: Dict,
        requirements: Optional[Dict] = None,
        mc_lock=None,
    ) -> Dict:
        """
        Executar estratègia de mineria.

        Args:
            mc: Instància de Minecraft
            start_pos: Posició inicial (x, y, z)
            inventory: Diccionari d'inventari actual amb requeriments
            mc_lock: Lock per sincronitzar accés a mc (opcional)

        Returns:
            dict: Materials col·lectats {material: quantitat}
        """
        pass

    def validate_requirements(self, inventory: Dict, requirements: Dict) -> bool:
        """
        Validar si l'inventari actual compleix amb els requeriments.

        Args:
            inventory: Inventari actual
            requirements: Diccionari de materials requerits

        Returns:
            bool: Cert si tots els requeriments es compleixen
        """
        if not requirements:
            return True

        for material, quantity in requirements.items():
            if inventory.get(material, 0) < quantity:
                return False
        return True

    def update_inventory(self, inventory: Dict, collected: Dict) -> Dict:
        """
        Actualitzar inventari amb materials col·lectats.

        Args:
            inventory: Inventari actual
            collected: Materials col·lectats en aquesta operació

        Returns:
            dict: Inventari actualitzat
        """
        updated = inventory.copy()
        for material, quantity in collected.items():
            updated[material] = updated.get(material, 0) + quantity
        return updated

    def mine_block(
        self,
        mc,
        position: Tuple[int, int, int],
        block_type: str,
        inventory: Dict,
        requirements: Optional[Dict] = None,
        mc_lock=None,
    ) -> Dict:
        """
        Minar un bloc única i afegir materials a l'inventari.

        Args:
            mc: Instància de Minecraft
            position: Posició del bloc (x, y, z)
            block_type: Tipus de bloc a minar
            inventory: Inventari actual
            mc_lock: Threading lock per sincronitzar accés al socket

        Returns:
            dict: Materials extrets d'aquest bloc
        """
        if self.is_stopped:
            return {}

        # Verifica si el bloc té rendiments definits
        if block_type not in self.BLOCK_YIELDS:
            logger.warning(f"Tipus de bloc desconegut: {block_type}")
            return {}

        # Comprovar que el bloc existent coincideix amb el tipus esperat abans de minar
        if mc:
            try:
                if mc_lock:
                    mc_lock.acquire()
                try:
                    existing_id = mc.getBlock(position[0], position[1], position[2])
                    # Debug temporal
                    if existing_id != 0:
                        logger.info(
                            f"DEBUG: Trobat Block amb ID {existing_id} a {position} (Busquem: {block_type})"
                        )
                    else:
                        # Logejar aire "ocasionalment" per demostrar que estem escanejant
                        if (position[0] + position[1] + position[2]) % 10 == 0:
                            logger.info(f"DEBUG: AIRE trobat a {position}")
                finally:
                    if mc_lock:
                        mc_lock.release()
            except Exception as e:
                logger.error(f"Error obtenint bloc a {position}: {e}")
                return {}

            allowed_ids = {
                "stone": {mcblock.STONE.id},
                "dirt": {mcblock.DIRT.id, mcblock.GRASS.id},
                "sand": {mcblock.SAND.id},
                "sandstone": {mcblock.SANDSTONE.id},
            }.get(block_type, set())

            if existing_id not in allowed_ids:
                return {}

        # Extreure materials d'aquest bloc
        materials = self.BLOCK_YIELDS[block_type].copy()

        # Intentar trencar el bloc si la instància de minecraft està disponible
        if mc:
            try:
                if mc_lock:
                    mc_lock.acquire()
                try:
                    mc.setBlock(position[0], position[1], position[2], 0)  # Aire
                    self.blocks_mined += 1
                finally:
                    if mc_lock:
                        mc_lock.release()
            except Exception as e:
                logger.error(f"Error minant bloc a {position}: {e}")

        return materials

    def handle_pause(self) -> None:
        """Pausar operacions de mineria."""
        self.is_paused = True
        logger.info(f"Mineria de {self.get_name()} pausada")

    def handle_resume(self) -> None:
        """Reprendre operacions de mineria."""
        self.is_paused = False
        logger.info(f"Mineria de {self.get_name()} represa")

    def handle_stop(self) -> None:
        """Aturar operacions de mineria."""
        self.is_stopped = True
        logger.info(f"Mineria de {self.get_name()} aturat")

    def reset(self) -> None:
        """Resetejar estat de l'estratègia."""
        self.is_paused = False
        self.is_stopped = False
        self.blocks_mined = 0
        self.materials_collected = {}
        logger.info(f"Estratègia {self.get_name()} resetejada")

    def get_name(self) -> str:
        """Retorna el nom de l'estratègia."""
        return self.__class__.__name__

    def get_status(self) -> Dict:
        """
        Obtenir estatus actual de mineria.

        Returns:
            dict: Informació d'estatus incloent posició, materials col·lectats, blocs minats
        """
        return {
            "strategy": self.get_name(),
            "position": self.current_position,
            "materials_collected": self.materials_collected.copy(),
            "blocks_mined": self.blocks_mined,
            "is_paused": self.is_paused,
            "is_stopped": self.is_stopped,
        }

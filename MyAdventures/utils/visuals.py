from typing import Tuple

try:
    from mcpi import block as mcblock
except Exception:  # fallback if import fails at edit time
    mcblock = None

def place_marker_block(mc, x: int, y: int, z: int, color_data: int = 11):
    """Col·locar un bloc de llana de color a la ubicació donada. Per defecte: blau (data=11)."""
    if mcblock and hasattr(mcblock, "WOOL"):
        mc.setBlock(x, y, z, mcblock.WOOL.id, color_data)
    else:
        # fallback to stone if wool constant is unavailable
        mc.setBlock(x, y, z, 1)  # 1 = stone on many mcpi builds

def mark_bot(mc, x: int, y: int, z: int, wool_color: int, label: str):
    """Col·locar un bloc marcador i publicar al xat."""
    place_marker_block(mc, x, y, z, wool_color)
    try:
        mc.postToChat(f"[{label}] marcador col·locat en ({x},{y},{z}).")
    except Exception:
        pass

def place_chest(mc, x: int, y: int, z: int, facing: int = 3):
    """Col·locar un únic cofre a les coordenades. facing: 2/3/4/5 = NESW dades típiques."""
    if mcblock and hasattr(mcblock, "CHEST"):
        mc.setBlock(x, y, z, mcblock.CHEST.id, facing)
    else:
        mc.setBlock(x, y, z, 54, facing)

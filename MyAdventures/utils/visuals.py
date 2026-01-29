from typing import Tuple, Optional

try:
    from mcpi import block as mcblock
except Exception:  # per si el import falla
    mcblock = None

def mark_bot(mc, x: int, y: int, z: int, wool_color: int = 11, label: Optional[str] = None):
    """
    Col·locar un bloc de llana de color a la ubicació donada.
    Si s'especifica el label, també es publica un missatge al xat.
    """

    mc.setBlock(x, y, z, mcblock.WOOL.id, wool_color)

    if label:
        try:
            mc.postToChat(f"[{label}] marcador col·locat en ({x},{y},{z}).")
        except Exception:
            pass

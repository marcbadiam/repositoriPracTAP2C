from abc import ABC, abstractmethod
import csv
import os
import logging
from utils.validators import es_fila_valida

logger = logging.getLogger(__name__)

class BuildPlan(ABC):
    """Classe base per a tots els plans de construcció."""
    
    @property
    @abstractmethod
    def name(self):
        """Nom únic del pla."""
        pass

    @property
    @abstractmethod
    def bom(self):
        """Llista de materials necessaris (Bill of Materials)."""
        pass

    @abstractmethod
    def generate(self, x, y, z):
        """Genera la llista de blocs a construir relatius a (x, y, z)."""
        pass

    def load_from_csv(self, filename, x, y, z):
        """Mètode d'ajuda per carregar plans des de CSV."""

        csv_path = os.path.join("data", "plans", filename)
        
        def to_absolute_block(row):
            dx, dy, dz = int(row["dx"]), int(row["dy"]), int(row["dz"])
            material = row["material"]
            return (x + dx, y + dy, z + dz, material)

        with open(csv_path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            valid_rows = filter(es_fila_valida, reader)
            return list(map(to_absolute_block, valid_rows))

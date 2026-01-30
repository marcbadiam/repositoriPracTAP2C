# Conjunt de proves per estratègies de mineria
import unittest
from strategies.strategy_base import MiningStrategy
from strategies.grid_search import GridSearchStrategy
from strategies.vertical_search import VerticalSearchStrategy


class TestMiningStrategies(unittest.TestCase):
    """Prova totes les implementacions d'estratègies de mineria."""
    
    def test_strategy_inheritance(self):
        """Prova que totes les estratègies hereten de MiningStrategy."""
        strategies = [
            GridSearchStrategy(),
            VerticalSearchStrategy(),
        ]
        
        for strategy in strategies:
            self.assertIsInstance(strategy, MiningStrategy)
    
    
    def test_vertical_search_returns_materials(self):
        """Prova que VerticalSearchStrategy retorna els tipus de materials esperats."""
        strategy = VerticalSearchStrategy()
        result = strategy.mine(start_pos=(0, 0, 0))
        
        self.assertIsInstance(result, dict)
        # self.assertIn('iron', result)
        # self.assertIn('wood', result)
        self.assertIn('stone', result)
    
    def test_strategy_get_name(self):
        """Prova l'obtenció del nom de l'estratègia."""
        strategy = GridSearchStrategy()
        name = strategy.get_name()
        
        self.assertEqual(name, "GridSearchStrategy")
    



if __name__ == "__main__":
    unittest.main()

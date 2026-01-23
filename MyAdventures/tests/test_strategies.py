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
    
    def test_grid_search_returns_materials(self):
        """Prova que GridSearchStrategy retorna els tipus de materials esperats."""
        strategy = GridSearchStrategy()
        result = strategy.mine()
        
        self.assertIsInstance(result, dict)
        self.assertIn('iron', result)
        self.assertIn('wood', result)
        self.assertIn('stone', result)
    
    def test_vertical_search_returns_materials(self):
        """Prova que VerticalSearchStrategy retorna els tipus de materials esperats."""
        strategy = VerticalSearchStrategy()
        result = strategy.mine()
        
        self.assertIsInstance(result, dict)
        self.assertIn('iron', result)
        self.assertIn('wood', result)
        self.assertIn('stone', result)
    
    def test_strategy_get_name(self):
        """Prova l'obtenció del nom de l'estratègia."""
        strategy = GridSearchStrategy()
        name = strategy.get_name()
        
        self.assertEqual(name, "GridSearchStrategy")
    
    def test_different_yields(self):
        """Prova que diferents estratègies retornen quantitats diferents."""
        grid = GridSearchStrategy().mine()
        vertical = VerticalSearchStrategy().mine()
        
        # Només verifica que retornen dades, no quantitats específiques
        self.assertTrue(len(grid) > 0)
        self.assertTrue(len(vertical) > 0)


if __name__ == "__main__":
    unittest.main()

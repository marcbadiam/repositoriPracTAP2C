# Conjunt de proves per utilitats de programació funcional
import unittest
from utils.functional import (
    find_flat_zones,
    calculate_total_resources,
    extract_elevations,
    calculate_terrain_stats,
    summarize_mining_results,
    compose,
    filter_by_resource
)


class TestFunctionalUtilities(unittest.TestCase):
    """Prova les utilitats de programació funcional."""
    
    def test_find_flat_zones(self):
        """Prova el filtratge de zones planes."""
        terrain = [
            {"x": 0, "z": 0, "elevation": 10, "variance": 1.0},
            {"x": 1, "z": 0, "elevation": 15, "variance": 5.0},
            {"x": 2, "z": 0, "elevation": 11, "variance": 1.5}
        ]
        
        flat_zones = find_flat_zones(terrain, max_variance=2.0)
        self.assertEqual(len(flat_zones), 2)
    
    def test_calculate_total_resources(self):
        """Prova l'agregació de recursos utilitzant reduce."""
        inventories = [
            {"iron": 5, "wood": 10},
            {"iron": 3, "stone": 7},
            {"wood": 5, "stone": 3}
        ]
        
        total = calculate_total_resources(inventories)
        
        self.assertEqual(total["iron"], 8)
        self.assertEqual(total["wood"], 15)
        self.assertEqual(total["stone"], 10)
    
    def test_extract_elevations(self):
        """Prova l'extracció d'elevacions utilitzant map."""
        terrain = [
            {"x": 0, "z": 0, "elevation": 10},
            {"x": 1, "z": 0, "elevation": 15},
            {"x": 2, "z": 0, "elevation": 11}
        ]
        
        elevations = extract_elevations(terrain)
        
        self.assertEqual(elevations, [10, 15, 11])
    
    def test_calculate_terrain_stats(self):
        """Prova el càlcul complet d'estadístiques de terreny."""
        terrain = [
            {"x": 0, "z": 0, "elevation": 10, "variance": 1.0},
            {"x": 1, "z": 0, "elevation": 15, "variance": 1.5},
            {"x": 2, "z": 0, "elevation": 11, "variance": 1.2}
        ]
        
        stats = calculate_terrain_stats(terrain)
        
        self.assertEqual(stats["count"], 3)
        self.assertAlmostEqual(stats["avg_elevation"], 12.0)
        self.assertEqual(stats["min_elevation"], 10)
        self.assertEqual(stats["max_elevation"], 15)
    
    def test_summarize_mining_results(self):
        """Prova el resum de resultats de mineria."""
        sessions = [
            {"session_id": 1, "inventory": {"iron": 5, "wood": 10}},
            {"session_id": 2, "inventory": {"stone": 7}},
            {"session_id": 3, "inventory": {}}
        ]
        
        summary = summarize_mining_results(sessions)
        
        self.assertEqual(summary["total_sessions"], 3)
        self.assertEqual(summary["successful_sessions"], 2)
        self.assertEqual(summary["total_resources"]["iron"], 5)
        self.assertAlmostEqual(summary["success_rate"], 2/3)
    
    def test_compose_functions(self):
        """Prova la composició de funcions."""
        add_one = lambda x: x + 1
        multiply_two = lambda x: x * 2
        
        composed = compose(multiply_two, add_one)
        result = composed(5)  # (5 + 1) * 2 = 12
        
        self.assertEqual(result, 12)
    
    def test_filter_by_resource(self):
        """Prova la funció de filtre d'ordre superior."""
        inventories = [
            {"iron": 5, "wood": 10},
            {"stone": 7},
            {"iron": 3, "stone": 2}
        ]
        
        has_iron = filter_by_resource("iron")
        iron_inventories = list(filter(has_iron, inventories))
        
        self.assertEqual(len(iron_inventories), 2)
    
    def test_empty_terrain_data(self):
        """Prova la gestió de dades de terreny buides."""
        stats = calculate_terrain_stats([])
        
        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["avg_elevation"], 0)


if __name__ == "__main__":
    unittest.main()

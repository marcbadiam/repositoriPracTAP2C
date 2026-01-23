# Conjunt de proves per descobriment reflexiu
import unittest
from utils.discovery import discover_classes, discover_strategies, discover_agents
from strategies.strategy_base import MiningStrategy
from agents.base_agent import BaseAgent


class TestReflectiveDiscovery(unittest.TestCase):
    """Prova el descobriment automàtic d'agents i estratègies."""
    
    def test_discover_strategies(self):
        """Prova el descobriment automàtic d'estratègies."""
        strategies = discover_strategies()
        

        self.assertGreaterEqual(len(strategies), 3)
        

        for name, strategy_class in strategies.items():
            self.assertTrue(issubclass(strategy_class, MiningStrategy))
    
    def test_discover_agents(self):
        """Prova el descobriment automàtic d'agents."""
        agents = discover_agents()
        
        # Ha de trobar almenys 3 agents: Explorer, Miner, Builder
        self.assertGreaterEqual(len(agents), 3)
        
        # Comprova que les classes descobertes són subclasses de BaseAgent
        for name, agent_class in agents.items():
            self.assertTrue(issubclass(agent_class, BaseAgent))
    
    def test_strategy_names(self):
        """Prova que els noms de les estratègies són correctes."""
        strategies = discover_strategies()
        
        strategy_names = set(strategies.keys())
        expected_names = {"GridSearchStrategy", "VerticalSearchStrategy", "VeinSearchStrategy"}
        
        # Totes les estratègies esperades han de ser descobertes
        self.assertTrue(expected_names.issubset(strategy_names))
    
    def test_agent_names(self):
        """Prova que els noms dels agents són correctes."""
        agents = discover_agents()
        
        agent_names = set(agents.keys())
        expected_names = {"ExplorerBot", "MinerBot", "BuilderBot"}
        
        # Tots els agents esperats han de ser descoberts
        self.assertTrue(expected_names.issubset(agent_names))
    
    def test_discovered_strategies_instantiable(self):
        """Prova que les estratègies descobertes es poden instanciar."""
        strategies = discover_strategies()
        
        for name, strategy_class in strategies.items():
            try:
                instance = strategy_class()
                self.assertIsInstance(instance, MiningStrategy)
            except Exception as e:
                self.fail(f"No s'ha pogut instanciar {name}: {e}")


if __name__ == "__main__":
    unittest.main()

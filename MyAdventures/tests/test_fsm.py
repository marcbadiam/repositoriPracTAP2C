# Prova bàsica per FSM i agents
import unittest
from agents.base_agent import BaseAgent, AgentState

class DummyAgent(BaseAgent):
    def perceive(self):
        pass
    def decide(self):
        pass
    def act(self):
        pass

class TestFSM(unittest.TestCase):
    def test_state_transitions(self):
        agent = DummyAgent("TestAgent")
        agent.set_state(AgentState.RUNNING)
        self.assertEqual(agent.state, AgentState.RUNNING)
        agent.set_state(AgentState.PAUSED)
        self.assertEqual(agent.state, AgentState.PAUSED)
        agent.set_state(AgentState.ERROR)
        self.assertEqual(agent.state, AgentState.ERROR)

if __name__ == "__main__":
    unittest.main()

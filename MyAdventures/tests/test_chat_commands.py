import unittest
from utils.chat_commands import ChatCommandHandler, create_default_handlers
from agents.base_agent import BaseAgent, AgentState


class DummyAgent(BaseAgent):
    """Agent de prova simple."""

    def perceive(self):
        pass

    def decide(self):
        pass

    def act(self):
        pass

    def pause(self):
        self.set_state(AgentState.PAUSED)

    def resume(self):
        self.set_state(AgentState.RUNNING)

    def stop(self):
        self.set_state(AgentState.STOPPED)


class TestChatCommands(unittest.TestCase):
    """Prova l'anàlisi i gestió d'ordres de xat."""

    def setUp(self):
        """Configura el gestor de prova."""
        self.handler = ChatCommandHandler()

    def test_parse_simple_command(self):
        """Prova l'anàlisi d'una ordre simple."""
        cmd = self.handler.parse_command("-agent help")

        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command, "agent help")
        self.assertEqual(len(cmd.args), 0)

    def test_parse_command_with_args(self):
        """Prova l'anàlisi d'una ordre amb arguments."""
        cmd = self.handler.parse_command("-explorer start x=10 z=20 range=50")

        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command, "explorer start")
        self.assertEqual(cmd.args["x"], 10)
        self.assertEqual(cmd.args["z"], 20)
        self.assertEqual(cmd.args["range"], 50)

    def test_parse_command_string_args(self):
        """Prova l'anàlisi d'una ordre amb arguments de text."""
        cmd = self.handler.parse_command("-miner set strategy vertical")

        self.assertIsNotNone(cmd)
        # L'ordre inclou tots els tokens que no són arguments
        self.assertEqual(cmd.command, "miner set strategy vertical")

    def test_parse_non_command(self):
        """Prova que els textos que no són ordres retornen None."""
        cmd = self.handler.parse_command("hello world")

        self.assertIsNone(cmd)

    def test_register_and_handle_command(self):
        """Prova el registre i gestió d'una ordre."""
        executed = []

        def test_handler(args):
            executed.append(True)

        self.handler.register("test command", test_handler)
        result = self.handler.handle_command("-test command")

        self.assertTrue(result)
        self.assertEqual(len(executed), 1)

    def test_handle_unknown_command(self):
        """Prova la gestió d'ordres desconegudes."""
        result = self.handler.handle_command("-unknown command")

        self.assertFalse(result)

    def test_create_default_handlers(self):
        """Prova la creació de gestors d'ordres per defecte."""
        agent = DummyAgent("TestAgent")
        agents = {"TestAgent": agent}

        handler = create_default_handlers(agents, None, None)

        # Comprova que els gestors comuns estan registrats
        self.assertIn("agent help", handler.handlers)
        self.assertIn("agent status", handler.handlers)

    def test_agent_control_commands(self):
        """Prova el control d'agents mitjançant ordres."""
        agent = DummyAgent("TestAgent")

        # Prova pausa
        agent.set_state(AgentState.RUNNING)
        agent.handle_command("pause", {})
        self.assertEqual(agent.state, AgentState.PAUSED)

        # Prova reprendre
        agent.handle_command("resume", {})
        self.assertEqual(agent.state, AgentState.RUNNING)

        # Prova aturar
        agent.handle_command("stop", {})
        self.assertEqual(agent.state, AgentState.STOPPED)


if __name__ == "__main__":
    unittest.main()

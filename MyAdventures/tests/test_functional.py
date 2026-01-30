import unittest
from unittest.mock import patch, mock_open
import json
from utils.functional import (
    parse_log_line,
    load_logs,
    filter_logs,
    count_logs_by_level,
    get_agent_activity
)

class TestFunctionalLogAnalysis(unittest.TestCase):
    """Test de les utilitats de programació funcional per anàlisi de logs."""
    
    def test_parse_log_line_valid(self):
        """Prova el parseig de línies de log vàlides."""
        line = '{"level": "INFO", "message": "Test"}'
        result = parse_log_line(line)
        self.assertEqual(result["level"], "INFO")
        self.assertEqual(result["message"], "Test")
        
    def test_parse_log_line_invalid(self):
        """Prova la gestió d'errors amb línies malformades."""
        line = 'INVALID JSON'
        result = parse_log_line(line)
        self.assertEqual(result["level"], "ERROR")
        self.assertEqual(result["message"], "Log line malformed")

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"level": "INFO"}\n{"level": "ERROR"}')
    def test_load_logs(self, mock_file, mock_exists):
        """Prova de carrega de logs (lazy)"""
        mock_exists.return_value = True
        
        logs_gen = load_logs("dummy.log")
        logs = list(logs_gen)
        
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0]["level"], "INFO")
        self.assertEqual(logs[1]["level"], "ERROR")

    def test_filter_logs(self):
        """Prova el filter de logs."""
        data = [
            {"level": "INFO", "logger": "Bot1"},
            {"level": "ERROR", "logger": "Bot1"},
            {"level": "INFO", "logger": "Bot2"}
        ]
        
        # Filter de INFO
        infos = list(filter_logs(data, level="INFO"))
        self.assertEqual(len(infos), 2)
        
        # Filter de Bot1 i INFO
        bot1_infos = list(filter_logs(data, level="INFO", logger="Bot1"))
        self.assertEqual(len(bot1_infos), 1)
        self.assertEqual(bot1_infos[0]["logger"], "Bot1")

    def test_count_logs_by_level(self):
        """Prova el recompte utilitzant reduce."""
        data = [
            {"level": "INFO"},
            {"level": "INFO"},
            {"level": "ERROR"},
            {"level": "DEBUG"}
        ]
        
        counts = count_logs_by_level(data)
        self.assertEqual(counts["INFO"], 2)
        self.assertEqual(counts["ERROR"], 1)
        self.assertEqual(counts["DEBUG"], 1)

    def test_get_agent_activity(self):
        """Prova nLogs per agent."""
        data = [
            {"logger": "ExplorerBot"},
            {"logger": "MinerBot"},
            {"logger": "ExplorerBot"}
        ]
        
        activity = get_agent_activity(data)
        self.assertEqual(activity["ExplorerBot"], 2)
        self.assertEqual(activity["MinerBot"], 1)

if __name__ == "__main__":
    unittest.main()

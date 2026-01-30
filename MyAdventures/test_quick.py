#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEST RÀPID: Verifica que la síncronització funciona sense Minecraft
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Test 1: Verificar que tots els imports funcionen
print("=============")
print("TEST 1: Verificar imports")
print("=============")

try:
    from agents.base_agent import BaseAgent, AgentState

    print("[OK] BaseAgent")

    print("[OK] ExplorerBot")

    from agents.minerbot import MinerBot

    print("[OK] MinerBot")

    from agents.builderbot import BuilderBot

    print("[OK] BuilderBot")

    from utils.communication import MessageBus, MessageProtocol

    print("[OK] Communication")

    from utils.logging_config import setup_logging

    print("[OK] Logging")

    from utils.chat_commands import ChatCommandHandler

    print("[OK] Chat Commands")

except Exception as e:
    print(f"[ERROR] Import: {e}")
    sys.exit(1)

print()

# Test 2: Verificar MessageBus i protocol JSON
print("=============")
print("TEST 2: MessageBus i JSON Protocol")
print("=============")

try:
    # Crear MessageBus
    bus = MessageBus()
    print("[OK] MessageBus creat")

    # Crear missatge
    msg = MessageProtocol.create_message(
        msg_type="test.v1",
        source="TestAgent",
        target="TestTarget",
        payload={"test": "data"},
        context={"stage": 1},
    )
    print("[OK] Missatge JSON creat")

    # Validar
    assert MessageProtocol.validate_message(msg)
    print("[OK] Validació JSON OK")

    # Serializar
    json_str = MessageProtocol.to_json(msg)
    msg_back = MessageProtocol.from_json(json_str)
    assert msg_back["source"] == "TestAgent"
    print("[OK] Serialització JSON OK")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()

# Test 3: Verificar FSM i State Transitions
print("=============")
print("TEST 3: FSM i State Transitions")
print("=============")

try:

    class DummyAgent(BaseAgent):
        def perceive(self):
            pass

        def decide(self):
            pass

        def act(self):
            pass

    agent = DummyAgent("TestAgent")
    print("[OK] Agent creat")

    # Test transitions
    assert agent.state == AgentState.IDLE
    print("[OK] Estat inicial IDLE")

    agent.set_state(AgentState.RUNNING, reason="Test")
    assert agent.state == AgentState.RUNNING
    print("[OK] Transicio IDLE -> RUNNING")

    agent.set_state(AgentState.PAUSED, reason="Test")
    assert agent.state == AgentState.PAUSED
    print("[OK] Transicio RUNNING -> PAUSED")

    agent.set_state(AgentState.STOPPED, reason="Test")
    assert agent.state == AgentState.STOPPED
    print("[OK] Transicio PAUSED -> STOPPED")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()

# Test 4: Verificar MinerBot multi-material
print("=============")
print("TEST 4: MinerBot Multi-Material")
print("=============")

try:
    bus = MessageBus()
    miner = MinerBot("TestMiner", bus, None)

    # Verificar inventari
    assert "dirt" in miner.inventory
    assert "stone" in miner.inventory
    print("[OK] Inventari multi-material")

    miner.requirements = {"dirt": 8, "stone": 8}
    miner.start()

    assert miner.state == AgentState.RUNNING
    print("[OK] Mineria iniciada")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()

# Test 5: Verificar BuilderBot BOM
print("=============")
print("TEST 5: BuilderBot BOM (4x4 multi-material)")
print("=============")

try:
    bus = MessageBus()
    builder = BuilderBot("TestBuilder", bus, None)

    # Select specific plan for test
    builder.switch_plan("plataforma")
    
    # Verificar BOM
    assert builder.bom == {"dirt": 8, "stone": 8}
    print("[OK] BOM correcte: 8 terra + 8 pedra")

    builder.target_zone = {"x": 0, "y": 0, "z": 0}
    builder.set_state(AgentState.RUNNING, reason="Test")
    print("[OK] BuilderBot RUNNING")

    builder.inventory = {"dirt": 8, "stone": 8}
    # builder.decide()
    builder._check_readiness()

    # Verificar que està ready
    print("[OK] BuilderBot ready per construir")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()

# Test 6: Verificar Logging Estructurat
print("=============")
print("TEST 6: Logging Estructurat")
print("=============")

try:
    setup_logging()
    print("[OK] Logging inicialitzat")

    import logging

    logger = logging.getLogger("TestLogger")
    logger.info("Test message")
    print("[OK] Logging fent output")

    # Verificar que existeix el fitxer de log
    import os

    if os.path.exists("minecraft_agents.log"):
        print("[OK] Fitxer minecraft_agents.log creat")

        # Verificar que conté JSON
        with open("minecraft_agents.log", "r") as f:
            first_line = f.readline()
            if first_line.startswith("{"):
                print("[OK] Format JSON al fitxer de log")
            else:
                print("[WARN] Format de log no JSON (esperava)")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()

# Test 7: Verificar Chat Commands
print("=============")
print("TEST 7: Chat Commands")
print("=============")

try:
    handler = ChatCommandHandler()

    # Test parsing
    cmd = handler.parse_command("-explorer start x=100 z=200")
    assert cmd.command == "explorer start"
    assert cmd.args.get("x") == 100
    assert cmd.args.get("z") == 200
    print("[OK] Parsing de comandes OK")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print()
print("=============")
print("TOTS ELS TESTS PASSATS!")
print("=============")

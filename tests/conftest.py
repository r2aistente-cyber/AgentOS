"""Fixtures compartidos para toda la suite de tests.

No hay fixtures autouse a nivel de sesión aquí: cada suite de test es
responsable de su propio aislamiento porque testea código con formas muy
distintas (hub/*.py vs las copias por-agente en hub/templates/*).
Ver tests/template/conftest.py y tests/s8/conftest.py para el patrón usado
para testear hub/templates (inyecta agent_config falso + hub/templates en
sys.path).
"""
from __future__ import annotations

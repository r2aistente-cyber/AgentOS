# Conftest aislado para los tests de Sprint 8.
# No hereda las fixtures autouse del conftest.py raíz (que usan rutas Linux).
#
# El helper _classify en test_exec_security.py inyecta stubs de "tools" y
# "tools.registry" en sys.modules para poder importar exec_tools.py sin
# ejecutar su register(). Aquí limpiamos esos stubs después de cada test
# para que no contaminen los módulos reales de hub/templates importados
# por test_engine_llm.py y otras suites.
import sys
import pytest


@pytest.fixture(autouse=True)
def _cleanup_template_stubs():
    """Limpia los módulos stub inyectados por los helpers de s8 tras cada test."""
    yield
    # Eliminar stubs que _classify() puede dejar en sys.modules
    for key in list(sys.modules):
        if key in ("tools", "tools.registry", "_exec_tools_classify"):
            mod = sys.modules[key]
            # Solo borramos el stub si es un ModuleType básico sin __file__ real
            # (los módulos reales sí tienen __file__)
            if not getattr(mod, "__file__", None):
                sys.modules.pop(key, None)

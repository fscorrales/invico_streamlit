"""
Fixtures compartidas de los tests unitarios.

Convención del proyecto: los tests son **puros** (``DataFrame`` ->
``DataFrame``). No se toca la red, ni ``st.session_state``, ni Playwright.
Si un test necesitara I/O, debe marcarse explícitamente con
``@pytest.mark.integration`` (ver ``addopts`` en ``pyproject.toml``).
"""

from typing import Any, Dict

import pandas as pd
import pytest

# Columnas reales que consume ``filtrar_comprobantes_honorarios``. Se mantienen
# alineadas con el shape devuelto por ``get_siif_comprobantes_gtos_unified_cta_cte``
# para que los tests fallen si la función empieza a exigir una columna nueva.
COLUMNS = [
    "nro_comprobante",
    "cuit",
    "grupo",
    "partida",
    "cta_cte",
    "glosa",
]


# -------------------------------------------------
@pytest.fixture
def comprobante_factory() -> Any:
    """Factory de filas de comprobantes de gastos.

    Devuelve una fila que **sí** debe clasificarse como facturero; cada test
    rompe una sola condición mediante ``overrides`` para aislar el fallo.

    Returns:
        Callable que acepta overrides y devuelve un ``dict`` de fila.
    """

    def _build(**overrides: Any) -> Dict[str, Any]:
        row: Dict[str, Any] = {
            "nro_comprobante": "00123/26",
            "cuit": "30632351514",
            "grupo": "3",
            "partida": "308",
            "cta_cte": "130832-05",
            "glosa": "PAGO HONORARIOS FACTURERO",
        }
        row.update(overrides)
        return row

    return _build


# -------------------------------------------------
@pytest.fixture
def as_dataframe() -> Any:
    """Convierte filas en un ``DataFrame`` con las columnas reales.

    Returns:
        Callable que recibe filas y devuelve un ``pd.DataFrame``.
    """

    def _to_df(*rows: Dict[str, Any]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=COLUMNS)
        return pd.DataFrame(list(rows), columns=COLUMNS)

    return _to_df

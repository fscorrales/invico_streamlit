"""Tests de ``dataframe_a_registros`` (Control Otros Gastos).

``df.to_dict(orient="records")`` materializa los opcionales ausentes
como ``np.nan``; httpx serializa ese ``NaN`` (``json.dumps`` con
``allow_nan=True``) y el backend lo rechaza en la validación de
Pydantic, descartando filas del snapshot. Fue lo que dejó la hoja
``otros_gastos_siif`` sin el resto (``nro_fondo`` nulo) y la SGF sin
los cuit nulos, vaciando el cruce 1:1.

Ejecutar desde la raíz del proyecto:

    python -m unittest tests.test_dataframe_a_registros -v
"""

import json
import unittest
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.automation.analysis.control_otros_gastos import dataframe_a_registros


# --------------------------------------------------
class TestDataframeARegistros(unittest.TestCase):
    """La conversión DataFrame → registros debe ser JSON-safe."""

    # --------------------------------------------------
    def test_nan_convierte_en_none(self) -> None:
        """Los opcionales ausentes terminan como ``None``, no ``NaN``."""
        df = pd.DataFrame(
            [
                {
                    "nro_comprobante": "00048/26",
                    "nro_fondo": np.nan,
                    "importe": 45000.0,
                },
                {
                    "nro_comprobante": "00339/26",
                    "nro_fondo": "27",
                    "importe": 1000000.0,
                },
            ]
        )

        filas: List[Dict[str, Any]] = dataframe_a_registros(df)

        self.assertIsNone(filas[0]["nro_fondo"])
        self.assertEqual(filas[1]["nro_fondo"], "27")

    # --------------------------------------------------
    def test_salida_es_json_esticto_sin_nan(self) -> None:
        """La lista resultante sobrevive a un JSON estricto del back."""
        df = pd.DataFrame(
            [{"a": np.nan, "b": np.int64(5), "c": np.float64(1.5)}]
        )

        filas = dataframe_a_registros(df)

        # allow_nan=False es lo que exige back (y lo que rompía el POST)
        texto = json.dumps(filas, allow_nan=False)
        self.assertIn('"a": null', texto)
        self.assertIn('"b": 5', texto)
        self.assertIn('"c": 1.5', texto)

    # --------------------------------------------------
    def test_tipos_numpy_son_nativos(self) -> None:
        """numpy.int64/bool_ salen como int/bool de Python."""
        df = pd.DataFrame(
            [{"ejercicio": np.int64(2026), "es_pagado": np.bool_(True)}]
        )

        filas = dataframe_a_registros(df)

        self.assertIsInstance(filas[0]["ejercicio"], int)
        self.assertIsInstance(filas[0]["es_pagado"], bool)

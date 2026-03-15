"""Página: SIIF RF602.

Muestra el DataFrame del reporte RF602 del SIIF obtenido vía
GET /siif/rf602/ con filtro por ejercicio fiscal.
"""

from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.views.aux_tables import report_template


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_rf602",
            "default": get_ejercicios_list()[-1],
        },
        # {
        #     "label": "Unidades Ejecutoras",
        #     "options": ["Educación", "Salud", "Seguridad", "Obras"],
        #     "query_param": "unidad_id",
        #     "key": "ms_unidades",
        #     "default": ["Salud"]
        # }
    ]

    report_template(
        key="rf602",
        title="SIIF - Reporte RF602",
        endpoint=Endpoints.SIIF_RF602.value,
        description="Ejecución presupuestaria por estructura programática y "
        "partida. Datos extraídos del Sistema Integrado de "
        "Información Financiera (SIIF).",
        filters_config=mis_filtros,
    )

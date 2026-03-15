"""Página: SIIF RF610.

Muestra el DataFrame del reporte RF610 del SIIF obtenido vía
GET /siif/rf610/ con filtro por ejercicio fiscal.
"""

from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.views.aux_tables import report_template

ENDPOINT = Endpoints.SIIF_RF610.value


def render() -> None:
    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_rf610",
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
        key="rf610",
        title="SIIF - Reporte RF610",
        endpoint=Endpoints.SIIF_RF610.value,
        description="Ejecución presupuestaria con descripciones de programas, subprogramas, proyectos y actividades. Datos del SIIF.",
        filters_config=mis_filtros,
    )

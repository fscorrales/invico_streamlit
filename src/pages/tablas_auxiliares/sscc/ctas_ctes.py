"""Página: Tablas Auxiliares SSCC - Ctas Ctes (CRUD solo admin).

Unificador de Cuentas Corrientes con grilla exportable y, cuando el
usuario logueado tiene el rol ``admin``, botones de Agregar / Editar /
Borrar que abren los modales de ``src.views.modals``.
"""

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from src.components import text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import apply_text_filters, get_ctas_ctes
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    ReportState,
    dataframe_with_buttons,
    modal_ctas_ctes,
    modal_delete_registro_gral,
    report_data_version_key,
    report_header,
)

ENDPOINT = Endpoints.CTAS_CTES.value
REPORTE = "ctas_ctes"
LEGACY_TRIGGER_KEY = "ctas_ctes_uploader_iteration"
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Cuenta unificada",
        "column": "map_to",
        "placeholder": "Ej: 130101-01",
        "help": "Búsqueda parcial de la cuenta unificada (map_to), sin distinguir mayúsculas.",
    },
    {
        "label": "Desc. cta. cte.",
        "column": "desc_cta_cte",
        "placeholder": "Ej: BANCO",
        "help": "Búsqueda parcial de la descripción de la cuenta corriente.",
    },
]

# Orden lógico de la grilla: primero la cuenta unificada y la
# descripción, luego los nexos de cada sistema. ``id`` y ``updated_at``
# (cerrojo) son técnicos: no se muestran.
COLUMNAS_VISIBLES: list[str] = [
    "map_to",
    "desc_cta_cte",
    "sscc_cta_cte",
    "real_cta_cte",
    "siif_recursos_cta_cte",
    "siif_gastos_cta_cte",
    "siif_contabilidad_cta_cte",
    "sgf_cta_cte",
    "siif_cta_cte",
    "icaro_cta_cte",
]
COLUMNAS_OCULTAS: list[str] = ["id", "updated_at"]


# --------------------------------------------------
def _es_admin() -> bool:
    """True si el usuario logueado tiene el rol ``admin``."""
    usuario = st.session_state.get("user") or {}
    return "admin" in usuario.get("roles", [])


# --------------------------------------------------
def add_ctas_ctes() -> None:
    """Abre el modal de alta de cuenta corriente."""
    modal_ctas_ctes(
        key_prefix=f"add_ctas_ctes_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
    )


# --------------------------------------------------
def edit_ctas_ctes(datos_edicion: dict[str, Any]) -> None:
    """Abre el modal de edición precargado con la fila seleccionada."""
    modal_ctas_ctes(
        key_prefix=f"edit_ctas_ctes_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        datos_carga=datos_edicion,
        es_edicion=True,
    )


# --------------------------------------------------
def delete_ctas_ctes(datos_eliminar: dict[str, Any]) -> None:
    """Abre el modal de confirmación de baja de la cuenta corriente."""
    modal_delete_registro_gral(
        endpoint=f"{ENDPOINT}/delete_one/{datos_eliminar['id']}",
        desc_registro=f"con Cuenta Unificada {datos_eliminar.get('map_to', '')}",
        session_state_update_key=report_data_version_key(REPORTE),
        key_prefix=f"delete_ctas_ctes_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    )


# --------------------------------------------------
def render() -> None:
    # La cabecera (título, filtro avanzado, export) es un @st.fragment
    # que retorna el estado del reporte. Sin uploader: el alta/baja se
    # hace con los botones del CRUD (solo admin).
    state: ReportState = report_header(
        key=REPORTE,
        title="SSCC - Reporte " + REPORTE,
        description="Unificador de Cuentas Corrientes",
        endpoint=ENDPOINT,
        filters_config=None,
        has_export=True,
    )

    # Sincronizamos el trigger legacy ``ctas_ctes_uploader_iteration``
    # (consumido por ``get_ctas_ctes_list`` y las automatizaciones): el
    # CRUD incrementa ``data_version`` y esas cachés deben invalidarse
    # también. Nos quedamos con el máximo para no degradar el trigger.
    legacy_trigger = int(st.session_state.get(LEGACY_TRIGGER_KEY, 0))
    if state.data_version > legacy_trigger:
        legacy_trigger = state.data_version
    st.session_state[LEGACY_TRIGGER_KEY] = legacy_trigger

    es_admin = _es_admin()

    # df vacío por defecto para evitar UnboundLocalError si falla la API
    df = pd.DataFrame()
    try:
        df = get_ctas_ctes(
            filtro_avanzado=state.filtro_avanzado,
            update_trigger=state.data_version,
        )
        if df.empty:
            st.info("No se encontraron resultados.")
    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    if not df.empty:
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        # ``columns=len(FILTROS_TABLA)`` (= 2) deja las 2 cajas en una
        # sola fila con el mismo ancho que las columnas de la cabecera
        # (filtro avanzado + export), y solo afecta a ESTA página.
        valores_filtro = text_filters_bar(
            FILTROS_TABLA, key_prefix=REPORTE, columns=len(FILTROS_TABLA)
        )
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Orden dinámico: columnas visibles conocidas (las que falten se
        # omiten) + cualquier otra que traiga la API, excluyendo las
        # técnicas (id/updated_at) que ``column_order`` oculta.
        column_order = [
            col for col in COLUMNAS_VISIBLES if col in df_vista.columns
        ] + [
            col
            for col in df_vista.columns
            if col not in COLUMNAS_VISIBLES and col not in COLUMNAS_OCULTAS
        ]

        dataframe_with_buttons(
            df_vista,
            key=f"{REPORTE}_df_ctas_ctes",
            column_order=column_order,
            selection_mode="single-row" if es_admin else None,
            add_func=add_ctas_ctes if es_admin else None,
            edit_func=edit_ctas_ctes if es_admin else None,
            delete_func=delete_ctas_ctes if es_admin else None,
            show_buttons=es_admin,
        )

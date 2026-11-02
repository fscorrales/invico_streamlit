"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Planillometro's "Obras Desactivadas" view
"""

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

import src.utils.exceptions as ex
from src.components import text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ejercicios_list
from src.services.process_df import apply_text_filters
from src.utils.transform_data import formato_moneda_ar
from src.views import (
    ReportState,
    dataframe_with_buttons,
    modal_delete_registro_gral,
    modal_obras_desactivadas,
    report_data_version_key,
    report_header,
)

REPORTE = "obras_desactivadas"
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Cta. contable",
        "column": "cta_contable",
        "placeholder": "Ej: 1112-2-6",
    },
    {
        "label": "Estructura",
        "column": "estructura",
        "placeholder": "Ej: 11-00-02-79-421",
    },
]


# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_obras_desactivadas(
    filtro_avanzado: str = "",
    update_trigger: int = 0,
    selections: list[tuple[str, list[Any]]] | None = None,
) -> pd.DataFrame:
    """
    Obtiene el padrón de obras desactivadas desde la API.

    No persiste en Parquet: el ``@st.cache_data`` (TTL de 1 hora) es la
    única capa de caché, que evita llamadas repetidas a la API dentro
    del mismo TTL. Las excepciones no se cachean: se re-lanzan en cada
    invocación para que la UI pueda notificarlas.

    Args:
        filtro_avanzado: Filtro dinámico (e.g. ``ejercicio=2024``).
        update_trigger: Incrementar para forzar la actualización de caché.
        selections: Tuplas ``(query_param, valores)`` de los multiselects
            server-side (``filters_config`` de ``report_header``). Cada
            valor se serializa como string separado por comas
            (e.g. ``ejercicio=2026,2025``). Lista vacía o ``None`` no
            agrega parámetros (sin filtro).

    Returns:
        DataFrame con las obras desactivadas.

    Raises:
        APIConnectionError: Si la API falla.
        APIResponseError: Si la API retorna un error.
    """
    params_peticion: dict[str, Any] = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }
    if selections:
        for nombre_param, valores in selections:
            if valores:
                params_peticion[nombre_param] = ",".join(map(str, valores))
    df: pd.DataFrame = fetch_dataframe(
        Endpoints.OBRAS_DESACTIVADAS.value, params=params_peticion
    )
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cta_contable", "estructura"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
def add_obras_desactivadas(estructura: str | None = None) -> None:
    """Abre el modal de alta de obra desactivada.

    Args:
        estructura: Valor precargado en el selectbox "Estructura" (e.g.
            la estructura de la fila seleccionada en el planillómetro).
            El usuario puede cambiarla; ``None`` deja el combo vacío.
    """
    modal_obras_desactivadas(
        key_prefix=f"add_obras_desactivadas_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        datos_carga={"estructura": estructura} if estructura else None,
    )


# --------------------------------------------------
def edit_obras_desactivadas(datos_edicion: dict[str, Any]) -> None:
    modal_obras_desactivadas(
        key_prefix=f"edit_obras_desactivadas_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        datos_carga=datos_edicion,
        es_edicion=True,
    )


# --------------------------------------------------
def delete_obras_desactivadas(datos_eliminar: dict[str, Any]) -> None:
    modal_delete_registro_gral(
        endpoint=f"{Endpoints.OBRAS_DESACTIVADAS.value}/delete_one/{datos_eliminar['id']}",
        desc_registro=f"con cuenta contable {datos_eliminar['cta_contable']} y estructura {datos_eliminar['estructura']}",
        session_state_update_key=report_data_version_key(REPORTE),
        key_prefix=f"delete_obras_desactivadas_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    )


# --------------------------------------------------
def render() -> None:
    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-2],
        },
    ]

    # La cabecera (título, filtros, export) es un @st.fragment que retorna
    # el estado del reporte: no hace falta leer nada de session_state.
    state: ReportState = report_header(
        key=REPORTE,
        title="Obras Desactivadas",
        description="Puede trabajar aquí o en la pestaña 'Planillómetro EECC'.",
        endpoint=Endpoints.OBRAS_DESACTIVADAS.value,
        filters_config=mis_filtros,
        has_export=True,
    )

    # Ejecutamos la lógica con el fetcher cacheado local
    # (@st.cache_data vive en este módulo, igual que en el resto de las
    # páginas con fetcher propio). state.data_version se incrementa al
    # crear/editar/borrar registros y sirve de update_trigger para
    # invalidar ese caché.
    df_obras_desactivadas = pd.DataFrame()  # type: ignore  # fallback por defecto
    try:
        df_obras_desactivadas = get_obras_desactivadas(
            filtro_avanzado=state.filtro_avanzado,
            update_trigger=state.data_version,
            selections=state.selections,
        )
        if df_obras_desactivadas.empty:
            st.info("No se encontraron resultados.")
    except ex.APIConnectionError as exc:
        st.error(f"🌐 {exc}")
    except ex.APIResponseError as exc:
        st.error(f"⚠️ {exc}")

    # Mostrar resultados (usando session_state para que no desaparezcan)
    if not df_obras_desactivadas.empty:
        df_obras_desactivadas["importe"] = df_obras_desactivadas["importe"].apply(
            formato_moneda_ar
        )
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        valores_filtro = text_filters_bar(FILTROS_TABLA, key_prefix=REPORTE)
        df_vista = apply_text_filters(df_obras_desactivadas, valores_filtro)

        dataframe_with_buttons(
            df_vista,
            key=f"{REPORTE}_df_obras_desactivadas",
            height=300,
            column_order=[
                "ejercicio",
                "cta_contable",
                "estructura",
                "importe",
                "notas",
            ],
            selection_mode="single-row",
            add_func=add_obras_desactivadas,
            edit_func=edit_obras_desactivadas,
            delete_func=delete_obras_desactivadas,
        )


if __name__ == "__main__":
    render()

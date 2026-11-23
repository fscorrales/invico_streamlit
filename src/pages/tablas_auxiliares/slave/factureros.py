import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import apply_text_filters, fetch_dataframe
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import report_header

ENDPOINT = Endpoints.SLAVE_FACTUREROS.value
REPORTE = "slave_factureros"
# Columnas del DataFrame que NO se muestran en la grilla: id/_id son el
# interno de Mongo y updated_at la marca técnica de la migración de
# SLAVE. Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id", "updated_at")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
# Nota: esta tabla NO tiene columnas de importe (solo beneficiario,
# actividad y partida), por lo que no formatea moneda ni dibuja
# subtotales.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Beneficiario",
        "column": "beneficiario",
        "placeholder": "Ej: GOMEZ",
        "help": "Búsqueda parcial del nombre del facturero, sin distinguir mayúsculas.",
    },
    {
        "label": "Actividad",
        "column": "actividad",
        "placeholder": "Ej: 11-00-02",
        "help": "Búsqueda parcial de la actividad (imputación).",
    },
    {
        "label": "Partida",
        "column": "partida",
        "placeholder": "Ej: 1311",
        "help": "Búsqueda parcial de la partida presupuestaria.",
    },
]


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_slave_factureros(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    df = fetch_dataframe(ENDPOINT, params=params_peticion)
    if not df.empty:
        df = df.sort_values(
            ["nombre_completo", "actividad", "partida"],
        )

    return df


# --------------------------------------------------
def render() -> None:

    report_header(
        key=REPORTE,
        title="Slave - Tabla Factureros",
        description="Listado de Personal Facturero de Slave",
        endpoint=ENDPOINT,
        has_export=True,
    )

    if st.session_state.get(f"{REPORTE}_automation_success"):
        # Limpiamos el flag para que no entre en bucle infinito
        st.session_state[f"{REPORTE}_automation_success"] = False

        # Incrementamos el trigger de forma síncrona y segura
        actual = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
        st.session_state[f"{REPORTE}_uploader_iteration"] = actual + 1

        # Forzamos el recálculo total de la página con el nuevo trigger
        st.rerun()

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        df = get_slave_factureros(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info("No se encontraron resultados.")
        # else:
        #     st.session_state[f"data_{key}_carga"] = df_final
        #     st.session_state[f"data_{key}_retenciones"] = df_final_ret

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 4. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        # Son 3 filtros: se usa el default ``columns=3`` de
        # ``text_filters_bar()`` (una sola fila).
        valores_filtro = text_filters_bar(FILTROS_TABLA, key_prefix=REPORTE)
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = ["beneficiario"]

        # Generamos el orden dinámico: todas las de la vista que no estén
        # en la lista negra ni en CAMPOS_OCULTOS (id/_id/updated_at se
        # ocultan en la grilla)
        orden_dinamico = first_cols + [
            col
            for col in df_vista.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df_vista,
            key=f"{REPORTE}_df_slave_factureros",
            column_order=orden_dinamico,
        )

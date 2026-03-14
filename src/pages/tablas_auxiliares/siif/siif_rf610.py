"""Página: SIIF RF610.

Muestra el DataFrame del reporte RF610 del SIIF obtenido vía
GET /siif/rf610/ con filtro por ejercicio fiscal.
"""

import streamlit as st

from src.constants.endpoints import Endpoints
from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)

ENDPOINT = Endpoints.SIIF_RF610.value


def render() -> None:
    st.markdown("# SIIF - Reporte RF610")
    st.write(
        "Ejecución presupuestaria con descripciones de programas, "
        "subprogramas, proyectos y actividades. Datos del SIIF."
    )

    # --- Filtros y Actualización ---
    col1, col2 = st.columns([1, 3])
    with col1:
        ejercicio = st.number_input(
            "Ejercicio",
            min_value=2010,
            max_value=2030,
            value=2025,
            step=1,
        )
    with col2:
        st.write("")  # Espaciado para alinear con el input
        st.write("")
        if st.button("🔄 Actualizar desde SIIF"):
            st.info(
                "Automatización Playwright no implementada aún. "
                "Se lanzará el script de scraping del SIIF."
            )

    # --- Carga y visualización de datos ---
    try:
        with st.spinner("Cargando datos RF610..."):
            df = fetch_dataframe(
                ENDPOINT,
                params={"ejercicio": ejercicio, "limit": None},
            )

        if df.empty:
            st.info(f"No se encontraron datos RF610 para el ejercicio {ejercicio}.")
        else:
            st.write(f"### Registros encontrados: {len(df)}")
            st.dataframe(df, width="stretch")

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

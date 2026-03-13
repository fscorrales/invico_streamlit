"""Página: SSCC Banco INVICO.

Muestra el DataFrame del reporte Banco INVICO obtenido vía
GET /sscc/bancoINVICO/ con filtros por ejercicio y cuenta corriente.
"""

import streamlit as st

from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)

ENDPOINT = "/sscc/bancoINVICO/"


def render() -> None:
    st.markdown("# SSCC - Banco INVICO")
    st.write(
        "Movimientos bancarios del Instituto de Vivienda de "
        "Corrientes. Datos extraídos del Sistema de Seguimiento "
        "de Cuentas Corrientes (SSCC)."
    )

    # --- Filtros y Actualización ---
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        ejercicio = st.number_input(
            "Ejercicio",
            min_value=2010,
            max_value=2030,
            value=2025,
            step=1,
        )
    with col2:
        cta_cte = st.text_input(
            "Cuenta Corriente (opcional)",
            value="",
            help="Filtrar por número de cuenta corriente.",
        )
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Actualizar desde SSCC"):
            st.info(
                "Automatización Pywinauto no implementada aún. "
                "Se lanzará el script de escritorio del SSCC."
            )

    # --- Carga y visualización de datos ---
    try:
        with st.spinner("Cargando datos Banco INVICO..."):
            params: dict = {"ejercicio": ejercicio, "limit": None}
            if cta_cte.strip():
                params["ctaCte"] = cta_cte.strip()

            df = fetch_dataframe(ENDPOINT, params=params)

        if df.empty:
            st.info(
                f"No se encontraron datos de Banco INVICO para el "
                f"ejercicio {ejercicio}."
            )
        else:
            st.write(f"### Registros encontrados: {len(df)}")
            st.dataframe(df, width="stretch")

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

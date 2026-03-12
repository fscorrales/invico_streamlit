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


st.sidebar.header("Banco INVICO")
st.markdown("# SSCC - Banco INVICO")
st.write(
    "Movimientos bancarios del Instituto de Vivienda de "
    "Corrientes. Datos extraídos del Sistema de Seguimiento "
    "de Cuentas Corrientes (SSCC)."
)

# --- Filtros ---
ejercicio = st.sidebar.number_input(
    "Ejercicio",
    min_value=2010,
    max_value=2030,
    value=2025,
    step=1,
)

cta_cte = st.sidebar.text_input(
    "Cuenta Corriente (opcional)",
    value="",
    help="Filtrar por número de cuenta corriente.",
)

# --- Botón de actualización ---
if st.sidebar.button("🔄 Actualizar desde SSCC"):
    st.sidebar.info(
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
        st.dataframe(df, use_container_width=True)

except APIConnectionError as e:
    st.error(f"⚠️ Error de conexión: {e}")
except APIResponseError as e:
    st.error(f"⚠️ Error de API: {e}")

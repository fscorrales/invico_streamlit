"""Página: Control Recursos.

Muestra el DataFrame del control de recursos obtenido vía
GET /control/controlRecursos/ con filtro por ejercicio fiscal.
"""

import streamlit as st

from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)

ENDPOINT = "/control/controlRecursos/"


st.sidebar.header("Control Recursos")
st.markdown("# Control Recursos")
st.write(
    "Cruce de recursos SIIF vs depósitos bancarios. "
    "Permite filtrar por ejercicio fiscal y actualizar los datos."
)

# --- Filtros ---
ejercicio = st.sidebar.number_input(
    "Ejercicio",
    min_value=2010,
    max_value=2030,
    value=2025,
    step=1,
)

# --- Botón de actualización ---
if st.sidebar.button("🔄 Actualizar desde fuentes"):
    st.sidebar.info(
        "Automatización no implementada aún. "
        "Se lanzará el script correspondiente."
    )

# --- Carga y visualización de datos ---
try:
    with st.spinner("Cargando datos de Control Recursos..."):
        df = fetch_dataframe(
            ENDPOINT,
            params={"ejercicio": ejercicio, "limit": None},
        )

    if df.empty:
        st.info(
            f"No se encontraron datos para el ejercicio {ejercicio}."
        )
    else:
        st.write(
            f"### Registros encontrados: {len(df)}"
        )
        st.dataframe(df, use_container_width=True)

except APIConnectionError as e:
    st.error(f"⚠️ Error de conexión: {e}")
except APIResponseError as e:
    st.error(f"⚠️ Error de API: {e}")

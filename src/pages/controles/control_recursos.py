"""Página: Control Recursos.

Muestra el DataFrame del control de recursos obtenido vía
GET /control/controlRecursos/ con filtro por ejercicio fiscal.
"""

import streamlit as st

from src.constants.endpoints import Endpoints
from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)

ENDPOINT = Endpoints.CONTROL_RECURSOS.value


st.markdown("# Control Recursos")
st.write(
    "Cruce de recursos SIIF vs depósitos bancarios. "
    "Permite filtrar por ejercicio fiscal y actualizar los datos."
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
    st.write("")
    st.write("")
    if st.button("🔄 Actualizar desde fuentes"):
        st.info(
            "Automatización no implementada aún. Se lanzará el script correspondiente."
        )

# --- Carga y visualización de datos ---
try:
    with st.spinner("Cargando datos de Control Recursos..."):
        df = fetch_dataframe(
            ENDPOINT,
            params={"ejercicio": ejercicio, "limit": None},
        )

    if df.empty:
        st.info(f"No se encontraron datos para el ejercicio {ejercicio}.")
    else:
        st.write(f"### Registros encontrados: {len(df)}")
        st.dataframe(df, width="stretch")

except APIConnectionError as e:
    st.error(f"⚠️ Error de conexión: {e}")
except APIResponseError as e:
    st.error(f"⚠️ Error de API: {e}")

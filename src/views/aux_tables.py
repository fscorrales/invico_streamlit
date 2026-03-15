import itertools

import pandas as pd
import streamlit as st

from src.components.buttons import button_export, button_update
from src.components.multiselects import multiselect_filter
from src.components.text_inputs import text_input_advance_filter
from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)


@st.fragment  # Permite que los filtros internos no recarguen TODA la página
# --------------------------------------------------
def report_template(
    key: str, title: str, endpoint: str, description: str, filters_config: list
):
    """
    Vista reutilizable.
    filters_config: Lista de dicts con ['label', 'options', 'key', 'default']
    """
    st.markdown(f"# {title}")
    st.write(description)

    selections = []

    # 1. Renderizar Filtros
    # --- Filtros (Estado local del componente) ---
    with st.container(horizontal=True, vertical_alignment="bottom"):
        for i, f_conf in enumerate(filters_config):
            # Guardamos la selección en un diccionario para la API
            val = multiselect_filter(
                label=f_conf["label"],
                options=f_conf["options"],
                default=f_conf.get("default", []),
                key=f_conf["key"],  # Key única para evitar conflictos en Streamlit
            )
            # El nombre de la clave aquí debe coincidir con lo que espera tu API
            selections.append((f_conf["query_param"], val))

        filtro_avanzado = text_input_advance_filter(
            key="text_input_advance_filter-" + key
        )

        button_update("Actualizar desde SIIF", key="button_update-" + key)

        # Aquí podrías integrar tu logic de exportación
        button_export("Exportar a Excel y GS", key="button_export-" + key)

    # --- Lógica de Datos ---
    # 2. Validar que no haya filtros vacíos
    if any(not s[1] for s in selections):
        st.warning("Seleccione al menos un valor en cada filtro.")
        return

    # 3. Lógica de Fetch Iterativo (El equivalente al v-for de Vue + API calls)
    try:
        with st.spinner("Consultando datos..."):
            df_final = pd.DataFrame()

            # Extraemos solo las listas de valores: [[2023, 2024], ["Salud", "Educación"]]
            listas_valores = [s[1] for s in selections]
            # Extraemos los nombres de los parámetros: ["ejercicio", "unidad_id"]
            nombres_params = [s[0] for s in selections]

            # itertools.product genera todas las combinaciones posibles:
            # (2023, "Salud"), (2023, "Educación"), (2024, "Salud"), ...
            for combinacion in itertools.product(*listas_valores):
                # Creamos el diccionario de params para esta petición específica
                params_peticion = dict(zip(nombres_params, combinacion))
                params_peticion["limit"] = 0
                params_peticion["queryFilter"] = filtro_avanzado

                # Hacemos el fetch individual
                df_parcial = fetch_dataframe(endpoint, params=params_peticion)
                df_final = pd.concat([df_final, df_parcial], ignore_index=True)

            if df_final.empty:
                st.info("No se encontraron resultados.")
            else:
                st.session_state[f"data_{endpoint}"] = df_final

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 4. Mostrar resultados (usando session_state para que no desaparezcan)
    data_key = f"data_{endpoint}"
    if data_key in st.session_state:
        st.dataframe(st.session_state[data_key], width="stretch")

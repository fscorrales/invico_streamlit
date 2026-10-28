"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: EECC's Planillometro (Cecilia)
Data required:
    - Icaro Carga
    - SIIF rf602
    - SIIF rf610
    - Planillomtro Histórico (Patricia)
"""

import json
from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.automation.analysis.reporte_planillometro import (
    sync_reporte_planillometro_from_siif,
)
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import (
    fetch_dataframe,
    get_ejercicios_list,
    post_request,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPOINT = Endpoints.REPORTE_PLANILLOMETRO.value
REPORTE = "reporte_planillometro_eecc"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1Hmb7xmzhZBoicnL5_tN7mr1kOj-r3gw8lCkPErR8Xd4"


# --------------------------------------------------
def _upload_planillometro_eecc(df: pd.DataFrame) -> dict[str, Any]:
    """
    Sube el dataframe resultante a la base de datos mediante
    POST /reporte/reportePlanillometro. Devuelve la respuesta
    estandarizada (RouteReturnSchema: title, added, deleted, errors).
    """
    # Convertimos el DataFrame a registros nativos de Python
    # (numpy -> int/float y NaN -> null) para evitar errores de serialización.
    registros = json.loads(df.to_json(orient="records", date_format="iso"))
    return post_request(ENDPOINT, json_body=registros)


# --------------------------------------------------
def _render_post_summary(result: dict[str, Any], show_toast: bool = False) -> None:
    """Emite el toast de la subida (RouteReturnSchema) y, solo si hay
    inconsistencias, renderiza warning + métricas + detalle bajo el dataframe.
    """
    titulo = result.get("title") or "Sincronización"
    agregados = result.get("added", 0)
    eliminados = result.get("deleted", 0)
    lista_errores = result.get("errors", [])
    num_errores = len(lista_errores)

    # El toast solo se emite cuando la subida acaba de realizarse
    if show_toast:
        mensaje_toast = (
            f"📊 {titulo}: +{agregados} agregados, -{eliminados} eliminados."
        )
        if num_errores > 0:
            st.toast(mensaje_toast + f" ({num_errores} con errores)", icon="⚠️")
        else:
            st.toast(mensaje_toast, icon="✅")

    # Render condicional: si la sincronización fue limpia, el toast es suficiente
    if num_errores == 0:
        return

    st.warning(
        f"⚠️ **{titulo}**: {num_errores} inconsistencias detectadas "
        "durante la sincronización."
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Registros Agregados", agregados)
    col2.metric("Registros Eliminados", eliminados)
    col3.metric("Inconsistencias", num_errores, delta_color="inverse")

    with st.expander("❌ Detalle de Inconsistencias por Documento", expanded=True):
        for error_doc in lista_errores:
            doc_id = error_doc.get("doc_id", "ID Desconocido")
            detalles = error_doc.get("details", [])
            st.markdown(f"**Documento ID:** `{doc_id}`")
            for det in detalles:
                st.caption(f"📍 {det.get('loc')} | 🏷️ {det.get('error_type')}")
                st.write(f"💬 {det.get('msg')}")
            st.divider()


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_reporte_planillometro_eecc(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(ENDPOINT, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
async def run_automation(
    siif_username: str, siif_password: str, reporte: str
) -> list[str]:
    """
    Descarga y procesa rf610 desde SIIF (Playwright) para los ejercicios
    seleccionados y los sincroniza con el backend.
    """
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    return await sync_reporte_planillometro_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )


# --------------------------------------------------
def _generate_planillometro_eecc(ejercicio: int) -> pd.DataFrame:
    """
    GET /reporte/reportePlanillometro/generate replicando los parámetros
    de export_eecc: include_pa6=False, desagregar_desc_subprog=False,
    un solo ejercicio y limit=0 (equivale a limit=None: el servicio solo
    aplica df.head() cuando limit > 0).
    FastAPI enruta los query params por el alias camelCase de CamelModel.
    """
    params = {
        "ejercicio": ejercicio,
        "limit": 0,
        "includePa6": "false",
        "desagregarDescSubprog": "false",
    }
    return fetch_dataframe(ENDPOINT + "/generate", params=params)


# --------------------------------------------------
def _generate_and_upload() -> None:
    """
    Pipeline posterior a la automatización (u omisión de la descarga):
    1) GET /generate  -> reporte calculado por el backend.
    2) POST /reporte/reportePlanillometro -> sincroniza MongoDB.
    Guarda la respuesta (RouteReturnSchema) o el error en session_state
    para renderizarlos después del rerun.
    """
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    if not ejercicios:
        st.session_state[f"{REPORTE}_sync_warning"] = (
            "Seleccione un ejercicio antes de sincronizar el reporte."
        )
        return

    ejercicio = int(ejercicios[0])  # La vista permite un solo ejercicio

    try:
        with st.spinner("Generando el reporte Planillómetro EECC..."):
            df_generado = _generate_planillometro_eecc(ejercicio)

        if df_generado.empty:
            st.session_state[f"{REPORTE}_sync_warning"] = (
                "El endpoint /generate no devolvió registros: no se realizó el POST."
            )
            return

        with st.spinner("Sincronizando la base de datos (POST)..."):
            respuesta_post = _upload_planillometro_eecc(df_generado)

        if respuesta_post:
            st.session_state[f"{REPORTE}_post_result"] = respuesta_post
            st.session_state[f"{REPORTE}_post_toast_pending"] = True
        else:
            st.session_state[f"{REPORTE}_sync_warning"] = (
                "El POST no devolvió una respuesta válida."
            )
    except APIConnectionError as e:
        st.session_state[f"{REPORTE}_sync_error"] = f"Error de conexión: {e}"
    except APIResponseError as e:
        st.session_state[f"{REPORTE}_sync_error"] = f"Error de API: {e}"


# --------------------------------------------------
def render(
    automation_func: Optional[Any] = None,
) -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title=REPORTE.replace("_", " ").title(),
        endpoint=ENDPOINT,
        description=f"La automatización y la exportación impactan en los 3 subreportes/pestañas. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            automation_func or run_automation,
            key=REPORTE,
            downloaded_info="SIIF's rf610.",
        ),
        export_endpoint=ENDPOINT + "/exportEECC",
        has_advanced_filter=False,
        max_selections=1,  # Limitar a un solo ejercicio por vez
    )

    if st.session_state.get(f"{REPORTE}_automation_success"):
        # Limpiamos el flag para que no entre en bucle infinito
        st.session_state[f"{REPORTE}_automation_success"] = False

        # Pipeline: GET /generate -> POST (Mongo). Se ejecuta tanto tras la
        # automatización como cuando se omite la descarga del reporte.
        _generate_and_upload()

        # Incrementamos el trigger de forma síncrona y segura para que el
        # GET Get All refresque la tabla con los datos recién sincronizados
        actual = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
        st.session_state[f"{REPORTE}_uploader_iteration"] = actual + 1

        # Forzamos el recálculo total de la página con el nuevo trigger
        st.rerun()

    # Mostramos errores/avisos de la última sincronización (tras el rerun)
    error_sync = st.session_state.pop(f"{REPORTE}_sync_error", None)
    if error_sync:
        st.error(f"⚠️ {error_sync}")

    aviso_sync = st.session_state.pop(f"{REPORTE}_sync_warning", None)
    if aviso_sync:
        st.warning(aviso_sync)

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        df = get_reporte_planillometro_eecc(
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
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_planillometro_eecc",
            column_order=orden_dinamico,
        )

        # 5. Resumen de la última sincronización (RouteReturnSchema)
        resultado_post = st.session_state.get(f"{REPORTE}_post_result")
        if resultado_post:
            toast_pendiente = st.session_state.pop(
                f"{REPORTE}_post_toast_pending", False
            )
            _render_post_summary(resultado_post, show_toast=toast_pendiente)


if __name__ == "__main__":
    render()

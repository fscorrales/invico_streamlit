"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Recursos vs SSCC depósitos
Data required:
    - SIIF rcocc31
    - SIIF rci02
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1bZnvl9YkHC-N1HbIbnFNrqU3Iq03PG81u7fdHe_v_pw
"""

import pandas as pd
import streamlit as st

from src.automation.analysis import control_aporte_empresario
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_aporte_empresario, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_APORTE_EMPRESARIO.value
REPORTE = "control_aporte_empresario"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1bZnvl9YkHC-N1HbIbnFNrqU3Iq03PG81u7fdHe_v_pw"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo / correlativo SQL). Se excluyen de ``column_order``, lo que hace
# que Streamlit las oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    reporte: str,
) -> list[str]:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # 2. Iniciamos la descarga automática
    results = []
    # 2.a. Ejecutamos la automatización de SIIF
    results = await control_aporte_empresario.sync_control_aporte_empresario_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 3. El backend recalcula el cruce (GET /generateSIIF) y congelamos
    #    el snapshot en Mongo con un POST por ejercicio.
    results.extend(
        control_aporte_empresario.compute_control_aporte_empresario(
            ejercicios=ejercicios
        )
    )

    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Omite la descarga de reportes (SIIF) y recalcula el cruce
    con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_aporte_empresario``)
            usada para leer los ejercicios seleccionados en
            ``st.session_state``.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # Solo recalculamos: sin sync_control_aporte_empresario_from_siif().
    # compute_control_aporte_empresario() pide el cruce al backend
    # (GET /control/controlAporteEmpresario/generateSIIF) y sincroniza
    # la colección con un POST por ejercicio.
    return control_aporte_empresario.compute_control_aporte_empresario(
        ejercicios=ejercicios
    )


# --------------------------------------------------
def _render_totales_control_aporte_empresario(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce
    Recurso 3% vs Retención 337: total de recursos, total de
    retenciones y la diferencia entre ambos.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de recursos
    (``_render_totales_control_recursos``). Sin ``nowrap`` ni ellipsis:
    el texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles ``recurso`` y
    ``retencion`` (con ``parse_moneda_ar``, que acepta tanto el número
    crudo de la API como una cadena ya formateada) y la resta se
    formatea con ``formato_moneda_ar``.

    Args:
        df: DataFrame del control de aporte empresario (se espera que
            tenga las columnas ``recurso`` y ``retencion``).
    """
    columnas_requeridas = {"recurso", "retencion"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_recurso: float = df["recurso"].apply(parse_moneda_ar).sum()
    total_retencion: float = df["retencion"].apply(parse_moneda_ar).sum() * -1
    diferencia: float = total_recurso - total_retencion

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total Recursos",
            total_recurso,
            "Suma de la columna recurso de todas las filas visibles",
        ),
        (
            "Total Retenciones",
            total_retencion,
            "Suma de la columna retencion de todas las filas visibles",
        ),
        (
            "Diferencia",
            diferencia,
            "Total Recursos - Total Retenciones",
        ),
    )

    items: list[str] = []
    for etiqueta, total, ayuda in metricas:
        valor = formato_moneda_ar(total)
        # Dos ítems: etiqueta (línea 1) + valor en negrita (línea 2).
        # Sin nowrap/ellipsis para que el total nunca aparezca cortado.
        items.append(
            f'<div title="{ayuda}" '
            f'style="flex:1 1 0; min-width:0; text-align:center;">'
            f'<div style="font-size:11px; opacity:0.75; '
            f'white-space:normal;">{etiqueta}</div>'
            f'<div style="font-size:13px; font-weight:600;">'
            f"{valor}</div></div>"
        )

    st.markdown(
        '<div style="display:flex; gap:0.75rem; font-size:13px; '
        'align-items:flex-start;">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
def render() -> None:

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
        description=f"Cruce de Recurso 3% (rci02) vs Retención 337 (rcocc31). Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="SIIF: rci02 y rcocc31 (1112-2-6 y 2122-1-2)",
            skip_callback=(lambda: run_skip(REPORTE)) if run_skip else None,
        ),
        max_selections=1,
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
        df = get_control_aporte_empresario(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info("No se encontraron resultados.")

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la
        # lista negra ni en CAMPOS_OCULTOS (id/_id se ocultan en la grilla)
        orden_dinamico = first_cols + [
            col
            for col in df.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_aporte_empresario",
            column_order=orden_dinamico,
        )

        # Franja de totales: total de recursos, total de retenciones y
        # la diferencia entre ambos, siempre visible fuera de la grilla.
        _render_totales_control_aporte_empresario(df)


if __name__ == "__main__":
    render()

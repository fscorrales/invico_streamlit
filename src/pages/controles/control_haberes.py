"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Haberes vs SSCC
Data required:
    - SIIF rcg01_uejp
    - SIIF rpa03g
    - SIIF rdeu012
    - SIIF rcocc31 (2122-1-2)
    - SSCC Resumen General de Movimientos
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1A9ypUkwm4kfLqUAwr6-55crcFElisOO9fOdI6iflMAc
"""

import pandas as pd
import streamlit as st

from src.automation.analysis import control_haberes
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_haberes, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_and_sscc_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_HABERES.value
REPORTE = "control_haberes"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1A9ypUkwm4kfLqUAwr6-55crcFElisOO9fOdI6iflMAc"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
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
    results = await control_haberes.sync_control_haberes_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 2.b. Ejecutamos el módulo runner de SSCC en un proceso separado
    control_haberes.sync_control_haberes_from_sscc(
        sscc_username=sscc_username,
        sscc_password=sscc_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SSCC ejecutado correctamente.")

    # 3. El backend recalcula el cruce (GET /generate) y congelamos el
    #    snapshot en Mongo con un POST por ejercicio.
    results.extend(control_haberes.compute_control_haberes(ejercicios=ejercicios))

    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Omite la descarga de reportes (SIIF y SSCC) y recalcula el cruce
    con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_haberes``)
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

    # Solo recalculamos: sin sync_control_haberes_from_siif() ni
    # sync_control_haberes_from_sscc(). compute_control_haberes() pide
    # el cruce al backend (GET /control/controlHaberes/generate) y
    # sincroniza la colección con un POST por ejercicio.
    return control_haberes.compute_control_haberes(ejercicios=ejercicios)


# --------------------------------------------------
def _render_totales_control_haberes(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce mensual
    Haberes SIIF vs SSCC: total ejecutado en SIIF, total pagado en el
    banco (SSCC) y la diferencia entre ambos.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de obras
    (``_render_totales_control_obras``). Sin ``nowrap`` ni ellipsis: el
    texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles ``ejecutado_siif`` y
    ``pagado_sscc`` (con ``parse_moneda_ar``, que acepta tanto el número
    crudo de la API como una cadena ya formateada) y la resta se
    formatea con ``formato_moneda_ar``.

    Args:
        df: DataFrame del control de haberes (se espera que tenga las
            columnas ``ejecutado_siif`` y ``pagado_sscc``).
    """
    columnas_requeridas = {"ejecutado_siif", "pagado_sscc"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_ejecutado_siif: float = df["ejecutado_siif"].apply(parse_moneda_ar).sum()
    total_pagado_sscc: float = df["pagado_sscc"].apply(parse_moneda_ar).sum()
    diferencia: float = total_ejecutado_siif - total_pagado_sscc

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total Ejecutado SIIF",
            total_ejecutado_siif,
            "Suma de la columna ejecutado_siif de todas las filas visibles",
        ),
        (
            "Total Pagado SSCC",
            total_pagado_sscc,
            "Suma de la columna pagado_sscc de todas las filas visibles",
        ),
        (
            "Diferencia",
            diferencia,
            "Total Ejecutado SIIF - Total Pagado SSCC",
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
        description=f"SIIF Haberes vs SSCC. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_and_sscc_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="SIIF's rdeu012, rcocc31 (2122-1-2), gto_rpa03g y rcg01_uejp. SSCC's Banco INVICO",
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
        df = get_control_haberes(
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
        # Formato moneda AR ($ 1.234,56) para los importes visibles de la
        # grilla. ``parse_moneda_ar`` (franja de totales) es el inverso de
        # ``formato_moneda_ar`` y acepta tanto el número crudo de la API
        # como la cadena ya formateada, por lo que los totales siguen
        # cuadrando con lo que muestra la grilla. El df proviene de
        # ``@st.cache_data`` (copia deserializada por llamada), por lo que
        # mutarlo en el lugar es seguro. Los nulos quedan en blanco y la
        # pasada extra por ``parse_moneda_ar`` hace el formateo idempotente
        # ante cadenas ya formateadas.
        for columna_moneda in ("ejecutado_siif", "pagado_sscc", "diferencia", "dif_acum"):
            if columna_moneda in df.columns:
                df[columna_moneda] = df[columna_moneda].apply(
                    lambda valor: (
                        formato_moneda_ar(parse_moneda_ar(valor))
                        if pd.notna(valor)
                        else ""
                    )
                )

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
            key=f"{REPORTE}_df_control_haberes",
            column_order=orden_dinamico,
        )

        # Franja de totales: ejecutado SIIF vs pagado SSCC, siempre
        # visible fuera de la grilla.
        _render_totales_control_haberes(df)


if __name__ == "__main__":
    render()

from typing import Any

import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rfondo07tp import Rfondo07tp
from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import (
    apply_text_filters,
    fetch_dataframe,
    get_ejercicios_list,
    get_tipos_comprobantes_siif_list,
    post_request,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPOINT = Endpoints.SIIF_RFONDO07TP.value
REPORTE = "rfondo07tp"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
# "mes" es una búsqueda parcial simple sobre la columna homónima
# (formato MM/AAAA); no usa semántica de "mes hasta".
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Mes",
        "column": "mes",
        "placeholder": "Ej: 05/2026",
        "help": "Búsqueda parcial del mes (MM/AAAA), sin distinguir mayúsculas.",
    },
    {
        "label": "Glosa",
        "column": "glosa",
        "placeholder": "Ej: DEPOSITO",
        "help": "Búsqueda parcial de la glosa, sin distinguir mayúsculas.",
    },
    {
        "label": "Nro. fondo",
        "column": "nro_fondo",
        "placeholder": "Ej: 00123",
        "help": "Búsqueda parcial del número de fondo, sin distinguir mayúsculas.",
    },
]
# Columnas con importes: se formatean como moneda AR en la grilla y son
# las que alimentan la franja de subtotales. Los 3 valores son numéricos
# crudos de la API (``process_dataframe`` los pasa por ``pd.to_numeric``).
COLUMNAS_IMPORTE: tuple[str, ...] = ("ingresos", "egresos", "saldo")
# Subtotales de la franja bajo la grilla (etiqueta visible, columnas que
# se suman).
COLUMNAS_SUBTOTALES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Total Ingresos", ("ingresos",)),
    ("Total Egresos", ("egresos",)),
    ("Total Saldo", ("saldo",)),
)
TIPOS_COMPROBANTES = get_tipos_comprobantes_siif_list(
    update_trigger=st.session_state.tipos_comprobantes_siif_uploader_iteration
)


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfondo07tp(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFONDO07TP.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "tipo_comprobante", "nro_comprobante"],
            ascending=[False, False, False, False],
        )

    return df


# --------------------------------------------------
async def run_automation(username: str, password: str, reporte: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    tipos_comprobantes = st.session_state.get("tipos_comprobante_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    if not tipos_comprobantes:
        st.error("No hay tipos de comprobantes seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    if isinstance(tipos_comprobantes, str):
        tipos_comprobantes = [tipos_comprobantes]

    async with async_playwright() as p:
        siif = Rfondo07tp()
        # The Rfondo07tp class handles login via SIIFReportManager.login
        await siif.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await siif.go_to_reports()

        results = []
        for ej in ejercicios:
            for tipo_comprobante in tipos_comprobantes:
                df_clean = await siif.download_and_process_report(
                    ejercicio=ej, tipo_comprobante=tipo_comprobante
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(ENDPOINT, json_body=json_data)
                    results.append(f"Ejercicio {ej}: {response}")

        await siif.logout()
        return results


# --------------------------------------------------
def _render_subtotales_rfondo07tp(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los subtotales de los
    importes (:data:`COLUMNAS_SUBTOTALES`): ingresos, egresos y saldo.

    Los subtotales quedan FUERA del dataframe —siempre a la vista— para
    que el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la de los demás reportes. Sin
    ``nowrap`` ni ellipsis: el texto nunca se recorta. Hereda los
    colores del tema (no se fijan colores en el markup) y los ``title``
    nativos del HTML muestran el tooltip al hacer hover, sin JS.

    Cada ítem suma sus :data:`COLUMNAS_SUBTOTALES` con
    ``parse_moneda_ar`` (acepta tanto el número crudo de la API como la
    cadena ya formateada) y el resultado se vuelve a formatear con
    ``formato_moneda_ar``, de modo que el subtotal coincide con lo que
    muestra la grilla. Las columnas ausentes se ignoran; si ningún ítem
    tiene columnas, no se dibuja nada.

    Args:
        df: Vista del reporte —la grilla ya filtrada por
            ``text_filters_bar()``.
    """
    items: list[str] = []
    for etiqueta, columnas in COLUMNAS_SUBTOTALES:
        columnas_presentes = [col for col in columnas if col in df.columns]
        if not columnas_presentes:
            continue
        total: float = sum(
            df[col].apply(parse_moneda_ar).sum() for col in columnas_presentes
        )
        valor = formato_moneda_ar(total)
        ayuda = "Subtotal de la vista filtrada: " + " + ".join(
            columnas_presentes
        )
        # Dos ítems: etiqueta (línea 1) + valor en negrita (línea 2).
        # Sin nowrap/ellipsis para que el subtotal nunca aparezca cortado.
        items.append(
            f'<div title="{ayuda}" '
            f'style="flex:1 1 0; min-width:0; text-align:center;">'
            f'<div style="font-size:11px; opacity:0.75; '
            f'white-space:normal;">{etiqueta}</div>'
            f'<div style="font-size:13px; font-weight:600;">'
            f"{valor}</div></div>"
        )

    if not items:
        return

    st.markdown(
        '<div style="display:flex; gap:0.75rem; font-size:13px; '
        'align-items:flex-start;">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
        {
            "label": "Elija el tipo de comprobante",
            "options": TIPOS_COMPROBANTES,
            "query_param": "tipoComprobante",
            "key": "tipos_comprobante_" + REPORTE,
            "default": "PA6",
        },
    ]

    report_template(
        key=REPORTE,
        title="SIIF - Reporte " + REPORTE,
        endpoint=ENDPOINT,
        description="Resumen de Fondos del Ejercicio por Tipo de Comprobante",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(run_automation, key=REPORTE),
        allow_extra_options=True,
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
        df = get_siif_rfondo07tp(
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
        # Formato moneda AR ($ 1.234,56) para los importes numéricos de
        # la grilla. ``parse_moneda_ar`` (franja de subtotales) es el
        # inverso de ``formato_moneda_ar`` y acepta tanto el número crudo
        # de la API como la cadena ya formateada, por lo que los
        # subtotales siguen cuadrando con lo que muestra la grilla. El df
        # proviene de ``@st.cache_data`` (copia deserializada por
        # llamada), por lo que mutarlo en el lugar es seguro. Los nulos
        # quedan en blanco y la pasada extra por ``parse_moneda_ar`` hace
        # el formateo idempotente ante cadenas ya formateadas.
        for columna_moneda in COLUMNAS_IMPORTE:
            if columna_moneda in df.columns:
                df[columna_moneda] = df[columna_moneda].apply(
                    lambda valor: (
                        formato_moneda_ar(parse_moneda_ar(valor))
                        if pd.notna(valor)
                        else ""
                    )
                )

        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        valores_filtro = text_filters_bar(FILTROS_TABLA, key_prefix=REPORTE)
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
            "mes",
            "fecha",
            "tipo_comprobante",
            "nro_comprobante",
            "ingresos",
            "egresos",
            "saldo",
        ]

        # Generamos el orden dinámico: todas las de la vista que no estén
        # en la lista negra ni en CAMPOS_OCULTOS (id/_id se ocultan en la
        # grilla)
        orden_dinamico = first_cols + [
            col
            for col in df_vista.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df_vista,
            key=f"{REPORTE}_df_rfondo07tp",
            column_order=orden_dinamico,
        )

        # Franja de subtotales: ingresos, egresos y saldo de las filas
        # visibles (tras los filtros de la barra), siempre fuera de la
        # grilla.
        if not df_vista.empty:
            _render_subtotales_rfondo07tp(df_vista)

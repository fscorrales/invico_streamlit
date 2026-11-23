from typing import Any

import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

from src.automation.sgv.saldos_barrios_evolucion import SaldosBarriosEvolucion
from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import (
    apply_text_filters,
    fetch_dataframe,
    get_ejercicios_list,
    post_request,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_us, parse_moneda_ar
from src.views import (
    report_template,
    request_sgv_credentials_modal,
)

ENDPOINT = Endpoints.SALDOS_BARRIOS_EVOLUCION.value
REPORTE = "saldos_barrios_evolucion"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Barrio",
        "column": "barrio",
        "placeholder": "Ej: SAN MARTIN",
        "help": "Búsqueda parcial del nombre del barrio, sin distinguir mayúsculas.",
    },
    {
        "label": "Cód. barrio",
        "column": "cod_barrio",
        "placeholder": "Ej: 0001",
        "help": "Búsqueda parcial del código de barrio (4 dígitos con ceros).",
    },
]
# Columnas con importes: se formatean como moneda (estilo US) en la grilla y son
# las que alimentan la franja de subtotales. Los 4 valores son
# numéricos crudos de la API (``SaldosBarriosEvolucionReport`` los
# declara como float y la automatización los pasa por ``astype(float)``).
COLUMNAS_IMPORTE: tuple[str, ...] = (
    "saldo_inicial",
    "amortizacion",
    "cambios",
    "saldo_final",
)
# Subtotales de la franja bajo la grilla (etiqueta visible, columnas que
# se suman): el acumulado de la vista filtrada por cada columna de saldo.
COLUMNAS_SUBTOTALES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Saldo Inicial", ("saldo_inicial",)),
    ("Amortización", ("amortizacion",)),
    ("Cambios", ("cambios",)),
    ("Saldo Final", ("saldo_final",)),
)


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sgv_barrios_saldo_evolucion(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(ENDPOINT, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cod_barrio"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
async def run_automation(username: str, password: str, reporte: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    async with async_playwright() as p:
        sgv = SaldosBarriosEvolucion()
        await sgv.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await sgv.go_to_specific_report()

        results = []
        for ej in ejercicios:
            df_clean = await sgv.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(ENDPOINT, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await sgv.logout()
        return results


# --------------------------------------------------
def _render_subtotales_sgv_saldos_barrios_evolucion(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los subtotales de saldos
    (:data:`COLUMNAS_SUBTOTALES`): saldo inicial, amortización, cambios
    y saldo final.

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
    ``formato_moneda_us``, de modo que el subtotal coincide con lo que
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
        valor = formato_moneda_us(total)
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
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-2],
        },
    ]

    report_template(
        key=REPORTE,
        title="SGV - Saldos por Barrios (evolución)",
        endpoint=ENDPOINT,
        description="Saldos por Barrios del Sistema Recuperos",
        filters_config=mis_filtros,
        update_func=lambda: request_sgv_credentials_modal(run_automation, key=REPORTE),
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
        df = get_sgv_barrios_saldo_evolucion(
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
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        # Son 2 filtros: se usa el default ``columns=3`` de
        # ``text_filters_bar()`` (una sola fila).
        valores_filtro = text_filters_bar(FILTROS_TABLA, key_prefix=REPORTE)
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
            "cod_barrio",
            "barrio",
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
            key=f"{REPORTE}_df_saldos_barrios_evolucion",
            column_order=orden_dinamico,
            columnas_importe=COLUMNAS_IMPORTE,
        )

        # Franja de subtotales: saldos y movimientos de las filas
        # visibles (tras los filtros de la barra), siempre fuera de la
        # grilla.
        if not df_vista.empty:
            _render_subtotales_sgv_saldos_barrios_evolucion(df_vista)

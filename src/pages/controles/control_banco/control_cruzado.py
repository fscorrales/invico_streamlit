from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import (
    apply_mes_hasta_filter,
    apply_text_filters,
    get_control_banco_cruzado,
    get_ejercicios_list,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_and_sscc_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_BANCO_CRUZADO.value
REPORTE = "control_banco_cruzado"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1CRQjzIVzHKqsZE8_E1t8aRQDfWfZALhbe64WcxHiSM4"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Columnas que se subtotalizan bajo la grilla (columna, etiqueta
# visible). Se calculan sobre la vista filtrada con ``parse_moneda_ar``
# y se muestran con ``formato_moneda_ar``.
COLUMNAS_SUBTOTALES: tuple[tuple[str, str], ...] = (
    ("siif_importe", "Total SIIF"),
    ("sscc_importe", "Total SSCC"),
    ("diferencia", "Diferencia"),
)
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
# "mes" es especial: se resuelve con apply_mes_hasta_filter() porque
# tiene semántica de "mes hasta" (ej: "05" -> meses 01..05 del ejercicio
# en trabajo; "05/2026" -> meses 01/2026..05/2026).
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Cta. cte.",
        "column": "cta_cte",
        "placeholder": "Ej: 130101-01",
        "help": "Búsqueda parcial de la cuenta corriente, sin distinguir mayúsculas.",
    },
    {
        "label": "Clase",
        "column": "clase",
        "placeholder": "Ej: HABERES",
        "help": "Búsqueda parcial de la clase, sin distinguir mayúsculas.",
    },
    {
        "label": "Mes hasta",
        "column": "mes",
        "placeholder": "Ej: 05, 5 o 05/2026",
        "help": (
            "Trae todos los meses del año hasta el indicado (inclusive). "
            "Formato: MM o MM/AAAA. Sin año explícito se usa el ejercicio "
            "seleccionado arriba."
        ),
    },
]


# --------------------------------------------------
def _render_subtotales_banco_cruzado(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con el subtotal de cada columna
    de importes del cruce SIIF vs SSCC (:data:`COLUMNAS_SUBTOTALES`).

    Los subtotales quedan FUERA del dataframe —siempre a la vista— para
    que el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la de los demás controles
    (``_render_totales_*``). Sin ``nowrap`` ni ellipsis: el texto nunca
    se recorta. Hereda los colores del tema (no se fijan colores en el
    markup) y los ``title`` nativos del HTML muestran el tooltip al
    hacer hover, sin JS.

    Se suman los valores de las columnas visibles con
    ``parse_moneda_ar`` (acepta tanto el número crudo de la API como la
    cadena ya formateada) y el resultado se vuelve a formatear con
    ``formato_moneda_ar``, de modo que el subtotal coincide con lo que
    muestra la grilla.

    Args:
        df: Vista del cruce —la grilla ya filtrada por
            ``text_filters_bar()``— (columnas de
            :data:`COLUMNAS_SUBTOTALES`; las ausentes se ignoran).
    """
    columnas_subtotales = [
        (columna, etiqueta)
        for columna, etiqueta in COLUMNAS_SUBTOTALES
        if columna in df.columns
    ]
    if not columnas_subtotales:
        return

    ayuda = "Subtotal de la columna visible en la grilla (vista filtrada)"
    items: list[str] = []
    for columna, etiqueta in columnas_subtotales:
        total: float = df[columna].apply(parse_moneda_ar).sum()
        valor = formato_moneda_ar(total)
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

    st.markdown(
        '<div style="display:flex; gap:0.75rem; font-size:13px; '
        'align-items:flex-start;">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
def render(
    automation_func: Optional[Any] = None,
    skip_func: Optional[Any] = None,
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
        update_func=lambda: request_siif_and_sscc_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF: rcocc31 (ctas. contables del rvicon03), rcg01uejp y gto_rpa03g. SSCC's Banco INVICO",
            skip_callback=(lambda: skip_func(REPORTE)) if skip_func else None,
        ),
        export_endpoint=Endpoints.CONTROL_BANCO.value + "/export",
        export_mode="sheet",
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
        df = get_control_banco_cruzado(
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
        # Formato moneda AR ($ 1.234,56) para los importes visibles de la
        # grilla. ``parse_moneda_ar`` (franja de subtotales) es el inverso
        # de ``formato_moneda_ar`` y acepta tanto el número crudo de la API
        # como la cadena ya formateada, por lo que los subtotales siguen
        # cuadrando con lo que muestra la grilla. El df proviene de
        # ``@st.cache_data`` (copia deserializada por llamada), por lo que
        # mutarlo en el lugar es seguro. Los nulos quedan en blanco y la
        # pasada extra por ``parse_moneda_ar`` hace el formateo idempotente
        # ante cadenas ya formateadas. Se formatean exactamente las
        # columnas de COLUMNAS_SUBTOTALES.
        for columna_moneda, _etiqueta in COLUMNAS_SUBTOTALES:
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
        # "mes" no es un contains simple: se resuelve con semántica de
        # "mes hasta" ("05"/"5" -> meses 01..05 del ejercicio en trabajo;
        # "05/2026" -> meses 01/2026..05/2026).
        valor_mes: str = valores_filtro.pop("mes", "").strip()
        df_vista = apply_text_filters(df, valores_filtro)

        ejercicios_trabajo: list[int] = st.session_state.get(
            f"ejercicios_{REPORTE}", []
        )
        if isinstance(ejercicios_trabajo, int):
            ejercicios_trabajo = [ejercicios_trabajo]
        try:
            df_vista = apply_mes_hasta_filter(
                df_vista,
                valor_mes,
                ejercicios_trabajo,
            )
        except ValueError as exc:
            st.warning(f"⚠️ Filtro 'Mes hasta' no aplicado: {exc}")

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
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
            key=f"{REPORTE}_df_control_banco_cruzado",
            column_order=orden_dinamico,
        )

        # Franja de subtotales: SIIF, SSCC y diferencia de las filas
        # visibles (tras los filtros de la barra), siempre fuera de la
        # grilla.
        if not df_vista.empty:
            _render_subtotales_banco_cruzado(df_vista)


if __name__ == "__main__":
    render()

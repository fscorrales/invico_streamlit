from datetime import datetime

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import apply_text_filters, fetch_dataframe
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_us, parse_moneda_ar
from src.views import report_header

ENDPOINT = Endpoints.SLAVE_HONORARIOS.value
REPORTE = "slave_honorarios"
# Columnas del DataFrame que NO se muestran en la grilla: id/_id son el
# interno de Mongo y updated_at la marca técnica de la migración de
# SLAVE. Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id", "updated_at")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
# "mes" es una búsqueda parcial simple sobre la columna homónima
# (formato MM/AAAA); no usa semántica de "mes hasta".
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Tipo",
        "column": "tipo",
        "placeholder": "Ej: HON",
        "help": "Búsqueda parcial del tipo de liquidación, sin distinguir mayúsculas.",
    },
    {
        "label": "Actividad",
        "column": "actividad",
        "placeholder": "Ej: 11-00-02",
        "help": "Búsqueda parcial de la actividad (imputación).",
    },
    {
        "label": "Beneficiario",
        "column": "beneficiario",
        "placeholder": "Ej: GOMEZ",
        "help": "Búsqueda parcial del nombre del proveedor, sin distinguir mayúsculas.",
    },
    {
        "label": "Mes",
        "column": "mes",
        "placeholder": "Ej: 05/2026",
        "help": "Búsqueda parcial del mes de liquidación (formato MM/AAAA).",
    },
]
# Columnas con importes: se formatean como moneda (estilo US) en la grilla y son
# las que alimentan la franja de subtotales. Los 10 valores son
# numéricos crudos de la API (la migración de SLAVE los guarda como
# números y ``mutual``/``embargo`` arrancan en 0).
COLUMNAS_IMPORTE: tuple[str, ...] = (
    "importe_bruto",
    "sellos",
    "seguro",
    "iibb",
    "lp",
    "otras_retenciones",
    "anticipo",
    "descuento",
    "mutual",
    "embargo",
)
# Retenciones: TODO lo que se descuenta del importe bruto. Es la suma
# exacta del 2º renglón de la franja, de modo que
# Importe Neto = Importe Bruto − Retenciones queda como lo que se paga
# efectivamente.
RETENCIONES: tuple[str, ...] = (
    "iibb",
    "lp",
    "sellos",
    "seguro",
    "embargo",
    "otras_retenciones",
    "mutual",
    "descuento",
    "anticipo",
)
# Subtotales de la franja bajo la grilla, en DOS filas. Cada ítem es
# (etiqueta visible, columnas a sumar, columnas a restar): el restar
# (tupla vacía cuando no aplica) permite dibujar el Importe Neto sin
# crear una columna derivada en la grilla.
#   * 1ª fila: importe bruto, retenciones e importe neto
#     (= bruto − retenciones).
#   * 2ª fila: el detalle de las retenciones —IIBB, LP + Sellos,
#     seguro, embargo y "otros" (otras retenciones, mutual, descuento y
#     anticipo)—; su suma coincide con el ítem "Retenciones".
ItemSubtotal = tuple[str, tuple[str, ...], tuple[str, ...]]
FILAS_SUBTOTALES: tuple[tuple[ItemSubtotal, ...], ...] = (
    (
        ("Importe Bruto", ("importe_bruto",), ()),
        ("Retenciones", RETENCIONES, ()),
        ("Importe Neto", ("importe_bruto",), RETENCIONES),
    ),
    (
        ("IIBB", ("iibb",), ()),
        ("LP + Sellos", ("lp", "sellos"), ()),
        ("Seguro", ("seguro",), ()),
        ("Embargo", ("embargo",), ()),
        ("Otros", ("otras_retenciones", "mutual", "descuento", "anticipo"), ()),
    ),
)


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_slave_honorarios(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    if filtro_avanzado == "":
        filtro_avanzado = f"ejercicio={datetime.today().year}"

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    df = fetch_dataframe(Endpoints.SLAVE_HONORARIOS.value, params=params_peticion)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
def _render_subtotales_slave_honorarios(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los subtotales, en DOS filas.

    Primera fila (:data:`FILAS_SUBTOTALES`[0]): importe bruto,
    retenciones e importe neto (= importe bruto − retenciones: el único
    ítem calculado, no existe como columna en la grilla). Segunda fila
    (:data:`FILAS_SUBTOTALES`[1]): el detalle de las retenciones —
    IIBB, LP + Sellos, seguro, embargo y "otros" (otras retenciones,
    mutual, descuento y anticipo)—; su suma coincide con el ítem
    "Retenciones" de la 1ª fila.

    Los subtotales quedan FUERA del dataframe —siempre a la vista— para
    que el usuario no tenga que desplazarse hasta la última fila. Cada
    fila es una franja HTML flex de dos líneas por ítem (etiqueta
    arriba, valor en negrita abajo) y ambas se apilan en un contenedor
    flex vertical, idéntico en estilo al del resumen de rendiciones.
    Sin ``nowrap`` ni ellipsis: el texto nunca se recorta. Hereda los
    colores del tema (no se fijan colores en el markup) y los ``title``
    nativos del HTML muestran el tooltip al hacer hover, sin JS.

    Cada ítem suma sus columnas a sumar y resta las a restar con
    ``parse_moneda_ar`` (acepta tanto el número crudo de la API como la
    cadena ya formateada) y el resultado se vuelve a formatear con
    ``formato_moneda_us``, de modo que el subtotal coincide con lo que
    muestra la grilla. Las columnas ausentes se ignoran; si ningún ítem
    de una fila tiene columnas, esa fila no se dibuja.

    Args:
        df: Vista del reporte —la grilla ya filtrada por
            ``text_filters_bar()``.
    """
    filas_html: list[str] = []
    for fila in FILAS_SUBTOTALES:
        items: list[str] = []
        for etiqueta, sumar, restar in fila:
            sumar_presentes = [col for col in sumar if col in df.columns]
            restar_presentes = [col for col in restar if col in df.columns]
            if not sumar_presentes and not restar_presentes:
                continue
            total: float = sum(
                df[col].apply(parse_moneda_ar).sum() for col in sumar_presentes
            )
            total -= sum(
                df[col].apply(parse_moneda_ar).sum()
                for col in restar_presentes
            )
            valor = formato_moneda_us(total)
            ayuda = "Subtotal de la vista filtrada: " + " + ".join(
                sumar_presentes
            )
            if restar_presentes:
                ayuda += " - " + " - ".join(restar_presentes)
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
            continue
        # Una fila = un div flex horizontal; las filas se apilan abajo.
        filas_html.append(
            '<div style="display:flex; gap:0.75rem; font-size:13px; '
            'align-items:flex-start;">' + "".join(items) + "</div>"
        )

    if not filas_html:
        return

    st.markdown(
        '<div style="display:flex; flex-direction:column; '
        'gap:0.35rem;">' + "".join(filas_html) + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
def render() -> None:

    report_header(
        key=REPORTE,
        title="Slave - Tabla Honorarios",
        description="Tabla Honorarios de Slave",
        endpoint=ENDPOINT,
        has_export=True,
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
        df = get_slave_honorarios(
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
        # ``columns=len(FILTROS_TABLA)`` (= 4) deja los 4 filtros en una
        # sola fila y solo afecta a ESTA página: el resto de los reportes
        # sigue usando el default ``columns=3`` de ``text_filters_bar()``.
        valores_filtro = text_filters_bar(
            FILTROS_TABLA, key_prefix=REPORTE, columns=len(FILTROS_TABLA)
        )
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = ["ejercicio"]

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
            key=f"{REPORTE}_df_slave_honorarios",
            column_order=orden_dinamico,
            columnas_importe=COLUMNAS_IMPORTE,
        )

        # Franja de subtotales: importe bruto, retenciones e importe
        # neto de las filas visibles (tras los filtros de la barra),
        # siempre fuera de la grilla.
        if not df_vista.empty:
            _render_subtotales_slave_honorarios(df_vista)

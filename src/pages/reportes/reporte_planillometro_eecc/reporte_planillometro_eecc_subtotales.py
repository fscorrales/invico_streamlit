"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Planillometro EECC's "Subtotales" view

Muestra el reporte Planillómetro EECC con una franja de subtotales bajo
la grilla para las 5 columnas de importes del reporte (Ejecución Actual,
Acumulado, En Curso, Terminado Ant y Terminado Actual).

Al seleccionar una fila de la grilla principal se lista, debajo, la
colección CARGA ICARO agrupada por ``desc_obra``, filtrada por la
estructura de la fila y hasta su ejercicio, con: ejercicio de alta
(mínimo), total ejecutado y máximo avance.

Data required:
    - Reporte Planillómetro EECC
    - Icaro Carga
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.pages.reportes.reporte_planillometro_eecc.reporte_planillometro_eecc import (
    get_reporte_planillometro_eecc,
)
from src.services import apply_text_filters, fetch_dataframe, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_us, parse_moneda_ar
from src.views import report_template

ENDPOINT = Endpoints.REPORTE_PLANILLOMETRO.value
REPORTE = "planillometro_eecc_subtotales"
# Columnas del reporte que se subtotalizan bajo la grilla principal
# (columna del DataFrame, etiqueta visible).
COLUMNAS_SUBTOTALES: tuple[tuple[str, str], ...] = (
    ("ejecucion", "Ejecución Actual"),
    ("acum", "Acumulado"),
    ("en_curso", "En Curso"),
    ("terminadas_ant", "Terminado Ant"),
    ("terminadas_actual", "Terminado Actual"),
)
# Columnas del df principal del planillómetro que NO se muestran.
CAMPOS_OCULTOS_PRINCIPAL: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Estructura",
        "column": "estructura",
        "placeholder": "Ej: 11-00-02-79-421",
    },
    {
        "label": "Desc. proyecto",
        "column": "desc_proyecto",
        "placeholder": "Ej: Capital",
    },
    {
        "label": "Desc. actividad",
        "column": "desc_actividad",
        "placeholder": "Ej: Const. ...",
    },
]
# Altura del cuadro principal en píxeles (~7 filas visibles).
ALTURA_GRILLA_PRINCIPAL: int = 220
# Altura de la subgrilla de Carga ICARO agrupada (~6 filas visibles).
ALTURA_GRILLA_ICARO: int = 180


# --------------------------------------------------
def _formato_avance(valor: Any) -> str:
    """Convierte un avance fraccionario (0-1) a porcentaje legible.

    Args:
        valor: Avance crudo de Carga ICARO (e.g. ``0.8155``).

    Returns:
        ``"81.55%"`` o ``""`` si el valor es nulo.
    """
    if valor is None or pd.isna(valor):
        return ""
    return f"{float(valor):.2%}"


# --------------------------------------------------
def _render_subtotales_planillometro(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla principal con el subtotal de cada
    una de las 5 columnas de importes del planillómetro.

    Los subtotales quedan FUERA del dataframe —siempre a la vista— para
    que el usuario no tenga que desplazarse hasta la última fila. Es la
    misma franja HTML flex de dos líneas por ítem (etiqueta arriba,
    valor en negrita abajo) que usa la pestaña principal, con los ítems
    repartidos en columnas de igual ancho. Hereda los colores del tema y
    los ``title`` nativos del HTML muestran el tooltip al hacer hover.

    Se suman los valores de la vista filtrada (``parse_moneda_ar``
    acepta el valor crudo o la cadena ya formateada) y el resultado se
    vuelve a formatear, de modo que el subtotal coincide exactamente
    con lo que muestra la grilla.

    Args:
        df: Vista del reporte filtrada con ``FILTROS_TABLA`` (valores
            crudos o formateados; ambos son soportados).
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
        valor = formato_moneda_us(total)
        # Dos lítems: etiqueta (línea 1) + valor en negrita (línea 2).
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
@st.cache_data(show_spinner="Consultando Carga ICARO...", ttl=3600)
def get_carga_acum_obra(actividad: str, partida: str, ejercicio: int) -> pd.DataFrame:
    """Acumulado por obra de la Carga ICARO para una estructura.

    Consulta ``GET /icaro/carga/acumObra`` (sin ``limit``: sin límite
    de grupos), que agrupa en el backend por
    ``actividad``/``partida``/``desc_obra`` —importe (suma), ejercicio
    (mínimo) y avance (máximo)— filtrando hasta ``ejercicio``
    inclusive. Evita descargar la colección completa, que provocaba
    el timeout de lectura de 90 s.

    Args:
        actividad: Actividad de la estructura (e.g. ``11-00-02-79``).
        partida: Partida de la estructura (e.g. ``421``).
        ejercicio: Ejercicio máximo (inclusive) a considerar.

    Returns:
        DataFrame crudo con ``actividad``, ``partida``, ``desc_obra``,
        ``importe``, ``ejercicio`` y ``avance``. Vacío si no hay datos.
    """
    params = {
        "actividad": actividad,
        "partida": partida,
        "ejercicioHasta": int(ejercicio),
    }
    endpoint = Endpoints.ICARO_CARGA.value + "/acumObra"
    return fetch_dataframe(endpoint, params=params)


# --------------------------------------------------
def _acum_obra_formateado(df_acum: pd.DataFrame) -> pd.DataFrame:
    """Convierte la respuesta de ``acumObra`` en la grilla de detalle.

    Mapea ``ejercicio`` (mínimo del grupo) a ``Ejercicio Alta``,
    ``importe`` (suma) a ``Total Ejecutado`` NUMÉRICO —la grilla lo
    formatea como moneda US vía ``column_config``— y ``avance``
    (máximo) a ``Máximo Avance`` en porcentaje.

    Args:
        df_acum: Respuesta cruda de ``GET /icaro/carga/acumObra``.

    Returns:
        DataFrame con ``desc_obra``, ``Ejercicio Alta``,
        ``Total Ejecutado`` y ``Máximo Avance``, ordenado por
        ``ejercicio`` de mayor a menor y, dentro del mismo ejercicio,
        por ``avance`` de menor a mayor. Vacío si no hay datos o
        faltan columnas.
    """
    requeridas = {"desc_obra", "ejercicio", "importe", "avance"}
    if df_acum.empty or not requeridas.issubset(df_acum.columns):
        return pd.DataFrame()

    # Orden sobre los valores CRUDOS y antes del render: "Máximo
    # Avance" queda como cadena ("76.14%") y no se puede ordenar
    # numéricamente. Los nulos van al final (na_position="last") y el
    # sort estable mantiene el orden de `desc_obra` ante empates.
    df_ordenado = df_acum.copy()
    df_ordenado["ejercicio"] = pd.to_numeric(
        df_ordenado["ejercicio"], errors="coerce"
    )
    df_ordenado["avance"] = pd.to_numeric(df_ordenado["avance"], errors="coerce")
    df_ordenado = df_ordenado.sort_values(
        by=["ejercicio", "avance"],
        ascending=[False, True],
        kind="stable",
        na_position="last",
    )

    resultado = pd.DataFrame(
        {
            "desc_obra": df_ordenado["desc_obra"],
            "Ejercicio Alta": df_ordenado["ejercicio"].round().astype("Int64"),
            "Total Ejecutado": pd.to_numeric(
                df_ordenado["importe"], errors="coerce"
            ).fillna(0.0),
            "Máximo Avance": df_ordenado["avance"].apply(_formato_avance),
        }
    )
    return resultado.reset_index(drop=True)


# --------------------------------------------------
def _render_detalle_icaro(df_planillometro: pd.DataFrame, event: Any) -> None:
    """Renderiza debajo de la grilla la Carga ICARO de la fila elegida.

    Consulta ``GET /icaro/carga/acumObra`` con
    ``@st.cache_data`` propio (TTL de 1 hora por
    actividad/partida/ejercicio): el backend agrupa por ``desc_obra``
    y filtra hasta el ejercicio de la fila, sin descargar la
    colección completa de Carga ICARO.

    Args:
        df_planillometro: Vista del reporte planillómetro principal —
            la grilla ya filtrada con ``FILTROS_TABLA``.
        event: Evento de selección (``on_select="rerun"``) de la grilla
            principal; se espera ``selection_mode="single-row"``.
    """
    filas_seleccionadas: list[int] = list(event.selection.rows)
    # Se valida contra el largo de la vista porque la grilla puede
    # haberse reducido (FILTROS_TABLA) después de la última selección.
    if not filas_seleccionadas or filas_seleccionadas[0] >= len(df_planillometro):
        st.info(
            "Seleccione una fila del planillómetro para listar la Carga ICARO "
            "agrupada por desc_obra (estructura de la fila y hasta su ejercicio)."
        )
        return

    fila_seleccionada = df_planillometro.iloc[filas_seleccionadas[0]]
    estructura = fila_seleccionada.get("estructura")
    ejercicio = fila_seleccionada.get("ejercicio")

    if (
        estructura is None
        or pd.isna(estructura)
        or ejercicio is None
        or pd.isna(ejercicio)
    ):
        st.warning(
            "⚠️ La fila seleccionada no tiene estructura/ejercicio válidos "
            "para vincular la Carga ICARO."
        )
        return
    ejercicio = int(ejercicio)

    # Estructura "11-00-02-79-421" → actividad "11-00-02-79" y
    # partida "421": el último guión separa la partida del resto.
    estructura_limpia = str(estructura).strip()
    actividad, separador, partida = estructura_limpia.rpartition("-")
    if not separador or not actividad or not partida:
        st.warning(
            f"⚠️ La estructura '{estructura_limpia}' no tiene formato "
            "'actividad-partida' para vincular la Carga ICARO."
        )
        return

    try:
        df_acum = get_carga_acum_obra(actividad, partida, ejercicio)
    except APIConnectionError as e:
        st.error(f"🌐 {e}")
        return
    except APIResponseError as e:
        st.error(f"⚠️ {e}")
        return

    st.markdown(f"#### 📋 Carga ICARO - {estructura} (hasta {ejercicio})")

    df_detalle = _acum_obra_formateado(df_acum)
    if df_detalle.empty:
        st.info(
            "Sin registros de Carga ICARO para esta estructura "
            "hasta el ejercicio seleccionado."
        )
        return

    dataframe(
        df_detalle,
        key=f"{REPORTE}_df_icaro_carga_agrupada",
        height=ALTURA_GRILLA_ICARO,
        column_order=[
            "desc_obra",
            "Ejercicio Alta",
            "Total Ejecutado",
            "Máximo Avance",
        ],
        columnas_importe=("Total Ejecutado",),
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

    # Cabecera (título, filtros, export) como @st.fragment propio de esta
    # pestaña: clave independiente de la pestaña principal para no
    # compartir widgets de filtro ni el estado de exportación.
    report_template(
        key=REPORTE,
        title="",
        description=(
            "Subtotales del Planillómetro EECC. Al seleccionar una fila "
            "se lista la Carga ICARO agrupada por desc_obra."
        ),
        endpoint=ENDPOINT,
        filters_config=mis_filtros,
        update_func=None,
        has_update=False,  # La sincronización vive en la pestaña principal
        has_export=True,
        export_endpoint=ENDPOINT + "/exportEECC",
        has_advanced_filter=False,
        max_selections=1,  # Limitar a un solo ejercicio por vez
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        # Reutiliza el @st.cache_data de la pestaña principal: misma
        # colección, misma caché (TTL de 1 día) para ambas pestañas.
        df = get_reporte_planillometro_eecc(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info("No se encontraron resultados.")
    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    if df.empty:
        return

    # Filtros particulares de la grilla (frontend puro, sin llamadas
    # a la API): declarativos en FILTROS_TABLA y aplicados en cascada
    # sobre la vista que consumen grilla, subtotales y detalle ICARO.
    valores_filtro = text_filters_bar(FILTROS_TABLA, key_prefix=REPORTE)
    df_vista = apply_text_filters(df, valores_filtro)
    if df_vista.empty:
        st.info("No se encontraron resultados con los filtros de la barra.")
        return

    # Columnas fijas (pinned): siempre visibles al desplazar a la derecha
    first_cols = [col for col in ("ejercicio", "estructura") if col in df_vista.columns]

    # Orden dinámico: primeras las fijas y sin id/_id (ocultas)
    orden_dinamico = first_cols + [
        col
        for col in df_vista.columns
        if col not in first_cols and col not in CAMPOS_OCULTOS_PRINCIPAL
    ]

    # pinned=True mantiene ejercicio y estructura inmovibles mientras
    # se desplaza horizontalmente por la tabla.
    column_config_principal: dict[str, Any] = {}
    if "ejercicio" in first_cols:
        column_config_principal["ejercicio"] = st.column_config.NumberColumn(
            pinned=True,
            format="%d",
        )
    if "estructura" in first_cols:
        column_config_principal["estructura"] = st.column_config.TextColumn(pinned=True)

    event = dataframe(
        df_vista,
        key=f"{REPORTE}_df_planillometro",
        height=ALTURA_GRILLA_PRINCIPAL,
        column_order=orden_dinamico,
        column_config=column_config_principal,
        columnas_importe=tuple(col for col, _ in COLUMNAS_SUBTOTALES),
        on_select="rerun",
        selection_mode="single-row",
    )

    # Subtotales de las 5 columnas de importes: franja SIEMPRE visible
    # fuera de la grilla (sin scroll hasta la última fila), calculada
    # sobre la vista filtrada (mismas filas que la grilla).
    _render_subtotales_planillometro(df_vista)

    # Detalle de la Carga ICARO agrupado por desc_obra según la fila
    # seleccionada (estructura de la fila y hasta su ejercicio).
    _render_detalle_icaro(df_vista, event)


if __name__ == "__main__":
    render()

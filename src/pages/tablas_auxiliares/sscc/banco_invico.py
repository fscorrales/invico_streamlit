import os
import subprocess
import sys
from typing import Any

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.services import (
    apply_text_filters,
    fetch_dataframe,
    get_ejercicios_list,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_sscc_credentials_modal,
)

ENDPOINT = Endpoints.SSCC_BANCO_INVICO.value
REPORTE = "banco_invico"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "Cta. cte.",
        "column": "cta_cte",
        "placeholder": "Ej: 130101-01",
        "help": "Búsqueda parcial de la cuenta corriente, sin distinguir mayúsculas.",
    },
    {
        "label": "Cod. imputación",
        "column": "cod_imputacion",
        "placeholder": "Ej: 024",
        "help": "Búsqueda parcial del código de imputación, sin distinguir mayúsculas.",
    },
    {
        "label": "Beneficiario",
        "column": "beneficiario",
        "placeholder": "Ej: GONZALEZ",
        "help": "Búsqueda parcial del beneficiario, sin distinguir mayúsculas.",
    },
    {
        "label": "Concepto",
        "column": "concepto",
        "placeholder": "Ej: DEPOSITO",
        "help": "Búsqueda parcial del concepto, sin distinguir mayúsculas.",
    },
]
# Columnas con importes: se formatean como moneda AR en la grilla y son
# las que alimentan la franja de subtotales. ``importe`` es numérico
# crudo de la API (``process_dataframe`` lo pasa por ``astype(float)``).
COLUMNAS_IMPORTE: tuple[str, ...] = ("importe",)
# Subtotales de la franja bajo la grilla (etiqueta visible, columnas que
# se suman).
COLUMNAS_SUBTOTALES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Total Importe", ("importe",)),
)


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sscc_banco_invico(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SSCC_BANCO_INVICO.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "cta_cte"],
            ascending=[False, False, True],
        )

    return df


# --------------------------------------------------
def run_automation(username: str, password: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    ejercicios_str = ",".join(map(str, ejercicios))

    # En lugar de la ruta al archivo, usamos el nombre del módulo
    # Esto equivale a hacer: python -m src.automation.sscc.banco_invico_runner
    modulo_runner = "src.automation.sscc.banco_invico_runner"

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        # En PRODUCCIÓN (.exe): Pasamos el flag genérico Y LUEGO el string del módulo
        args = [
            sys.executable,
            "--automation",
            modulo_runner,  # 🚀 Se convierte en sys.argv[1] antes de que el arranque lo limpie
            username,
            password,
            st.session_state.get("token", ""),
            ejercicios_str,
        ]
    else:
        # En DESARROLLO (.py): Tu comando tradicional por consola con -m
        args = [
            sys.executable,
            "-m",
            modulo_runner,
            username,
            password,
            st.session_state.get("token", ""),
            ejercicios_str,
        ]

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )
    process.wait()  # Esperamos a que termine el proceso antes de continuar
    return process


# --------------------------------------------------
def _render_subtotales_banco_invico(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con el subtotal del importe
    (:data:`COLUMNAS_SUBTOTALES`).

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
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title="SSCC - Reporte " + REPORTE,
        endpoint=ENDPOINT,
        description="",
        filters_config=mis_filtros,
        update_func=lambda: request_sscc_credentials_modal(run_automation, key=REPORTE),
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
        df = get_sscc_banco_invico(
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
        # Formato moneda AR ($ 1.234,56) para el importe de la grilla.
        # ``parse_moneda_ar`` (franja de subtotales) es el inverso de
        # ``formato_moneda_ar`` y acepta tanto el número crudo de la API
        # como la cadena ya formateada, por lo que los subtotales siguen
        # cuadrando con lo que muestra la grilla. El df proviene de
        # ``@st.cache_data`` (copia deserializada por llamada), por lo que
        # mutarlo en el lugar es seguro. Los nulos quedan en blanco y la
        # pasada extra por ``parse_moneda_ar`` hace el formateo idempotente
        # ante cadenas ya formateadas.
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
        # ``columns=len(FILTROS_TABLA)`` mantiene los 4 filtros en una
        # sola fila y solo afecta a ESTA página: el resto de los reportes
        # sigue usando el default ``columns=3`` de ``text_filters_bar()``.
        valores_filtro = text_filters_bar(
            FILTROS_TABLA, key_prefix=REPORTE, columns=len(FILTROS_TABLA)
        )
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = ["ejercicio", "mes", "fecha", "cta_cte", "importe"]

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
            key=f"{REPORTE}_df_banco_invico",
            column_order=orden_dinamico,
        )

        # Franja de subtotales: importe de las filas visibles (tras los
        # filtros de la barra), siempre fuera de la grilla.
        if not df_vista.empty:
            _render_subtotales_banco_invico(df_vista)

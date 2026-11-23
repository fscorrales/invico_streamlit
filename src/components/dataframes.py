__all__ = ["dataframe"]

from typing import Any

import pandas as pd
import streamlit as st

from src.utils.transform_data import formato_moneda_us, parse_moneda_ar

# Formato printf (sprintf.js, locale fijo US) de las columnas
# monetarias en la grilla: "$ 1,234.57" (negativos: "$ -1,234.57").
# Es el único punto de ajuste del estilo del grid. La franja de
# subtotales replica este mismo estilo con ``formato_moneda_us`` de
# ``utils/transform_data`` (mismo resultado: "$ 1,234.57").
FORMATO_MONEDA_GRID: str = "$ %,.2f"


# --------------------------------------------------
def dataframe(
    data: pd.DataFrame,
    key: str = "df",
    height: int = 300,
    columnas_importe: tuple[str, ...] | list[str] | None = None,
    **kwargs,
) -> Any:
    """Grilla interactiva con formato de moneda por lista blanca.

    Args:
        data: DataFrame a renderizar. No se muta en el lugar (el
            fallback de columnas no numéricas trabaja sobre una copia).
        key: Widget key de ``st.dataframe``.
        height: Alto del contenedor.
        columnas_importe: Columnas que deben mostrarse como moneda. Si
            el dtype es numérico se configura ``NumberColumn``: la celda
            conserva el número subyacente, con lo que el orden por
            header es NUMÉRICO (no alfabético como con strings). Si el
            dtype no es numérico (defensa: la API devolvió strings) se
            formatea a moneda estilo US sobre una copia local. Las
            columnas fuera de la lista (ejercicio, avance, partida...) no
            reciben configuración y se muestran tal cual.
        **kwargs: Se propagan a ``st.dataframe``. ``column_config`` del
            caller se fusiona al final (pisa el generado arriba) y
            ``hide_index`` tiene default True.

    Returns:
        El valor de ``st.dataframe`` (evento del widget) o ``None``.
    """
    column_config: dict[str, Any] = {}

    # Formato de moneda por lista blanca (ver docstring).
    fallback_cols: list[str] = []
    if columnas_importe:
        fallback_cols = [
            col
            for col in columnas_importe
            if col in data.columns
            and not pd.api.types.is_numeric_dtype(data[col])
        ]
        if fallback_cols:
            data = data.copy()
            for col in fallback_cols:
                data[col] = data[col].apply(
                    lambda valor: (
                        formato_moneda_us(parse_moneda_ar(valor))
                        if pd.notna(valor)
                        else ""
                    )
                )
        for col in columnas_importe:
            if col in data.columns and col not in fallback_cols:
                column_config[col] = st.column_config.NumberColumn(
                    format=FORMATO_MONEDA_GRID
                )

    # El caller puede ampliar el column_config (e.g. columnas con
    # pinned=True) y sobrescribir hide_index; se extraen de kwargs para no
    # duplicar el argumento en la llamada a st.dataframe.
    column_config.update(kwargs.pop("column_config", None) or {})
    hide_index = kwargs.pop("hide_index", True)

    with st.container(border=False, width="stretch"):
        return st.dataframe(
            data,
            key=key,
            height=height,
            width="stretch",
            column_config=column_config,
            hide_index=hide_index,
            **kwargs,
        )

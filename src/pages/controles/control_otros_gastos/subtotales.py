"""Franja de subtotales compartida por las pestañas de Otros Gastos."""

import streamlit as st


# --------------------------------------------------
def render_subtotales(items: list[tuple[str, str, str]]) -> None:
    """Franja compacta bajo la grilla con los subtotales de la tabla.

    Los subtotales quedan FUERA del dataframe —siempre a la vista— para
    que el usuario no tenga que desplazarse hasta la última fila. Es la
    misma franja HTML flex de dos líneas por ítem (etiqueta arriba,
    valor en negrita abajo) que usan el resto de los controles: sin
    ``nowrap`` ni ellipsis (el texto nunca se recorta), hereda los
    colores del tema (no se fijan colores en el markup) y los
    ``title`` nativos del HTML muestran el tooltip al hacer hover, sin
    JS.

    Args:
        items: Tuplas ``(etiqueta, valor_ya_formateado, ayuda)``; la
            ayuda se usa como tooltip del ítem.
    """
    if not items:
        return

    html: list[str] = []
    for etiqueta, valor, ayuda in items:
        html.append(
            f'<div title="{ayuda}" '
            f'style="flex:1 1 0; min-width:0; text-align:center;">'
            f'<div style="font-size:11px; opacity:0.75; '
            f'white-space:normal;">{etiqueta}</div>'
            f'<div style="font-size:13px; font-weight:600;">'
            f"{valor}</div></div>"
        )

    st.markdown(
        '<div style="display:flex; gap:0.75rem; font-size:13px; '
        'align-items:flex-start;">' + "".join(html) + "</div>",
        unsafe_allow_html=True,
    )

from typing import Any

import streamlit as st


# --------------------------------------------------
def multiselect_filter(label: str, options: list[str], default: Any = None, **kwargs):
    """Un componente reutilizable"""
    with st.container(border=False, width="stretch"):
        values = st.multiselect(label, options=options, default=default, **kwargs)
    return values

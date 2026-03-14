import streamlit as st


# --------------------------------------------------
def button_update(label: str, key: str = "button_update", **kwargs):
    """Un componente reutilizable"""
    with st.container(border=False, width="content"):
        if st.button("🔄 " + label, key=key, **kwargs):
            pass


# --------------------------------------------------
def button_export(label: str, key: str = "button_export", **kwargs):
    """Un componente reutilizable"""
    with st.container(border=False, width="content"):
        if st.button("🔄 " + label, key=key, **kwargs):
            pass

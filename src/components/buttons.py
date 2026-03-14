import streamlit as st


# --------------------------------------------------
def button_update(label: str, **kwargs):
    """Un componente reutilizable"""
    with st.container(border=False, width="content"):
        if st.button("🔄 " + label, **kwargs):
            pass


# --------------------------------------------------
def button_export(label: str, **kwargs):
    """Un componente reutilizable"""
    with st.container(border=False, width="content"):
        if st.button("🔄 " + label, **kwargs):
            pass

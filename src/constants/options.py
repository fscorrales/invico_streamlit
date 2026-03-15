import datetime as dt

import streamlit as st


@st.cache_data
# --------------------------------------------------
def get_ejercicios_list() -> list[int]:
    return list(range(2010, dt.date.today().year + 1))

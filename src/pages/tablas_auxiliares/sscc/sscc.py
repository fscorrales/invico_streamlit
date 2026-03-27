"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.pages.tablas_auxiliares.sscc import banco_invico


def main() -> None:
    tab1, tab2 = st.tabs(["Banco INVICO", "Ctas Ctes"])

    with tab1:
        banco_invico.render()

    with tab2:
        pass


if __name__ == "__main__":
    main()

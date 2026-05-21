"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.pages.tablas_auxiliares.sscc import banco_invico, ctas_ctes


def main() -> None:
    tab_banco_invico, tab_ctas_ctes = st.tabs(
        ["Banco INVICO", "Ctas Ctes"], on_change="rerun"
    )

    if tab_banco_invico.open:
        banco_invico.render()

    if tab_ctas_ctes.open:
        ctas_ctes.render()


if __name__ == "__main__":
    main()

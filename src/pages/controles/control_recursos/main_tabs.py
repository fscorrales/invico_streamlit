import streamlit as st

from src.pages.controles.control_recursos import (
    control_aporte_empresario,
    control_recursos,
)


def main() -> None:
    tab_control_recursos, tab_control_aporte_empresario = st.tabs(
        ["Control Recursos", "Control 3% INVICO (aport. empresario)"], on_change="rerun"
    )

    if tab_control_recursos.open:
        control_recursos.render()

    if tab_control_aporte_empresario.open:
        control_aporte_empresario.render()


if __name__ == "__main__":
    main()

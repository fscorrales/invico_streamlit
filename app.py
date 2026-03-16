"""
INVICO Control Presupuestario — Entrypoint principal.

Usa st.navigation() con secciones agrupadas para construir
el sidebar de navegación MPA. La sección "Administración"
solo es visible para usuarios con rol admin.
"""

import streamlit as st

from src.pages.login import render_login

st.set_page_config(
    page_title="INVICO Control Presupuestario",
    page_icon="📊",
    layout="wide",
)


# ──────────────────────────────────────────────
# Inicialización del estado de sesión
# ──────────────────────────────────────────────
def initialize_state() -> None:
    """Inicializa las claves mínimas en session_state."""
    if "token" not in st.session_state:
        st.session_state["token"] = None
    if "user" not in st.session_state:
        st.session_state["user"] = None


# ──────────────────────────────────────────────
# Navegación MPA
# ──────────────────────────────────────────────
def build_navigation() -> None:
    """Construye la navegación con st.navigation y ejecuta la página."""
    role = st.session_state["user"]["role"]

    pages: dict[str, list] = {
        "Controles": [
            st.Page(
                "src/pages/controles/control_recursos.py",
                title="Control Recursos",
                icon="💰",
            ),
            st.Page(
                "src/pages/controles/control_icaro.py",
                title="Control Icaro",
                icon="🏗️",
            ),
            st.Page(
                "src/pages/controles/control_obras.py",
                title="Control Obras",
                icon="🔨",
            ),
            st.Page(
                "src/pages/controles/control_honorarios.py",
                title="Control Honorarios",
                icon="📋",
            ),
            st.Page(
                "src/pages/controles/control_haberes.py",
                title="Control Haberes",
                icon="👤",
            ),
        ],
        "Tablas Auxiliares": [
            st.Page(
                "src/pages/tablas_auxiliares/siif/siif.py",
                title="SIIF",
                icon="📊",
            ),
            st.Page(
                "src/pages/tablas_auxiliares/sgf.py",
                title="SGF",
                icon="📑",
            ),
            st.Page(
                "src/pages/tablas_auxiliares/sscc.py",
                title="SSCC",
                icon="🏦",
            ),
        ],
        "Reportes": [
            st.Page(
                "src/pages/reportes/reportes_home.py",
                title="Reportes",
                icon="📈",
            ),
        ],
    }

    # Sección de admin solo visible para rol admin
    if role == "admin":
        pages["Administración"] = [
            st.Page(
                "src/pages/admin/gestion_usuarios.py",
                title="Gestión de Usuarios",
                icon="👥",
            ),
        ]

    pg = st.navigation(pages)

    # 2. Crear un "Header" en la parte superior de la página
    with st.container(
        vertical_alignment="center", height="stretch", gap=None, horizontal=False
    ):
        with st.container(
            horizontal=True, vertical_alignment="bottom", horizontal_alignment="right"
        ):
            with st.container(width="content"):
                st.write(f"👤 **{st.session_state['user']['username']}**")
            with st.container(width="content"):
                if st.button("Log out", width="stretch"):
                    st.session_state["token"] = None
                    st.session_state["user"] = None
                    st.rerun()

        st.divider()

    # 3. Ejecutar la página
    pg.run()

    # # ── Sidebar inferior: info de usuario y logout ──
    # with st.sidebar:
    #     st.divider()
    #     username = st.session_state["user"]["username"]
    #     st.caption(f"👤 {username} ({role})")

    #     if st.button("Cerrar Sesión", width="stretch"):
    #         st.session_state["token"] = None
    #         st.session_state["user"] = None
    #         st.rerun()


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main() -> None:
    initialize_state()

    # TEMPORARY: Bypass Login para desarrollo
    # if not st.session_state.get("token"):
    #     st.session_state["token"] = "dev-bypass-token"
    #     st.session_state["user"] = {
    #         "role": "admin",
    #         "username": "developer",
    #         "id": "1",
    #     }

    if not st.session_state["token"]:
        render_login()
    else:
        build_navigation()


# --------------------------------------------------
if __name__ == "__main__":
    main()

"""
INVICO Control Presupuestario — Entrypoint principal.

Usa st.navigation() con secciones agrupadas para construir
el sidebar de navegación MPA. La sección "Administración"
solo es visible para usuarios con rol admin.
"""

import streamlit as st

from src.services import auth_service

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
# Login
# ──────────────────────────────────────────────
def render_login() -> None:
    """Renderiza el formulario de login y registro de forma compacta."""
    # Usamos columnas para centrar el formulario y que no ocupe todo el ancho
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.title("Acceso al Sistema")

        tab_login, tab_register = st.tabs(["🔒 Iniciar Sesión", "📝 Registrarse"])

        with tab_login:
            st.info("Ingrese sus credenciales para continuar.")
            with st.form("login_form"):
                username = st.text_input("Usuario", key="login_username")
                password = st.text_input(
                    "Contraseña", type="password", key="login_password"
                )
                submitted = st.form_submit_button("Ingresar", use_container_width=True)

                if submitted:
                    with st.spinner("Autenticando en el Sistema..."):
                        try:
                            token = auth_service.login(username, password)
                            st.session_state["token"] = token

                            user_data = auth_service.get_current_user(token)
                            st.session_state["user"] = {
                                "role": user_data.role.value,
                                "username": user_data.username,
                                "id": user_data.id,
                            }
                            st.rerun()

                        except auth_service.AuthenticationError as e:
                            st.error(f"Error de acceso: {e}")
                        except auth_service.APIError as e:
                            st.error(f"Error en el servidor: {e}")
                        except Exception as e:
                            st.error(f"Ocurrió un error inesperado. {e}")

        with tab_register:
            st.info("Complete los datos para crear una nueva cuenta.")
            with st.form("register_form"):
                new_user = st.text_input("Usuario deseado", key="reg_username")
                new_pass = st.text_input(
                    "Contraseña", type="password", key="reg_password"
                )
                conf_pass = st.text_input(
                    "Confirmar Contraseña", type="password", key="reg_confirm"
                )
                submitted_reg = st.form_submit_button(
                    "Crear Cuenta", use_container_width=True
                )

                if submitted_reg:
                    if not new_user or not new_pass:
                        st.error("Todos los campos son obligatorios.")
                    elif new_pass != conf_pass:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        with st.spinner("Registrando usuario..."):
                            try:
                                auth_service.register(new_user, new_pass)
                                st.success(
                                    "✅ Registro solicitado exitosamente. "
                                    "Ahora puede intentar iniciar sesión."
                                )
                            except auth_service.APIResponseError as e:
                                st.error(f"Error de registro: {e}")
                            except Exception as e:
                                st.error(f"Error inesperado: {e}")


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


if __name__ == "__main__":
    main()

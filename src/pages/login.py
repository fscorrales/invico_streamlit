import streamlit as st

import src.utils.exceptions as ex
from src.services.auth_service import get_current_user, login, register


# --------------------------------------------------
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
                            token = login(username, password)
                            st.session_state["token"] = token

                            user_data = get_current_user(token)
                            st.session_state["user"] = {
                                "role": user_data.role.value,
                                "username": user_data.username,
                                "id": user_data.id,
                            }
                            st.rerun()

                        except ex.AuthenticationError as e:
                            st.error(f"Error de acceso: {e}")
                        except ex.APIConnectionError as e:
                            st.error(f"Error de conexión: {e}")
                        except ex.APIResponseError as e:
                            st.error(f"Error en el servidor: {e}")
                        except ex.ValidationError as e:
                            st.error(f"Dato inválido: {e}")
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
                                register(new_user, new_pass)
                                st.success(
                                    "✅ Registro solicitado exitosamente. "
                                    "Ahora puede intentar iniciar sesión."
                                )
                            except ex.APIResponseError as e:
                                st.error(f"Error de registro: {e}")
                            except Exception as e:
                                st.error(f"Error inesperado: {e}")

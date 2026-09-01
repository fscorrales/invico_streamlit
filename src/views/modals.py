__all__ = [
    "request_siif_credentials_modal",
    "request_sscc_credentials_modal",
    "request_sgf_credentials_modal",
    "request_siif_and_sscc_credentials_modal",
    "request_siif_and_sgf_credentials_modal",
    "request_siif_sscc_and_sgf_credentials_modal",
]

import time
from typing import Any, Callable

import streamlit as st

from src.components import button_cancel, button_robot


@st.dialog("Credenciales SIIF")
# --------------------------------------------------
def request_siif_credentials_modal(
    automation_callback: Callable[[str, str, str], None],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para solicitar credenciales del SIIF.
    automation_callback recibe (username, password, key).
    """
    st.write("Ingrese sus credenciales de SIIF para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if not username or not password:
                st.error("Debe ingresar usuario y contraseña.")
                return

            try:
                with st.spinner("Ejecutando automatización..."):
                    st.info("Automatización iniciada. Por favor, espere...")

                    import asyncio
                    import sys

                    # SOLUCIÓN PARA WINDOWS
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsProactorEventLoopPolicy()
                        )

                    async def run_automation():
                        return await automation_callback(username, password, key)

                try:
                    results = asyncio.run(run_automation())
                except RuntimeError:
                    # Si ya hay un loop corriendo (común en Streamlit)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(run_automation())

                st.success(f"Proceso finalizado: {len(results)} reportes procesados.")
                st.session_state[f"{key}_automation_success"] = True
                time.sleep(1)
                st.rerun()
                # st.success("✅ Proceso de actualización completado")

                # # Creamos un contenedor expandible para no ensuciar la vista si todo salió bien
                # with st.expander("Ver detalle del procesamiento", expanded=True):
                #     # Mostramos métricas rápidas
                #     c1, c2, c3 = st.columns(3)
                #     total_added = sum(r["added"] for r in results)
                #     total_deleted = sum(r["deleted"] for r in results)
                #     total_errors = sum(len(r["errors"]) for r in results)

                #     c1.metric("Registros Agregados", total_added)
                #     c2.metric("Registros Eliminados", total_deleted)
                #     c3.metric("Errores detectados", total_errors, delta_color="inverse")

                #     # Si hay errores, los mostramos en una tabla o lista roja
                #     if total_errors > 0:
                #         st.markdown("---")
                #         st.error("⚠️ Algunos registros no pudieron procesarse:")
                #         for res in results:
                #             for err in res["errors"]:
                #                 st.write(
                #                     f"**Doc ID {err['doc_id']}:** {err['details'][0]['msg']}"
                #                 )

            except Exception as e:
                st.error(f"Error durante la automatización: {e}")
                st.session_state[f"{key}_automation_success"] = False

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )


@st.dialog("Credenciales SSCC")
# --------------------------------------------------
def request_sscc_credentials_modal(
    automation_callback: Callable[[str, str], Any],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para SSCC usando Pywinauto (Síncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SSCC para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    username = st.text_input("Usuario", key=f"sscc_user_{key}")
    password = st.text_input("Contraseña", type="password", key=f"sscc_pass_{key}")
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if not username or not password:
                st.error("Debe completar ambos campos.")
                return

            try:
                # En Pywinauto, el spinner es vital porque el navegador/app
                # puede tardar segundos en reaccionar.
                with st.spinner(
                    "🤖 Robot SSCC en ejecución... Por favor, no mueva el mouse."
                ):
                    # Ejecución Directa (Síncrona)
                    # Al no ser async, no necesitamos loop, ni Proactor, ni await.
                    results = automation_callback(username, password)

                if results:
                    st.success(f"Proceso finalizado: {results}.")
                    st.session_state[f"{key}_automation_success"] = True
                else:
                    st.info("Proceso terminado sin resultados nuevos.")

                # Esperamos un segundo para que el usuario vea el éxito antes de recargar
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en la automatización SSCC: {str(e)}")
                st.session_state[f"{key}_automation_success"] = False

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )


@st.dialog("Credenciales SGF")
# --------------------------------------------------
def request_sgf_credentials_modal(
    automation_callback: Callable[[str, str], Any],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para SGF usando Pywinauto (Síncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SGF para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    username = st.text_input("Usuario", key=f"sgf_user_{key}")
    password = st.text_input("Contraseña", type="password", key=f"sgf_pass_{key}")
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if not username or not password:
                st.error("Debe completar ambos campos.")
                return

            try:
                # En Pywinauto, el spinner es vital porque el navegador/app
                # puede tardar segundos en reaccionar.
                with st.spinner(
                    "🤖 Robot SGF en ejecución... Por favor, no mueva el mouse."
                ):
                    # Ejecución Directa (Síncrona)
                    # Al no ser async, no necesitamos loop, ni Proactor, ni await.
                    results = automation_callback(username, password)

                if results:
                    st.success(f"Proceso finalizado: {results}.")
                    st.session_state[f"{key}_automation_success"] = True
                else:
                    st.info("Proceso terminado sin resultados nuevos.")

                # Esperamos un segundo para que el usuario vea el éxito antes de recargar
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en la automatización SGF: {str(e)}")
                st.session_state[f"{key}_automation_success"] = False

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )


@st.dialog("Credenciales SIIF y SSCC")
# --------------------------------------------------
def request_siif_and_sscc_credentials_modal(
    automation_callback: Callable[[str, str, str, str, str], Any],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para SIIF y SSCC usando Pywinauto (Síncrono) y Playwright (Asíncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SIIF y SSCC para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    siif_username = st.text_input("Usuario SIIF", key=f"siif_user_{key}")
    siif_password = st.text_input(
        "Contraseña SIIF", type="password", key=f"siif_pass_{key}"
    )
    sscc_username = st.text_input("Usuario SSCC", key=f"sscc_user_{key}")
    sscc_password = st.text_input(
        "Contraseña SSCC", type="password", key=f"sscc_pass_{key}"
    )
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if (
                not siif_username
                or not siif_password
                or not sscc_username
                or not sscc_password
            ):
                st.error("Debe completar todos los campos.")
                return

            try:
                # En Pywinauto, el spinner es vital porque el navegador/app
                # puede tardar segundos en reaccionar.
                with st.spinner(
                    "🤖 Robot en ejecución... Por favor, no mueva el mouse."
                ):
                    import asyncio
                    import sys

                    # SOLUCIÓN PARA WINDOWS
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsProactorEventLoopPolicy()
                        )

                    async def run_automation():
                        return await automation_callback(
                            siif_username,
                            siif_password,
                            sscc_username,
                            sscc_password,
                            key,
                        )

                try:
                    results = asyncio.run(run_automation())
                except RuntimeError:
                    # Si ya hay un loop corriendo (común en Streamlit)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(run_automation())

                if results:
                    st.success(
                        f"Proceso finalizado: {len(results)} reportes procesados."
                    )
                    st.session_state[f"{key}_automation_success"] = True
                else:
                    st.info("Proceso terminado sin resultados nuevos.")

                # Esperamos un segundo para que el usuario vea el éxito antes de recargar
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en la automatización SIIF y SSCC: {str(e)}")

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )


@st.dialog("Credenciales SIIF y SGF")
# --------------------------------------------------
def request_siif_and_sgf_credentials_modal(
    automation_callback: Callable[[str, str, str, str, str], Any],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para SIIF y SGF usando Pywinauto (Síncrono) y Playwright (Asíncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SIIF y SGF para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    siif_username = st.text_input("Usuario SIIF", key=f"siif_user_{key}")
    siif_password = st.text_input(
        "Contraseña SIIF", type="password", key=f"siif_pass_{key}"
    )
    sgf_username = st.text_input("Usuario SGF", key=f"sscc_user_{key}")
    sgf_password = st.text_input(
        "Contraseña SGF", type="password", key=f"sscc_pass_{key}"
    )

    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if (
                not siif_username
                or not siif_password
                or not sgf_username
                or not sgf_password
            ):
                st.error("Debe completar todos los campos.")
                return

            try:
                # En Pywinauto, el spinner es vital porque el navegador/app
                # puede tardar segundos en reaccionar.
                with st.spinner(
                    "🤖 Robot en ejecución... Por favor, no mueva el mouse."
                ):
                    import asyncio
                    import sys

                    # SOLUCIÓN PARA WINDOWS
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsProactorEventLoopPolicy()
                        )

                    async def run_automation():
                        return await automation_callback(
                            siif_username,
                            siif_password,
                            sgf_username,
                            sgf_password,
                            key,
                        )

                try:
                    results = asyncio.run(run_automation())
                except RuntimeError:
                    # Si ya hay un loop corriendo (común en Streamlit)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(run_automation())

                if results:
                    st.success(
                        f"Proceso finalizado: {len(results)} reportes procesados."
                    )
                    st.session_state[f"{key}_automation_success"] = True
                else:
                    st.info("Proceso terminado sin resultados nuevos.")

                # Esperamos un segundo para que el usuario vea el éxito antes de recargar
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en la automatización SIIF y SGF: {str(e)}")

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )


@st.dialog("Credenciales SIIF, SSCC y SGF")
# --------------------------------------------------
def request_siif_sscc_and_sgf_credentials_modal(
    automation_callback: Callable[[str, str, str, str, str, str, str], Any],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para SIIF y SGF usando Pywinauto (Síncrono) y Playwright (Asíncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SIIF, SSCC y SGF para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    siif_username = st.text_input("Usuario SIIF", key=f"siif_user_{key}")
    siif_password = st.text_input(
        "Contraseña SIIF", type="password", key=f"siif_pass_{key}"
    )
    sscc_username = st.text_input("Usuario SSCC", key=f"sscc_user_{key}")
    sscc_password = st.text_input(
        "Contraseña SSCC", type="password", key=f"sscc_pass_{key}"
    )
    sgf_username = st.text_input("Usuario SGF", key=f"sgf_user_{key}")
    sgf_password = st.text_input(
        "Contraseña SGF", type="password", key=f"sgf_pass_{key}"
    )

    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if (
                not siif_username
                or not siif_password
                or not sscc_username
                or not sscc_password
                or not sgf_username
                or not sgf_password
            ):
                st.error("Debe completar todos los campos.")
                return

            try:
                # En Pywinauto, el spinner es vital porque el navegador/app
                # puede tardar segundos en reaccionar.
                with st.spinner(
                    "🤖 Robot en ejecución... Por favor, no mueva el mouse."
                ):
                    import asyncio
                    import sys

                    # SOLUCIÓN PARA WINDOWS
                    if sys.platform == "win32":
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsProactorEventLoopPolicy()
                        )

                    async def run_automation():
                        return await automation_callback(
                            siif_username,
                            siif_password,
                            sscc_username,
                            sscc_password,
                            sgf_username,
                            sgf_password,
                            key,
                        )

                try:
                    results = asyncio.run(run_automation())
                except RuntimeError:
                    # Si ya hay un loop corriendo (común en Streamlit)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(run_automation())

                if results:
                    st.success(
                        f"Proceso finalizado: {len(results)} reportes procesados."
                    )
                    st.session_state[f"{key}_automation_success"] = True
                else:
                    st.info("Proceso terminado sin resultados nuevos.")

                # Esperamos un segundo para que el usuario vea el éxito antes de recargar
                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error en la automatización SIIF y SGF: {str(e)}")

        st.write(
            "**Debe esperar a que este MODAL se cierre automáticamente al finalizar la automatización.**"
        )

from typing import Callable

import streamlit as st


@st.dialog("Credenciales SIIF")
# --------------------------------------------------
def request_siif_credentials_modal(automation_callback: Callable[[str, str], None]):
    """
    Modal reutilizable para solicitar credenciales del SIIF.
    automation_callback recibe (username, password).
    """
    st.write("Ingrese sus credenciales de SIIF para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar Automatización"):
        if not username or not password:
            st.error("Debe ingresar usuario y contraseña.")
            return

        try:
            with st.spinner("Ejecutando automatización..."):
                import asyncio
                import sys

                # SOLUCIÓN PARA WINDOWS
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(
                        asyncio.WindowsProactorEventLoopPolicy()
                    )

                async def run_automation():
                    return await automation_callback(username, password)

            try:
                results = asyncio.run(run_automation())
            except RuntimeError:
                # Si ya hay un loop corriendo (común en Streamlit)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(run_automation())

            st.success(f"Proceso finalizado: {len(results)} reportes procesados.")
            st.rerun()

        except Exception as e:
            st.error(f"Error durante la automatización: {e}")


@st.dialog("Credenciales SSCC")
# --------------------------------------------------
def request_sscc_credentials_modal(automation_callback: Callable[[str, str], None]):
    """
    Modal reutilizable para solicitar credenciales del SSCC.
    automation_callback recibe (username, password).
    """
    st.write("Ingrese sus credenciales de SSCC para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar Automatización"):
        if not username or not password:
            st.error("Debe ingresar usuario y contraseña.")
            return

        try:
            with st.spinner("Ejecutando automatización..."):
                import asyncio
                import sys

                # SOLUCIÓN PARA WINDOWS
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(
                        asyncio.WindowsProactorEventLoopPolicy()
                    )

                async def run_automation():
                    return await automation_callback(username, password)

            try:
                results = asyncio.run(run_automation())
            except RuntimeError:
                # Si ya hay un loop corriendo (común en Streamlit)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(run_automation())

            st.success(f"Proceso finalizado: {len(results)} reportes procesados.")
            st.rerun()

        except Exception as e:
            st.error(f"Error durante la automatización: {e}")

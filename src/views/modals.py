from typing import Any, Callable

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
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"Error durante la automatización: {e}")


@st.dialog("Credenciales SSCC")
# --------------------------------------------------
def request_sscc_credentials_modal(automation_callback: Callable[[str, str], Any]):
    """
    Modal reutilizable para SSCC usando Pywinauto (Síncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.
    """
    st.write(
        "Ingrese sus credenciales de SSCC para iniciar la automatización de escritorio."
    )

    # Usamos keys únicas para evitar colisiones con otros modales
    username = st.text_input("Usuario", key="sscc_user")
    password = st.text_input("Contraseña", type="password", key="sscc_pass")

    if st.button("Lanzar Robot SSCC", type="primary"):
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
                st.success(f"Proceso finalizado: {len(results)} reportes procesados.")
            else:
                st.info("Proceso terminado sin resultados nuevos.")

            # Esperamos un segundo para que el usuario vea el éxito antes de recargar
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error en la automatización SSCC: {str(e)}")

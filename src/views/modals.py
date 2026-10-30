__all__ = [
    "request_siif_credentials_modal",
    "request_sscc_credentials_modal",
    "request_sgf_credentials_modal",
    "request_siif_and_sscc_credentials_modal",
    "request_siif_and_sgf_credentials_modal",
    "request_siif_sscc_and_sgf_credentials_modal",
    "modal_delete_registro_gral",
    "modal_obras_recuperadas",
    "request_sgv_credentials_modal",
]

import re
import time
from datetime import datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from src.components import button_cancel, button_robot, button_skip, button_submit
from src.constants.endpoints import Endpoints
from src.models.schemas import ObrasRecuperadasReport
from src.services.api_client import delete_request, post_request, put_request
from src.services.data_fetcher import get_ejercicios_list, get_obras_recuperadas
from src.utils.exceptions import AppBaseException
from src.utils.transform_data import parse_moneda_ar
from src.views.aux_tables import report_data_version_key


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
    Permite omitir la descarga para no ejecutar la automatización.
    """
    st.write("Ingrese sus credenciales de SIIF para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="medium"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_skip(
            "Omitir",
            key=f"{key}_btn_skip",
            help="Saltea la descarga del reporte y actualiza la vista con los datos ya cargados.",
        ):
            # No se ejecuta la automatización: solo se refresca la vista
            st.session_state[f"{key}_automation_success"] = True
            st.rerun()

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if not username or not password:
                st.error("Debe ingresar usuario y contraseña.")
                return

            if automation_callback is None:
                st.error(
                    "No hay ninguna automatización configurada para este reporte. "
                    "Utilice 'Omitir' para continuar sin descargar."
                )
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
    skip_callback: Callable[[], Any] | None = None,
):
    """
    Modal reutilizable para SIIF y SSCC usando Pywinauto (Síncrono) y Playwright (Asíncrono).
    automation_callback recibe (username, password) y devuelve la lista de resultados.

    El botón "Omitir" saltea la descarga de reportes sin requerir
    credenciales:

    - Con ``skip_callback``: se ejecuta ese callback (p.ej. recalcular el
      cruce con los datos ya presentes en la API) y luego se refresca la
      vista mediante el flag ``{key}_automation_success``.
    - Sin ``skip_callback``: solo se refresca la vista con los datos ya
      cargados (mismo comportamiento que el "Omitir" de
      :func:`request_siif_credentials_modal`).
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
        horizontal=True, border=False, horizontal_alignment="center", gap="medium"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_skip(
            "Omitir",
            key=f"{key}_btn_skip",
            help=(
                "Saltea la descarga de reportes. Si hay un callback "
                "configurado, recalcula con los datos ya cargados; "
                "sino, solo actualiza la vista."
            ),
        ):
            if skip_callback is None:
                # Sin callback: no se ejecuta ninguna automatización,
                # solo se refresca la vista con los datos ya cargados
                # (mismo comportamiento que request_siif_credentials_modal).
                st.session_state[f"{key}_automation_success"] = True
                st.rerun()
            else:
                try:
                    with st.spinner(
                        "Omitiendo descargas... "
                        "Recalculando con los datos ya cargados..."
                    ):
                        skip_callback()

                    st.success("Proceso finalizado sin descargar reportes.")
                    st.session_state[f"{key}_automation_success"] = True
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al omitir la descarga: {e}")
                    st.session_state[f"{key}_automation_success"] = False

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


# --------------------------------------------------
def _a_texto(valor: Any) -> str:
    """
    Convierte escalares de ``pandas``/``numpy`` a ``str`` saneado.

    Normaliza ``None``, ``numpy.nan``, ``pd.NA`` y ``pd.NaT`` a cadena
    vacía. Necesario porque ``DataFrame.to_dict()``
    (usado por la grilla para pasar ``datos_carga``) puede traer ``NaN``
    en campos opcionales como ``cuit``, y ``NaN`` no es JSON válido.

    Args:
        valor: Cualquier escalar proveniente de una fila del DataFrame.

    Returns:
        Cadena limpia (vacía si el valor era nulo).
    """
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor
    if pd.isna(valor):  # numpy.nan, pd.NA, pd.NaT
        return ""
    if isinstance(valor, float) and valor.is_integer():
        # Float entero (p.ej. 354.0): pierde la parte decimal para
        # coincidir con el valor canónico "354" de las referencias.
        return str(int(valor))
    return str(valor)


# --- MODAL: ELIMINAR COMPROBANTE GENERICO ---
@st.dialog("Confirmar Eliminación PERMANENTE", width="small")
def modal_delete_registro_gral(
    endpoint: str,
    desc_registro: str,
    session_state_update_key: str = None,
    key_prefix: str = "",
):
    # ``st.session_state`` es la fuente de verdad del token y SÍ está
    # disponible dentro de ``@st.dialog``. Lo leemos y lo pasamos
    # explícito a ``delete_request`` (``_get_headers()`` haría la misma
    # lectura como fallback).
    token = st.session_state.get("token")

    st.warning(
        f"⚠️ ¿Estás seguro de que deseás eliminar el registro **{desc_registro}**?"
    )
    st.write(
        "Esta acción es permanente y también eliminará todas las retenciones asociadas."
    )

    st.markdown("---")
    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", key=f"{key_prefix}_btn_cancel", type="secondary"):
            st.rerun()

        if button_submit("Si, Eliminar", key=f"{key_prefix}_btn_eliminar"):
            with st.spinner("Eliminando registro..."):
                try:
                    # El token explícito ya viene de ``st.session_state``
                    # (leído al iniciar este modal).
                    res = delete_request(endpoint, token=token)

                    if res:
                        st.success("Registro eliminado correctamente.")
                        if session_state_update_key:
                            if session_state_update_key not in st.session_state:
                                st.session_state[session_state_update_key] = 0
                            else:
                                st.session_state[session_state_update_key] += 1

                    else:
                        st.error(
                            "Error al eliminar el registro. Por favor, intenta nuevamente."
                        )

                    time.sleep(2)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al eliminar: {e}")


# --- MODAL: AGREGAR / EDITAR OBRA RECUPERADA ---
@st.dialog("Agregar / Editar OBRA RECUPERADA", width="medium")
def modal_obras_recuperadas(
    key_prefix: str,
    datos_carga: dict[str, Any] | None = None,
    es_edicion: bool = False,
    session_state_update_key: str = report_data_version_key("obras_recuperadas"),
) -> None:
    """
    Modal para dar de alta o editar una obra recuperada.

    Opera sobre la colección ``sgv_obras_recuperadas`` con los campos
    de ``models.schemas.ObrasRecuperadasReport``:

    - **Alta** (``es_edicion=False``): ``POST .../add_one`` (el Back
      genera el ``id``).
    - **Edición** (``es_edicion=True``): ``PUT .../update_one/{id}``.

    Los ``selectbox`` de Cód. Barrio y Estructura se poblan con los
    valores únicos de la propia colección
    (:func:`get_obras_recuperadas`) y aceptan opciones nuevas
    (``accept_new_options=True``). Si esa lectura falla se informa con
    ``st.warning`` y los combos quedan en modo escritura libre.

    Args:
        key_prefix: Prefijo único para las keys de los widgets (con
            timestamp con microsegundos, igual que el resto de modales).
        datos_carga: Fila a editar (``df.iloc[i].to_dict()``); ``None``
            en modo alta.
        es_edicion: ``True`` envía ``PUT .../update_one/{id}`` en vez de
            ``POST .../add_one``.
        session_state_update_key: Clave de ``st.session_state`` a
            incrementar tras guardar, para refrescar la grilla.
    """
    # ``st.session_state`` es la fuente de verdad del token y SÍ está
    # disponible dentro de ``@st.dialog``. Lo leemos y lo pasamos
    # explícito a ``post_request``/``put_request``; ``get_obras_recuperadas``
    # usa el fallback de ``_get_headers()``, que lee el mismo valor.
    token = st.session_state.get("token")

    # pandas NaN/NA/NaT -> None (JSON-compliant; igual que modal_precarizado).
    form_data: dict[str, Any] = {}
    if datos_carga:
        form_data = {
            campo: (None if pd.isna(valor) else valor)
            for campo, valor in datos_carga.items()
        }

    # ── Referencias: valores únicos de la propia colección ──
    update_trigger = int(st.session_state.get(session_state_update_key, 0))
    try:
        df_referencia = get_obras_recuperadas(update_trigger=update_trigger)
    except AppBaseException as exc:
        # No silenciamos: informamos y dejamos los selectbox en modo
        # escritura libre (accept_new_options=True) como fallback.
        st.warning(f"⚠️ No se pudieron cargar las referencias: {exc}")
        df_referencia = pd.DataFrame()

    cod_barrios: list[str] = []
    estructuras: list[str] = []
    if not df_referencia.empty:
        if "cod_barrio" in df_referencia.columns:
            cod_barrios = sorted(
                {_a_texto(v).strip() for v in df_referencia["cod_barrio"]} - {""}
            )
        if "estructura" in df_referencia.columns:
            estructuras = sorted(
                {_a_texto(v).strip() for v in df_referencia["estructura"]} - {""}
            )

    # En edición, el valor previo debe estar siempre entre las opciones.
    cod_barrio_previo = _a_texto(form_data.get("cod_barrio")).strip()
    estructura_previa = _a_texto(form_data.get("estructura")).strip()
    if cod_barrio_previo and cod_barrio_previo not in cod_barrios:
        cod_barrios = [cod_barrio_previo, *cod_barrios]
    if estructura_previa and estructura_previa not in estructuras:
        estructuras = [estructura_previa, *estructuras]

    # Ejercicios: lista local (sin API); alta = último (año en curso).
    ejercicios: list[int] = get_ejercicios_list()
    ejercicio_inicial: int = ejercicios[-1]
    if es_edicion and form_data.get("ejercicio") is not None:
        ejercicio_inicial = int(form_data["ejercicio"])
    if ejercicio_inicial not in ejercicios:
        ejercicios = [ejercicio_inicial, *ejercicios]

    importe_inicial: float = 0.0
    if es_edicion and form_data.get("importe") is not None:
        # La grilla muestra ``importe`` con ``formato_moneda_ar`` (antes de
        # llegar al modal); ``parse_moneda_ar`` es su inverso y acepta tanto
        # el crudo como la cadena formateada ("$ 1.234,56"). ``float()`` aquí
        # lanzaba ValueError al editar un registro.
        importe_inicial = parse_moneda_ar(form_data["importe"])

    # Estado inicial de los widgets ANTES de crearlos (patrón setdefault
    # recomendado por Streamlit: evita el warning "value + session state").
    st.session_state.setdefault(f"{key_prefix}_ejercicio", ejercicio_inicial)
    st.session_state.setdefault(f"{key_prefix}_cod_barrio", cod_barrio_previo or None)
    st.session_state.setdefault(f"{key_prefix}_estructura", estructura_previa or None)
    st.session_state.setdefault(f"{key_prefix}_importe", importe_inicial)
    st.session_state.setdefault(f"{key_prefix}_notas", _a_texto(form_data.get("notas")))

    col_ejercicio, col_barrio = st.columns(2)
    ejercicio = col_ejercicio.selectbox(
        "Ejercicio",
        options=ejercicios,
        key=f"{key_prefix}_ejercicio",
        help="Ejercicio (año) al que pertenece la obra recuperada.",
    )
    # accept_new_options=True: sugiere valores ya cargados pero permite
    # ingresar códigos de barrio nuevos.
    cod_barrio = col_barrio.selectbox(
        "Cód. Barrio",
        options=cod_barrios,
        key=f"{key_prefix}_cod_barrio",
        placeholder="Escriba o elija un Cód. de Barrio.",
        accept_new_options=True,
        help="Código de barrio del padrón (ej: 884).",
    )

    col_estructura, col_importe = st.columns([2, 1])
    estructura = col_estructura.selectbox(
        "Estructura",
        options=estructuras,
        key=f"{key_prefix}_estructura",
        placeholder="Escriba o elija una Estructura.",
        accept_new_options=True,
        help="Formato requerido: 00-00-00-00-000 (ej: 11-00-02-79-421).",
    )
    importe = col_importe.number_input(
        "Importe",
        key=f"{key_prefix}_importe",
        step=0.01,
        format="%.2f",
        help="Importe de la recuperación (acepta negativos).",
    )

    notas = st.text_area(
        "Notas",
        key=f"{key_prefix}_notas",
        height=100,
        help="Observaciones u otra información relevante (opcional).",
    )

    if es_edicion:
        st.caption(
            f"Registro ID: `{form_data.get('id')}` | "
            f"Última actualización: {form_data.get('updated_at') or '—'}"
        )

    st.markdown("---")

    # BOTONES (Cancelar / Agregar o Editar)
    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="large"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key_prefix}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_submit(
            "Editar" if es_edicion else "Agregar",
            key=f"{key_prefix}_btn_add",
        ):
            # 1. Validación de datos
            errores: list[str] = []
            ejercicio_sel = ejercicio  # selectbox: siempre un int válido
            cod_barrio_limpio = _a_texto(cod_barrio).strip()
            estructura_limpia = _a_texto(estructura).strip()
            notas_limpia = _a_texto(notas).strip()
            importe_limpio = float(importe)  # number_input: numérico

            if not cod_barrio_limpio:
                errores.append("Debe indicar el Cód. de Barrio.")
            elif not re.fullmatch(r"\d{1,4}", cod_barrio_limpio):
                errores.append(
                    "El Cód. de Barrio debe contener de 1 a 4 dígitos (ej: 884)."
                )
            if not estructura_limpia:
                errores.append("Debe indicar la Estructura.")
            elif not re.fullmatch(r"\d{2}-\d{2}-\d{2}-\d{2}-\d{3}", estructura_limpia):
                errores.append(
                    "La Estructura debe tener el formato 00-00-00-00-000 "
                    "(ej: 11-00-02-79-421)."
                )

            registro_id = _a_texto(form_data.get("id"))
            if es_edicion and not registro_id:
                errores.append("El registro a editar no tiene un ID válido.")

            if errores:
                for err in errores:
                    st.toast(err, icon="⚠️")
                return

            # 2. Payload ajustado al esquema de la colección
            # ``sgv_obras_recuperadas`` (models.schemas.ObrasRecuperadasReport).
            payload: dict[str, Any] = {
                "ejercicio": int(ejercicio_sel),
                "cod_barrio": cod_barrio_limpio,
                "estructura": estructura_limpia,
                "importe": importe_limpio,
                "notas": notas_limpia,
            }
            # Cerrojo de concurrencia (el back filtra con
            # ``{"_id", "updated_at": <payload>}`` y devuelve 409 si no
            # matchea):
            # - Edición: eco LITERAL del ``updated_at`` original que trajo
            #   el GET. Enviar ``datetime.now()`` garantizaba 409 en el
            #   100% de las ediciones (nunca coincide con MongoDB).
            # - Alta: timestamp de creación (el POST no tiene cerrojo).
            if es_edicion:
                updated_at_original = form_data.get("updated_at")
                if not updated_at_original:
                    st.error(
                        "⚠️ El registro no incluye 'updated_at' (cerrojo de "
                        "edición). Recargue la página e intente nuevamente."
                    )
                    return
                payload["updated_at"] = updated_at_original
            else:
                payload["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Validación estricta: si algo falla, NO se envía nada.
            try:
                ObrasRecuperadasReport(**payload)
            except ValidationError as exc:
                st.error(f"⚠️ Los datos no cumplen ObrasRecuperadasReport: {exc}")
                return

            with st.spinner("Guardando obra recuperada..."):
                # 3. Alta: POST /add_one - Edición: PUT /update_one/{id}
                # token explícito leído de ``st.session_state`` al abrir el modal.
                try:
                    if es_edicion:
                        res = put_request(
                            endpoint=(
                                f"{Endpoints.OBRAS_RECUPERADAS.value}"
                                f"/update_one/{registro_id}"
                            ),
                            json_body=payload,
                            token=token,
                        )
                    else:
                        res = post_request(
                            endpoint=(f"{Endpoints.OBRAS_RECUPERADAS.value}/add_one"),
                            json_body=payload,
                            token=token,
                        )
                except AppBaseException as exc:
                    st.error(f"⚠️ {exc}")
                    return
                except Exception as exc:
                    st.error(f"❌ Ocurrió un error inesperado: {exc}")
                    return

                if not res:
                    st.error(
                        "La API no confirmó la operación. "
                        "Verifique e intente nuevamente."
                    )
                    return

                st.snow()
                st.toast(
                    f"✅ Obra Recuperada {estructura_limpia} "
                    f"{'editada' if es_edicion else 'agregada'} con éxito",
                    icon="📈",
                )

                # Invalida el caché de la grilla (@st.cache_data).
                st.session_state[session_state_update_key] = (
                    int(st.session_state.get(session_state_update_key, 0)) + 1
                )
                time.sleep(2)
                # Cierra el modal y recarga la página principal.
                st.rerun()


@st.dialog("Credenciales SGV")
# --------------------------------------------------
def request_sgv_credentials_modal(
    automation_callback: Callable[[str, str, str], None],
    key: str = "",
    downloaded_info: str = "-",
):
    """
    Modal reutilizable para solicitar credenciales del SGV.
    automation_callback recibe (username, password, key).
    Permite omitir la descarga para no ejecutar la automatización.
    """
    st.write("Ingrese sus credenciales de SGV para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    st.write("**Reportes ha descargar:** " + downloaded_info)

    with st.container(
        horizontal=True, border=False, horizontal_alignment="center", gap="medium"
    ):
        if button_cancel("Cancelar", type="secondary", key=f"{key}_btn_cancel"):
            st.rerun()  # Cierra el modal de forma segura

        if button_skip(
            "Omitir",
            key=f"{key}_btn_skip",
            help="Saltea la descarga del reporte y actualiza la vista con los datos ya cargados.",
        ):
            # No se ejecuta la automatización: solo se refresca la vista
            st.session_state[f"{key}_automation_success"] = True
            st.rerun()

        if button_robot("Ejecutar", key=f"{key}_btn_robot"):
            if not username or not password:
                st.error("Debe ingresar usuario y contraseña.")
                return

            if automation_callback is None:
                st.error(
                    "No hay ninguna automatización configurada para este reporte. "
                    "Utilice 'Omitir' para continuar sin descargar."
                )
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

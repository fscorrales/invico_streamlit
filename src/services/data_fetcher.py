__all__ = [
    "get_ejercicios",
    "get_sgf_origenes",
    "get_siif_rf602",
    "get_siif_rog01",
    "get_siif_rvicon03",
    "get_siif_rcocc31",
    "get_siif_ri102",
    "get_siif_rci02",
    "get_siif_rfp_p605b",
    "get_siif_rf610",
    "get_siif_rcg01_uejp",
    "get_siif_gto_rpa03g",
    "get_siif_rfondo07tp",
    "get_siif_rfondos04",
    "get_siif_rdeu012",
    "get_ctas_ctes",
    "get_ctas_ctes_list",
    "get_sscc_banco_invico",
    "get_sgf_resumen_rend_prov",
    "get_sgf_resumen_rend_obras",
    "get_tipos_comprobantes_siif_list",
    "get_grupos_partidas_siif_list",
    "get_grupos_partidas_str_siif_list",
    "get_partidas_principales_siif_list",
    "get_icaro_carga",
    "get_icaro_estructuras",
    "get_icaro_obras",
    "get_control_recursos",
    "get_control_obras",
    "get_control_icaro_anual",
    "get_control_icaro_comprobantes",
    "get_control_icaro_pa6",
    "get_control_banco_cruzado",
    "get_control_banco_siif",
    "get_control_banco_sscc",
    "get_reporte_planillometro_eecc",
]

import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.constants import Endpoints
from src.services.api_client import fetch_dataframe
from src.utils import get_cache_path


# --------------------------------------------------
@st.cache_data()
def get_ejercicios() -> list[int]:
    return list(range(2010, datetime.today().year + 1))


# --------------------------------------------------
@st.cache_data()
def get_sgf_origenes() -> list[str]:
    return ["EPAM", "OBRAS", "FUNCIONAMIENTO"]


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rf602(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RF602.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rog01(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_ROG01.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["partida"],
            ascending=[True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rvicon03(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RVICON03.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cta_contable"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rcocc31(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RCOCC31.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_entrada", "cta_contable"],
            ascending=[False, False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_ri102(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RI102.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cod_recurso", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rci02(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RCI02.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_entrada"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfp_p605b(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFP_P605B.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rf610(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RF610.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rcg01_uejp(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RCG01_UEJP.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_comprobante"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_gto_rpa03g(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_GTO_RPA03G.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_comprobante"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfondo07tp(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFONDO07TP.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "tipo_comprobante", "nro_comprobante"],
            ascending=[False, False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfondos04(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFONDOS04.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "tipo_comprobante", "nro_comprobante"],
            ascending=[False, False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rdeu012(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RDEU012.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "mes_hasta", "fecha", "nro_comprobante"],
            ascending=[False, True, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_ctas_ctes(filtro_avanzado: str = "", update_trigger: int = 0):
    file_path = os.path.join(get_cache_path(), "ctas_ctes_cache.parquet")

    # 1. Intentar cargar desde archivo local si no se fuerza la actualización
    # Si el trigger es 0, intentamos leer el archivo local primero
    if update_trigger == 0 and filtro_avanzado == "" and os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        # Si el archivo tiene menos de 24hs, lo usamos
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                return pd.read_parquet(file_path)
            except Exception:
                pass  # Si el parquet está corrupto, seguimos a la API

    # 2. Si no hay cache o es viejo, consultar API
    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    try:
        df = fetch_dataframe(Endpoints.CTAS_CTES.value, params=params_peticion)
        if not df.empty:
            # df = df.sort_values(["estructura"], ascending=True)
            # 3. Guardar en disco para la próxima vez
            if filtro_avanzado == "":
                df.to_parquet(file_path)
            return df

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Si falla la API pero hay un archivo viejo, lo usamos como backup
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)

    return pd.DataFrame()


@st.cache_data
# --------------------------------------------------
def get_ctas_ctes_list() -> list[str]:
    data = get_ctas_ctes(
        update_trigger=st.session_state.ctas_ctes_uploader_iteration
    ).copy()
    return data["map_to"].tolist()


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sscc_banco_invico(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SSCC_BANCO_INVICO.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "cta_cte"],
            ascending=[False, False, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sgf_resumen_rend_prov(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SGF_RESUMEN_REND_PROV.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "fecha", "cta_cte"],
    #         ascending=[False, False, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sgf_resumen_rend_obras(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SGF_RESUMEN_REND_OBRAS.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "fecha", "cta_cte"],
    #         ascending=[False, False, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...")
def get_tipos_comprobantes_siif_list(
    filtro_avanzado: str = "", update_trigger: int = 0
):
    file_path = os.path.join(get_cache_path(), "tipos_comprobantes_siif_cache.parquet")

    # 1. Intentar cargar desde archivo local si no se fuerza la actualización
    # Si el trigger es 0, intentamos leer el archivo local primero
    if update_trigger == 0 and filtro_avanzado == "" and os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        # Si el archivo tiene menos de 24hs, lo usamos
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                return pd.read_parquet(file_path)
            except Exception:
                pass  # Si el parquet está corrupto, seguimos a la API

    # 2. Si no hay cache o es viejo, consultar API
    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    try:
        df = fetch_dataframe(
            Endpoints.SIIF.value + "/tiposComprobantes", params=params_peticion
        )
        if not df.empty:
            # df = df.sort_values(["estructura"], ascending=True)
            # 3. Guardar en disco para la próxima vez
            if filtro_avanzado == "":
                df.to_parquet(file_path)
            return df

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Si falla la API pero hay un archivo viejo, lo usamos como backup
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)

    return pd.DataFrame()


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...")
def get_grupos_partidas_siif_list(filtro_avanzado: str = "", update_trigger: int = 0):
    file_path = os.path.join(get_cache_path(), "grupos_partidas_siif_cache.parquet")

    # 1. Intentar cargar desde archivo local si no se fuerza la actualización
    # Si el trigger es 0, intentamos leer el archivo local primero
    if update_trigger == 0 and filtro_avanzado == "" and os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        # Si el archivo tiene menos de 24hs, lo usamos
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                df = pd.read_parquet(file_path)
                return [str(x) for x in df[0].tolist()] if 0 in df.columns else []

            except Exception:
                pass  # Si el parquet está corrupto, seguimos a la API

    # 2. Si no hay cache o es viejo, consultar API
    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    try:
        df = fetch_dataframe(
            Endpoints.SIIF.value + "/gruposPartidas", params=params_peticion
        )
        if not df.empty:
            # df = df.sort_values(["estructura"], ascending=True)
            # 3. Guardar en disco para la próxima vez
            if filtro_avanzado == "":
                df.to_parquet(file_path)
            return [str(x) for x in df[0].tolist()] if 0 in df.columns else []

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Si falla la API pero hay un archivo viejo, lo usamos como backup
        if os.path.exists(file_path):
            df = pd.read_parquet(file_path)
            return [str(x) for x in df[0].tolist()] if 0 in df.columns else []

    return []


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...")
def get_grupos_partidas_str_siif_list(
    filtro_avanzado: str = "", update_trigger: int = 0
):
    file_path = os.path.join(get_cache_path(), "grupos_partidas_str_siif_cache.parquet")

    # 1. Intentar cargar desde archivo local si no se fuerza la actualización
    # Si el trigger es 0, intentamos leer el archivo local primero
    if update_trigger == 0 and filtro_avanzado == "" and os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        # Si el archivo tiene menos de 24hs, lo usamos
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                return pd.read_parquet(file_path)
            except Exception:
                pass  # Si el parquet está corrupto, seguimos a la API

    # 2. Si no hay cache o es viejo, consultar API
    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    try:
        df = fetch_dataframe(
            Endpoints.SIIF.value + "/gruposPartidasStr", params=params_peticion
        )
        if not df.empty:
            # df = df.sort_values(["estructura"], ascending=True)
            # 3. Guardar en disco para la próxima vez
            if filtro_avanzado == "":
                df.to_parquet(file_path)
            return df

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Si falla la API pero hay un archivo viejo, lo usamos como backup
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)

    return pd.DataFrame()


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...")
def get_partidas_principales_siif_list(
    filtro_avanzado: str = "", update_trigger: int = 0
):
    file_path = os.path.join(
        get_cache_path(), "partidas_principales_siif_cache.parquet"
    )

    # 1. Intentar cargar desde archivo local si no se fuerza la actualización
    # Si el trigger es 0, intentamos leer el archivo local primero
    if update_trigger == 0 and filtro_avanzado == "" and os.path.exists(file_path):
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        # Si el archivo tiene menos de 24hs, lo usamos
        if datetime.now() - mtime < timedelta(hours=24):
            try:
                return pd.read_parquet(file_path)
            except Exception:
                pass  # Si el parquet está corrupto, seguimos a la API

    # 2. Si no hay cache o es viejo, consultar API
    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    try:
        df = fetch_dataframe(
            Endpoints.SIIF.value + "/partidasPrincipales", params=params_peticion
        )
        if not df.empty:
            # df = df.sort_values(["estructura"], ascending=True)
            # 3. Guardar en disco para la próxima vez
            if filtro_avanzado == "":
                df.to_parquet(file_path)
            return df

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        # Si falla la API pero hay un archivo viejo, lo usamos como backup
        if os.path.exists(file_path):
            return pd.read_parquet(file_path)

    return pd.DataFrame()


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl=3600)
def get_icaro_carga(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.ICARO_CARGA.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_comprobante", "actividad", "partida", "fuente"],
            ascending=[False, False, False, True, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_icaro_estructuras(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    df = fetch_dataframe(Endpoints.ICARO_ESTRUCTURAS.value, params=params_peticion)
    if not df.empty:
        df = df.loc[:, ["estructura", "desc_estructura"]]
        df = df.sort_values(
            ["estructura"],
            ascending=[True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_icaro_obras(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    df = fetch_dataframe(Endpoints.ICARO_OBRAS.value, params=params_peticion)
    if not df.empty:
        df = df.sort_values(
            ["actividad", "partida", "fuente", "desc_obra"], ascending=True
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_recursos(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_RECURSOS.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "mes", "grupo", "cta_cte"],
            ascending=[False, True, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_obras(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_OBRAS.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_icaro_anual(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_ICARO_ANUAL.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_icaro_comprobantes(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_ICARO_COMPROBANTES.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_icaro_pa6(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_ICARO_PA6.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_banco_cruzado(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_BANCO_CRUZADO.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_banco_siif(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_BANCO_SIIF.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_banco_sscc(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.CONTROL_BANCO_SSCC.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_reporte_planillometro_eecc(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()
    print(params)

    df = fetch_dataframe(Endpoints.REPORTE_PLANILLOMETRO.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df

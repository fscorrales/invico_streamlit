__all__ = [
    "get_ejercicios_list",
    "get_sgf_origenes",
    "get_ctas_ctes",
    "get_ctas_ctes_list",
    "get_tipos_comprobantes_siif_list",
    "get_grupos_partidas_siif_list",
    "get_grupos_partidas_str_siif_list",
    "get_partidas_principales_siif_list",
    "get_control_recursos",
    "get_control_aporte_empresario",
    "get_control_banco_cruzado",
    "get_control_banco_siif",
    "get_control_banco_sscc",
    "get_referencias_obras_recuperadas",
    "get_referencias_obras_desactivadas",
]

import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from src.constants import Endpoints
from src.services.api_client import fetch_data, fetch_dataframe
from src.utils import get_cache_path


# --------------------------------------------------
@st.cache_data()
def get_ejercicios_list() -> list[int]:
    return list(range(2010, datetime.today().year + 1))


# --------------------------------------------------
@st.cache_data()
def get_sgf_origenes() -> list[str]:
    return ["EPAM", "OBRAS", "FUNCIONAMIENTO"]


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
def get_control_aporte_empresario(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    # Lee el snapshot persistido (POST posterior a /generateIcaro), igual
    # que get_control_recursos. El cómputo on-demand vive en el endpoint
    # /generateIcaro, al que solo llama compute_control_aporte_empresario().
    df = fetch_dataframe(Endpoints.CONTROL_APORTE_EMPRESARIO.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "mes", "cta_cte"],
            ascending=[True, True, True],
        )

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
def _normalizar_opciones(valores: list[Any]) -> list[str]:
    """
    Normaliza una lista de valores únicos devuelta por un endpoint ``unique*``.

    Convierte a ``str``, recorta espacios, descarta ``None``/vacíos y
    devuelve el resultado ordenado y sin duplicados. Es una capa
    defensiva: los endpoints ``uniqueCodBarrio``/``uniqueEstructura`` ya
    responden con ``sorted(distinct(...))``, pero así el frontend no
    depende de ese detalle de implementación del backend.

    Args:
        valores: Lista cruda proveniente de un endpoint ``unique*``.

    Returns:
        Lista ordenada de strings no vacíos, lista para ``options`` de
        un ``st.selectbox``.
    """
    normalizados = (str(valor).strip() for valor in valores if valor is not None)
    return sorted({valor for valor in normalizados if valor})


# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_referencias_obras_recuperadas(
    update_trigger: int = 0,
) -> tuple[list[str], list[str]]:
    """
    Referencias (Cód. Barrio y Estructura) para los combos del modal de
    obras recuperadas.

    Obtiene los valores únicos de dos colecciones del padrón mediante
    los endpoints ``distinct`` de MongoDB, con payload mínimo en lugar
    de descargar las colecciones completas:

    - ``cod_barrios``: ``GET /sgv/saldosBarriosEvolucion/uniqueCodBarrio``.
    - ``estructuras``: ``GET /reporte/reportePlanillometro/uniqueEstructura``.

    No persiste en Parquet: el ``@st.cache_data`` (TTL de 1 hora) es la
    única capa de caché, que evita llamadas repetidas a la API dentro
    del mismo TTL. Las excepciones no se cachean: se re-lanzan en cada
    invocación para que la UI pueda notificarlas.

    Args:
        update_trigger: Solo participa de la clave de caché (misma
            convención que el resto de la capa); incrementar para
            forzar la actualización.

    Returns:
        Tupla ``(cod_barrios, estructuras)`` con listas ordenadas de
        valores únicos y sin vacíos.

    Raises:
        APIConnectionError: Si la API falla.
        APIResponseError: Si la API retorna un error.
    """
    cod_barrios_crudos: list[Any] = fetch_data(
        f"{Endpoints.SALDOS_BARRIOS_EVOLUCION.value}/uniqueCodBarrio"
    )
    estructuras_crudas: list[Any] = fetch_data(
        f"{Endpoints.REPORTE_PLANILLOMETRO.value}/uniqueEstructura"
    )
    return (
        _normalizar_opciones(cod_barrios_crudos),
        _normalizar_opciones(estructuras_crudas),
    )


# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_referencias_obras_desactivadas(
    update_trigger: int = 0,
) -> tuple[list[str], list[str]]:
    """
    Referencias (Cta. Contable y Estructura) para los combos del modal
    de obras desactivadas.

    Obtiene los valores únicos mediante los endpoints ``distinct`` de
    MongoDB, con payload mínimo en lugar de descargar las colecciones
    completas:

    - ``cta_contables``:
      ``GET /sgv/obrasDesactivadas/uniqueCtaContable``.
    - ``estructuras``:
      ``GET /reporte/reportePlanillometro/uniqueEstructura`` (mismo
      padrón que :func:`get_referencias_obras_recuperadas`).

    No persiste en Parquet: el ``@st.cache_data`` (TTL de 1 hora) es la
    única capa de caché, que evita llamadas repetidas a la API dentro
    del mismo TTL. Las excepciones no se cachean: se re-lanzan en cada
    invocación para que la UI pueda notificarlas.

    Args:
        update_trigger: Solo participa de la clave de caché (misma
            convención que el resto de la capa); incrementar para
            forzar la actualización.

    Returns:
        Tupla ``(cta_contables, estructuras)`` con listas ordenadas de
        valores únicos y sin vacíos.

    Raises:
        APIConnectionError: Si la API falla.
        APIResponseError: Si la API retorna un error.
    """
    cta_contables_crudas: list[Any] = fetch_data(
        f"{Endpoints.OBRAS_DESACTIVADAS.value}/uniqueCtaContable"
    )
    estructuras_crudas: list[Any] = fetch_data(
        f"{Endpoints.REPORTE_PLANILLOMETRO.value}/uniqueEstructura"
    )
    return (
        _normalizar_opciones(cta_contables_crudas),
        _normalizar_opciones(estructuras_crudas),
    )

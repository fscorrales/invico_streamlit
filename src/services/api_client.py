"""
Cliente HTTP genérico para comunicación con la API de INVICO.

Encapsula las llamadas GET/PATCH con headers JWT desde session_state.
Todas las páginas deben usar este módulo en lugar de llamar a httpx
directamente.
"""

from typing import Any, Optional

import httpx
import pandas as pd
import streamlit as st

from ..config import settings

BASE_URL = settings.BASE_URL
DEFAULT_TIMEOUT = 30.0


class APIConnectionError(Exception):
    """Error de conexión con el servidor."""

    pass


class APIResponseError(Exception):
    """Error en la respuesta del servidor."""

    pass


def _get_headers() -> dict[str, str]:
    """Construye headers de autorización desde session_state."""
    token = st.session_state.get("token")
    if not token:
        raise APIConnectionError("No hay token de sesión. Inicie sesión nuevamente.")
    return {"Authorization": f"Bearer {token}"}


def fetch_data(
    endpoint: str,
    params: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Realiza un GET genérico a la API y retorna la lista de registros.

    Args:
        endpoint: Ruta relativa del endpoint (ej. "/siif/rf602/").
        params: Parámetros de query opcionales.

    Returns:
        Lista de diccionarios con los datos.

    Raises:
        APIConnectionError: Si no hay conexión.
        APIResponseError: Si la API retorna un error.
    """
    headers = _get_headers()
    clean_params = (
        {k: v for k, v in params.items() if v is not None} if params else None
    )

    try:
        response = httpx.get(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            params=clean_params,
            timeout=DEFAULT_TIMEOUT,
        )
    except httpx.RequestError as e:
        raise APIConnectionError(f"Error de conexión con el servidor: {e}") from e

    if response.status_code == 401:
        raise APIResponseError("Token expirado o inválido. Inicie sesión nuevamente.")
    if response.status_code != 200:
        raise APIResponseError(
            f"Error de API ({response.status_code}): {response.text}"
        )

    return response.json()


def fetch_dataframe(
    endpoint: str,
    params: Optional[dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Realiza un GET y retorna los datos como pd.DataFrame.

    Si no hay datos, retorna un DataFrame vacío.
    """
    data = fetch_data(endpoint, params)
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def patch_request(
    endpoint: str,
    json_body: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Realiza un PATCH genérico a la API.

    Args:
        endpoint: Ruta relativa del endpoint.
        json_body: Cuerpo JSON opcional.

    Returns:
        Diccionario con la respuesta.
    """
    headers = _get_headers()

    try:
        response = httpx.patch(
            f"{BASE_URL}{endpoint}",
            headers=headers,
            json=json_body,
            timeout=DEFAULT_TIMEOUT,
        )
    except httpx.RequestError as e:
        raise APIConnectionError(f"Error de conexión con el servidor: {e}") from e

    if response.status_code == 401:
        raise APIResponseError("Token expirado o inválido. Inicie sesión nuevamente.")
    if response.status_code != 200:
        raise APIResponseError(
            f"Error de API ({response.status_code}): {response.text}"
        )

    return response.json()

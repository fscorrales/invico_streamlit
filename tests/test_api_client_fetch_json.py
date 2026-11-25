"""Tests de ``fetch_json``.

El endpoint del cruce de Otros Gastos (``/control/otrosGastos/cruce``)
devuelve un payload compuesto ``{ejercicio, pareos, mensual}``, no una
lista de registros: ``fetch_dataframe`` asumiría una lista y perdiera
bloques. ``fetch_json`` devuelve el JSON cruda validado por
``_handle_response``.

Los tests son puros: se reemplaza ``httpx.get`` por respuestas fake,
sin red. Se pasa ``token`` explícito para no tocar ``st.session_state``
(fuera de un runtime de Streamlit).
"""

from typing import Any

import httpx
import pytest

from src.services import api_client
from src.services.api_client import fetch_json
from src.utils.exceptions import APIConnectionError, APIResponseError

ENDPOINT = "/control/otrosGastos/cruce"


# -------------------------------------------------
class _RespuestaFake:
    """Mínima interfaz de ``httpx.Response`` que usa ``_handle_response``."""

    def __init__(self, status_code: int, payload: Any = None, texto: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = texto

    def json(self) -> Any:
        return self._payload


# -------------------------------------------------
def test_fetch_json_devuelve_el_payload_compuesto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captura: dict[str, Any] = {}

    def _get(url: str, **kwargs: Any) -> _RespuestaFake:
        captura["url"] = url
        captura["params"] = kwargs.get("params")
        return _RespuestaFake(
            200, {"ejercicio": 2026, "pareos": [{"estado": "PAREADO"}], "mensual": []}
        )

    monkeypatch.setattr(api_client.httpx, "get", _get)

    bloque = fetch_json(ENDPOINT, params={"ejercicio": 2026, "vacio": None}, token="t")

    assert bloque["ejercicio"] == 2026
    assert bloque["pareos"] == [{"estado": "PAREADO"}]
    # Los params None se filtran (misma regla que fetch_data)
    assert captura["params"] == {"ejercicio": 2026}
    assert captura["url"].endswith(ENDPOINT)


# -------------------------------------------------
def test_fetch_json_404_lanza_api_response_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_client.httpx,
        "get",
        lambda *args, **kwargs: _RespuestaFake(404, texto="no existe"),
    )

    with pytest.raises(APIResponseError):
        fetch_json(ENDPOINT, token="t")


# -------------------------------------------------
def test_fetch_json_401_lanza_sesion_expirada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api_client.httpx, "get", lambda *args, **kwargs: _RespuestaFake(401)
    )

    with pytest.raises(APIResponseError, match="Sesión expirada"):
        fetch_json(ENDPOINT, token="t")


# -------------------------------------------------
def test_fetch_json_sin_red_lanza_api_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solicitud = httpx.Request("GET", "http://localhost/api")

    def _sin_red(*args: Any, **kwargs: Any) -> Any:
        raise httpx.RequestError("sin red", request=solicitud)

    monkeypatch.setattr(api_client.httpx, "get", _sin_red)

    with pytest.raises(APIConnectionError):
        fetch_json(ENDPOINT, token="t")

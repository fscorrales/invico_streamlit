"""
Tests de ``fetch_dataframe_paged``.

Cubren el fix del ``ReadTimeout`` en ``generate_banco_siif``: con
``limit=0``, ``/siif/rcocc31`` devuelve +47.000 registros en una sola
respuesta y agota ``DEFAULT_TIMEOUT`` (90s), abortando antes del POST y
dejando el snapshot desactualizado en $0.

Los tests son puros: se reemplaza ``fetch_data`` por un fake que devuelve
páginas en memoria, sin red.
"""

from typing import Any, Dict, List

import pandas as pd
import pytest

from src.services import api_client
from src.services.api_client import MAX_PAGED_ROWS, fetch_dataframe_paged

ENDPOINT = "/siif/rcocc31"


# -------------------------------------------------
def _make_pages(total: int, page_size: int) -> List[List[Dict[str, Any]]]:
    """Construye ``total`` registros repartidos en páginas de ``page_size``."""
    filas = [{"id": i, "cta_contable": f"2111-1-{i % 3}"} for i in range(total)]
    return [filas[i : i + page_size] for i in range(0, len(filas), page_size)] or [[]]


# -------------------------------------------------
@pytest.fixture
def fake_fetch(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Reemplaza ``fetch_data`` registrando cada request y devolviendo páginas.

    Returns:
        Callable que recibe ``total`` y ``page_size`` y expone
        ``requests`` (lista de params recibidos).
    """

    def _install(total: int, page_size: int) -> Any:
        pages = _make_pages(total, page_size)
        calls: List[dict] = []

        def _fake(endpoint: str, params: Any = None, token: Any = None) -> list:
            calls.append(dict(params or {}))
            offset = int((params or {}).get("offset", 0))
            limit = int((params or {}).get("limit", 0))
            # Reproduce el comportamiento del backend: offset/limit reales
            return (
                pages[offset // limit] if limit and offset // limit < len(pages) else []
            )

        monkeypatch.setattr(api_client, "fetch_data", _fake)

        class _Recorder:
            requests = calls

        return _Recorder()

    return _install


# ──────────────────────────────────────────────
# Comportamiento básico
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_una_sola_pagina_devuelve_todo(fake_fetch: Any) -> None:
    rec = fake_fetch(total=50, page_size=2000)

    df = fetch_dataframe_paged(ENDPOINT, params={"limit": 0, "ejercicio": 2026})

    assert len(df) == 50
    assert len(rec.requests) == 1


# -------------------------------------------------
def test_varias_paginas_se_concatenan(fake_fetch: Any) -> None:
    """REGRESIÓN: 47.000 registros deben venir en páginas, no de una."""
    rec = fake_fetch(total=5000, page_size=2000)

    df = fetch_dataframe_paged(ENDPOINT, params={"limit": 0, "ejercicio": 2026})

    assert len(df) == 5000
    assert len(rec.requests) == 3  # 2000 + 2000 + 1000
    assert [r["offset"] for r in rec.requests] == [0, 2000, 4000]


# -------------------------------------------------
def test_sin_registros_devuelve_dataframe_vacio(fake_fetch: Any) -> None:
    fake_fetch(total=0, page_size=2000)

    df = fetch_dataframe_paged(ENDPOINT, params={"limit": 0})

    assert isinstance(df, pd.DataFrame)
    assert df.empty


# ──────────────────────────────────────────────
# Contrato de parámetros
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_limit_y_offset_del_caller_se_ignoran(fake_fetch: Any) -> None:
    """El caller pasa ``limit=0``; quien controla la paginación es esta fn."""
    rec = fake_fetch(total=10, page_size=2000)

    fetch_dataframe_paged(
        ENDPOINT, params={"limit": 0, "offset": 999, "ejercicio": 2026}
    )

    assert len(rec.requests) == 1
    assert rec.requests[0]["limit"] == 2000
    assert rec.requests[0]["offset"] == 0


# -------------------------------------------------
def test_filtros_del_caller_se_conservan(fake_fetch: Any) -> None:
    rec = fake_fetch(total=5, page_size=2000)

    fetch_dataframe_paged(
        ENDPOINT, params={"limit": 0, "ejercicio": 2026, "ctaContable": "2111-1-1"}
    )

    assert rec.requests[0]["ejercicio"] == 2026
    assert rec.requests[0]["ctaContable"] == "2111-1-1"


# -------------------------------------------------
def test_params_none_no_falla(fake_fetch: Any) -> None:
    fake_fetch(total=3, page_size=2000)

    df = fetch_dataframe_paged(ENDPOINT)

    assert len(df) == 3


# ──────────────────────────────────────────────
# Seguridad
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_tope_de_seguridad_evita_bucle_infinito(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Si el backend ignorara ``offset`` siempre devolviendo página llena,
    el bucle debe cortarse en ``MAX_PAGED_ROWS``."""
    page = [{"id": i} for i in range(2000)]
    calls = {"n": 0}

    def _fake(endpoint: str, params: Any = None, token: Any = None) -> list:
        calls["n"] += 1
        return list(page)  # siempre llena, nunca termina

    monkeypatch.setattr(api_client, "fetch_data", _fake)

    df = fetch_dataframe_paged(ENDPOINT, params={"limit": 0}, page_size=2000)

    esperadas = MAX_PAGED_ROWS // 2000
    assert calls["n"] == esperadas
    assert len(df) == MAX_PAGED_ROWS


# -------------------------------------------------
def test_constante_de_seguridad() -> None:
    assert MAX_PAGED_ROWS == 200_000

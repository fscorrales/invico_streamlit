"""
Tests de regresión de ``filtrar_comprobantes_honorarios``.

Cubren el bug por el que ``factureros_funcionamiento`` y ``factureros_epam``
no generaban registros en SIIF: ``gto_rpa03g`` dejó de producir ``grupo="300"``
(commit ``c76b9f6``, v0.12.29) y pasó a producir ``grupo="3"``, mientras que
el filtro seguía exigiendo ``"300"``. El resultado era un DataFrame vacío
**sin excepción**, y por lo tanto ``siif_factureros_nro`` quedaba vacío:
``df["nro_original"].isin([])`` nunca era True.

Todos los tests son puros (``DataFrame`` -> ``DataFrame``): sin red, sin
``st.session_state`` ni Playwright.
"""

from typing import Any

import pandas as pd
import pytest

from src.automation.analysis.siif_unified import (
    CUIT_INVICO,
    GLOSAS_HONORARIOS,
    PARTIDA_EXCLUIDA_FACTUREROS,
    filtrar_comprobantes_honorarios,
)


# ──────────────────────────────────────────────
# Regresión: el bug original
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_grupo_servicios_un_digito_debe_incluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """REGRESIÓN: ``grupo="3"`` (formato actual) debe pasar el filtro.

    Este es exactamente el caso que fallaba: el filtro exigía ``"300"`` y
    ``gto_rpa03g`` produce ``"3"``.
    """
    df = as_dataframe(comprobante_factory(grupo="3"))

    result = filtrar_comprobantes_honorarios(df)

    assert len(result) == 1
    assert result["nro_comprobante"].tolist() == ["00123/26"]


# -------------------------------------------------
def test_grupo_legado_300_tambien_debe_incluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """Compatibilidad hacia atrás con registros previos al commit c76b9f6."""
    df = as_dataframe(comprobante_factory(grupo="300"))

    result = filtrar_comprobantes_honorarios(df)

    assert len(result) == 1


# -------------------------------------------------
@pytest.mark.parametrize("grupo_inesperado", ["1", "2", "4", "5"])
def test_grupo_distinto_de_servicios_debe_excluir(
    grupo_inesperado: str, comprobante_factory: Any, as_dataframe: Any
) -> None:
    """Solo el grupo 3 (servicios, donde viven los honorarios) debe pasar."""
    df = as_dataframe(comprobante_factory(grupo=grupo_inesperado))

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty


# ──────────────────────────────────────────────
# Resto de filtros (ya funcionaban, se protegen)
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_cuit_distinto_de_invico_debe_excluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    df = as_dataframe(comprobante_factory(cuit="30712345678"))

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty


# -------------------------------------------------
def test_partida_excluida_debe_excluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """La partida 384 queda fuera de la clasificación de factureros."""
    df = as_dataframe(comprobante_factory(grupo="3", partida="384"))

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty


# -------------------------------------------------
@pytest.mark.parametrize("cta_cte", ["130832-05", "130832-07"])
def test_ctas_ctes_de_factureros_deben_incluir(
    cta_cte: str, comprobante_factory: Any, as_dataframe: Any
) -> None:
    """Tanto funcionamiento (05) como EPAM (07) deben clasificarse."""
    df = as_dataframe(comprobante_factory(cta_cte=cta_cte))

    result = filtrar_comprobantes_honorarios(df)

    assert len(result) == 1
    assert result["cta_cte"].iloc[0] == cta_cte


# -------------------------------------------------
def test_cta_cte_de_haberes_debe_excluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """La 130832-04 (sueldos) no es cuenta de factureros."""
    df = as_dataframe(comprobante_factory(cta_cte="130832-04"))

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty


# ──────────────────────────────────────────────
# glosa: na=False (segundo fix)
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_glosa_none_no_debe_lanzar_excepcion(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """REGRESIÓN: ``glosa=None`` debe excluir la fila, no reventar.

    ``gto_rpa03g`` hace ``df.replace("", value=None)``, así que ``glosa``
    puede ser ``None``. Sin ``na=False``, ``str.contains`` devuelve ``NaN``
    y ``df.loc[mask]`` lanza ``ValueError: Cannot mask with non-boolean
    array containing NA / NaN values``.
    """
    df = as_dataframe(
        comprobante_factory(glosa=None),
        comprobante_factory(nro_comprobante="00999/26", glosa="PAGO HONORARIOS"),
    )

    result = filtrar_comprobantes_honorarios(df)  # no debe lanzar

    assert len(result) == 1
    assert result["nro_comprobante"].tolist() == ["00999/26"]


# -------------------------------------------------
@pytest.mark.parametrize(
    "glosa_valida",
    ["PAGO HONORARIOS", "RECON HONORARIOS", "LOCACION SERVICIOS"],
)
def test_glosas_de_honorarios_deben_incluir(
    glosa_valida: str, comprobante_factory: Any, as_dataframe: Any
) -> None:
    """Todas las glosas de ``GLOSAS_HONORARIOS`` deben clasificar."""
    assert len(GLOSAS_HONORARIOS) == 3  # HONOR, RECON, LOC

    df = as_dataframe(comprobante_factory(glosa=glosa_valida))

    result = filtrar_comprobantes_honorarios(df)

    assert len(result) == 1


# -------------------------------------------------
def test_glosa_sin_palabras_clave_debe_excluir(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    df = as_dataframe(comprobante_factory(glosa="PAGO PROVEEDOR GENERAL"))

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty


# ──────────────────────────────────────────────
# Casos borde
# ──────────────────────────────────────────────


# -------------------------------------------------
def test_dataframe_vacio_no_debe_lanzar(as_dataframe: Any) -> None:
    """Una entrada vacía (sin datos sincronizados) devuelve vacío."""
    df = as_dataframe()

    result = filtrar_comprobantes_honorarios(df)

    assert result.empty
    assert isinstance(result, pd.DataFrame)


# -------------------------------------------------
def test_condicion_unicamente_en_cta_cte_no_debe_pasar(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """Un registro que incumple *una* condición no debe pasar.

    Se rompe solo ``cta_cte``: el resto (cuit, grupo, partida, glosa) es
    válido, lo que demuestra que el filtro es una AND acumulativa.
    """
    df = as_dataframe(
        comprobante_factory(),
        comprobante_factory(nro_comprobante="00456/26", cta_cte="130832-09"),
    )

    result = filtrar_comprobantes_honorarios(df)

    assert len(result) == 1
    assert result["cta_cte"].tolist() == ["130832-05"]


# -------------------------------------------------
def test_no_debe_mutar_el_dataframe_entrada(
    comprobante_factory: Any, as_dataframe: Any
) -> None:
    """La función pura no debe modificar el ``DataFrame`` recibido."""
    df = as_dataframe(comprobante_factory(grupo="1"))
    filas_antes = len(df)

    filtrar_comprobantes_honorarios(df)

    assert len(df) == filas_antes


# -------------------------------------------------
def test_constantes_del_modulo() -> None:
    """Las constantes extraídas conservan sus valores históricos."""
    assert CUIT_INVICO == "30632351514"
    assert PARTIDA_EXCLUIDA_FACTUREROS == "384"
    assert GLOSAS_HONORARIOS == ["HONOR", "RECON", "LOC"]

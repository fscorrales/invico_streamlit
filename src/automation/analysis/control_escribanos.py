"""Automatización del control de Escribanos (SIIF vs SGF / SGF vs SSCC).

Descarga los auxiliares compartidos por AMBOS cruces:

- SIIF rcocc31 (cta. contable 2113-2-9) con Playwright en el hilo.
- SSCC Resumen General de Movimientos con el runner banco_invico en un
  proceso aparte (consola nueva en Windows).
- SGF Resumen de Rendiciones Proveedores con el runner
  resumen_rend_prov en un proceso aparte.

``ctas_ctes`` es dato manual y se carga desde Tablas Auxiliares → SSCC.
"""

import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import Rcocc31, login, logout
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_sgf_origenes, post_request

# Cta. contable SIIF de Escribanos (FEI / PFE)
CTA_CONTABLE_ESCRIBANOS = "2113-2-9"


# --------------------------------------------------
def sync_control_escribanos_from_sgf(
    sgf_username: str, sgf_password: str, token: str, ejercicios: List[int]
) -> None:

    modulo_runner = "src.automation.sgf.resumen_rend_prov_runner"
    ejercicios_str = ",".join(map(str, ejercicios))
    origenes_str = ",".join(get_sgf_origenes())

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        # En PRODUCCIÓN (.exe): Pasamos el flag genérico Y LUEGO el string del módulo
        args = [
            sys.executable,
            "--automation",
            modulo_runner,  # 🚀 Se convierte en sys.argv[1] antes de que el arranque lo limpie
            sgf_username,
            sgf_password,
            token,
            ejercicios_str,
            origenes_str,
        ]
    else:
        # En DESARROLLO (.py): Tu comando tradicional por consola con -m
        args = [
            sys.executable,
            "-m",
            modulo_runner,
            sgf_username,
            sgf_password,
            token,
            ejercicios_str,
            origenes_str,
        ]

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process_sgf = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SGF termine antes de devolver el control a Streamlit
    process_sgf.wait()
    print("✅ SGF Finalizado.")


# --------------------------------------------------
def sync_control_escribanos_from_sscc(
    sscc_username: str, sscc_password: str, token: str, ejercicios: List[int]
) -> None:

    modulo_runner = "src.automation.sscc.banco_invico_runner"
    ejercicios_str = ",".join(map(str, ejercicios))

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        # En PRODUCCIÓN (.exe): Pasamos el flag genérico Y LUEGO el string del módulo
        args = [
            sys.executable,
            "--automation",
            modulo_runner,  # 🚀 Se convierte en sys.argv[1] antes de que el arranque lo limpie
            sscc_username,
            sscc_password,
            token,
            ejercicios_str,
        ]
    else:
        # En DESARROLLO (.py): Tu comando tradicional por consola con -m
        args = [
            sys.executable,
            "-m",
            modulo_runner,
            sscc_username,
            sscc_password,
            token,
            ejercicios_str,
        ]

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process_sscc = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SSCC termine antes de devolver el control a Streamlit
    process_sscc.wait()
    print("✅ SSCC Finalizado.")


# --------------------------------------------------
async def sync_control_escribanos_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:
    """Descarga rcocc31 (2113-2-9) por ejercicio y lo persiste en el
    backend (POST /siif/rcocc31, idempotente por ejercicio+cta)."""

    async with async_playwright() as p:
        connect_siif = await login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )

        results = []
        # 🔹 Rcocc31
        rcocc31 = Rcocc31(siif=connect_siif)
        await rcocc31.go_to_reports()
        for ej in ejercicios:
            df_clean = await rcocc31.download_and_process_report(
                ejercicio=ej, cta_contable=CTA_CONTABLE_ESCRIBANOS
            )
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCOCC31.value, json_body=json_data
                )
                results.append(
                    f"Rcocc31 Ejercicio {ej} y cta. contable "
                    f"{CTA_CONTABLE_ESCRIBANOS}: {response}"
                )

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results


# --------------------------------------------------
def _compute_y_persistir(ruta_generate: str, ejercicios: List[int]) -> List[str]:
    """GET /generate* por ejercicio → POST del snapshot en su colección.

    Compartido por ambos cruces de escribanos (SIIF vs SGF y SGF vs
    SSCC): el backend arma el cruce on-demand con sus propias
    colecciones y luego se congela el snapshot con un POST (borrado
    idempotente por ejercicio).

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ruta_generate: Ruta del endpoint on-demand (p.ej.
            ``/control/controlEscribanos/generateSIIFVsSgf``).
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    endpoint_snapshot = Endpoints.CONTROL_ESCRIBANOS.value
    ruta_snapshot = _snapshot_de(ruta_generate)
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            endpoint_snapshot + ruta_generate,
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: el generate no devolvió registros; "
                "no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(
            endpoint_snapshot + ruta_snapshot, json_body=json_data
        )
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results


def _snapshot_de(ruta_generate: str) -> str:
    """Mapea la ruta /generate* a la ruta del snapshot correspondiente."""
    if "SIIF" in ruta_generate:
        return "/siifVsSgf"
    return "/sgfVsSscc"


# --------------------------------------------------
def compute_control_siif_vs_sgf(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce Escribanos SIIF vs SGF delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlEscribanos/generateSIIFVsSgf?ejercicio=X``
       : el backend arma el cruce (carga/pagos FEI vs pagos SGF).
    2. ``POST /control/controlEscribanos/siifVsSgf``: congela el
       snapshot en la colección ``control_escribanos_siif_vs_sgf``.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    return _compute_y_persistir("/generateSIIFVsSgf", ejercicios)


# --------------------------------------------------
def compute_control_sgf_vs_sscc(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce Escribanos SGF vs SSCC delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlEscribanos/generateSGFVsSscc?ejercicio=X``
       : el backend arma el cruce (neto SGF vs neto banco).
    2. ``POST /control/controlEscribanos/sgfVsSscc``: congela el
       snapshot en la colección ``control_escribanos_sgf_vs_sscc``.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    return _compute_y_persistir("/generateSGFVsSscc", ejercicios)
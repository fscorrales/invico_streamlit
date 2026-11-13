"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Control Anticipo de Viaticos (PA3)
Data required:
    - SIIF rfondos04 (PA3 y REV)
    - SIIF rpa03g
    - SIIF rcg01_uejp
    - SSCC Resumen General de Movimientos
        + 029 Anticipo de Viaticos Pagados (PAV de PA3)
        + 040 Reembolso por Gastos Mayores (Partida 373)
        + 005 Devolución de Fondos no Utilizados (REV)
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1alo5UBd7YRIBhSXqfo_c5Lz8JBfU3CXrVC0XOmtiH8c
"""

import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import GtoRpa03g, Rcg01Uejp, Rfondos04, login, logout
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, post_request


# --------------------------------------------------
def sync_control_viaticos_from_sscc(
    sscc_username: str, sscc_password: str, token: str, ejercicios: List[int]
) -> None:
    """Descarga el Banco INVICO (imputaciones 029/040/005) en un runner
    subprocess (consola independiente en Windows, como los demás controles)."""

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
async def sync_control_viaticos_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:
    """Descarga y pushea al backend los 3 reportes SIIF del control:

    - ``rcg01_uejp`` (por ejercicio)
    - ``rpa03g`` (ejercicio × grupos de partida 1-4)
    - ``rfondos04`` (ejercicio × tipos de comprobante PA3 y REV)
    """

    async with async_playwright() as p:
        connect_siif = await login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )
        results = []

        # 🔹 Rcg01Uejp
        rcg01_uejp = Rcg01Uejp(siif=connect_siif)
        await rcg01_uejp.go_to_reports()
        for ej in ejercicios:
            df_clean = await rcg01_uejp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCG01_UEJP.value, json_body=json_data
                )
                results.append(f"Ejercicio {ej}: {response}")
            else:
                print(f"⚠️ Rcg01Uejp Ejercicio {ej}: descarga fallida o sin datos")
                results.append(f"Ejercicio {ej}: ⚠️ Rcg01Uejp sin datos")

        # 🔹 GtoRpa03g
        gto_rpa03g = GtoRpa03g(siif=connect_siif)
        GRUPOS = ["1", "2", "3", "4"]
        for ej in ejercicios:
            for grupo in GRUPOS:
                df_clean = await gto_rpa03g.download_and_process_report(
                    ejercicio=ej, grupo_partida=grupo
                )
                if df_clean is not None and not df_clean.empty:
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_GTO_RPA03G.value, json_body=json_data
                    )
                    results.append(f"GtoRpa03g Ejercicio {ej}: {response}")
                else:
                    print(
                        f"⚠️ GtoRpa03g Ejercicio {ej} grupo {grupo}: "
                        "descarga fallida o sin datos"
                    )
                    results.append(
                        f"GtoRpa03g Ejercicio {ej} grupo {grupo}: ⚠️ sin datos"
                    )

        # 🔹 Rfondos04 (PA3 anticipo / REV reversión)
        rfondos04 = Rfondos04(siif=connect_siif)
        await rfondos04.go_to_reports()
        for ej in ejercicios:
            for tipo_comprobante in ["PA3", "REV"]:
                df_clean = await rfondos04.download_and_process_report(
                    ejercicio=ej, tipo_comprobante=tipo_comprobante
                )
                if df_clean is not None and not df_clean.empty:
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_RFONDOS04.value, json_body=json_data
                    )
                    results.append(
                        f"Rfondos04 {tipo_comprobante} Ejercicio {ej}: {response}"
                    )
                else:
                    print(
                        f"⚠️ Rfondos04 {tipo_comprobante} Ejercicio {ej}: "
                        "descarga fallida o sin datos"
                    )
                    results.append(
                        f"Rfondos04 {tipo_comprobante} Ejercicio {ej}: ⚠️ sin datos"
                    )

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results


# --------------------------------------------------
def compute_control_viaticos(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce Anticipo/Rendición de Viáticos delegado al
    backend (on-demand).

    Por cada ejercicio:

    1. ``GET /control/controlViaticos/generate?ejercicio=X``: el
       backend arma el cruce con sus propias colecciones (rfondos04,
       gastos 372/373 y Banco INVICO), sin descargar los crudos al
       cliente.
    2. ``POST /control/controlViaticos``: congela el snapshot del
       ejercicio en la colección ``control_viaticos_rendicion``
       (borrado idempotente por ejercicio), que es lo que luego leen el
       ``GET`` y la exportación a Google Sheet.

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    endpoint = Endpoints.CONTROL_VIATICOS.value
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            endpoint + "/generate",
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /generate no devolvió registros; "
                "no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(endpoint, json_body=json_data)
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results
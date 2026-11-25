"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Otros Gastos - SIIF vs SGF (lo que quedó por fuera de los
         demás controles)
Data required:
    - SIIF rcg01_uejp
    - SIIF gto_rpa03g (grupos 1-4)
    - SIIF rfondo07tp (PA6)
    - SGF Resumen de Rendiciones Proveedores
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1EBzBz17mtVzBmpAFznDyJf2RAJNspQyJQJaRD_WI5dE
"""

import json
import os
import subprocess
import sys
from typing import List

import pandas as pd
from playwright.async_api import async_playwright

from src.automation.siif import GtoRpa03g, Rcg01Uejp, Rfondo07tp, login, logout
from src.constants.endpoints import Endpoints
from src.services import fetch_data, fetch_dataframe, get_sgf_origenes, post_request

BASE = Endpoints.CONTROL_OTROS_GASTOS.value


# --------------------------------------------------
def dataframe_a_registros(df: pd.DataFrame) -> List[dict]:
    """Convierte un DataFrame en registros JSON-safe para el POST.

    ``df.to_dict(orient="records")`` materializa los campos opcionales
    que el backend omitió del JSON (``response_model_exclude_none``)
    como ``np.nan``; httpx serializa ese ``NaN`` con el token inválido
    ``NaN`` (``json.dumps`` con ``allow_nan=True`` por defecto) y el
    back lo rechaza en la validación de Pydantic (un campo ``str`` no
    admite ``nan``), descartando la fila EN SILENCIO del snapshot.

    Pasó en Control Otros Gastos: la tabla SIIF quedó sin el resto
    (todos con ``nro_fondo`` nulo) y la SGF sin los cuit nulos, lo que
    dejó el cruce 1:1 vacío.

    ``DataFrame.to_json`` sí emite ``null`` para los nulos y además
    normaliza los tipos numpy a tipos nativos de Python.

    Args:
        df: DataFrame con las filas a persistir.

    Returns:
        Lista de diccionarios sin ``NaN`` (``None`` en su lugar).
    """
    return json.loads(df.to_json(orient="records"))


# --------------------------------------------------
def sync_control_otros_gastos_from_sgf(
    sgf_username: str,
    sgf_password: str,
    token: str,
    ejercicios: List[int],
) -> None:
    """Descarga el Resumen de Rendiciones Proveedores en un runner
    subprocess (consola independiente en Windows, como los demás
    controles)."""

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
async def sync_control_otros_gastos_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:
    """Descarga y pushea al backend los 3 reportes SIIF del control:

    - ``rcg01_uejp`` (por ejercicio)
    - ``rfondo07tp`` (PA6: regularizaciones de fondos)
    - ``gto_rpa03g`` (ejercicio × grupos de partida 1-4)

    Si una descarga no produce datos se avisa (⚠️) en los resultados y
    en la consola: el loop no se traga el fallo en silencio.
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

        # 🔹 Rfondo07tp (PA6)
        rfondo07tp = Rfondo07tp(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rfondo07tp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RFONDO07TP.value, json_body=json_data
                )
                results.append(f"Ejercicio {ej}: {response}")
            else:
                print(f"⚠️ Rfondo07tp Ejercicio {ej}: descarga fallida o sin datos")
                results.append(f"Ejercicio {ej}: ⚠️ Rfondo07tp sin datos")

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
                    results.append(f"GtoRpa03g Ejercicio {ej} Gpo {grupo}: {response}")
                else:
                    print(
                        f"⚠️ GtoRpa03g Ejercicio {ej} grupo {grupo}: "
                        "descarga fallida o sin datos"
                    )
                    results.append(
                        f"Ejercicio {ej} Gpo {grupo}: ⚠️ GtoRpa03g sin datos"
                    )

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results

# --------------------------------------------------
def compute_control_otros_gastos_siif(ejercicios: List[int]) -> List[str]:
    """Calcula la tabla SIIF depurada y congela su snapshot.

    Por cada ejercicio:

    1. ``GET /control/otrosGastos/siif/generate?ejercicio=X``: el
       backend depura con sus propias colecciones (es_aprobado, MAP,
       PA6, obras Icaro, haberes, honorarios, viáticos y débitos;
       cajas chicas NO se depuran: SÍ están en SGF y se cruzan 1:1),
       sin descargar los crudos al cliente.
    2. ``POST /control/otrosGastos/siif``: congela el snapshot del
       ejercicio en la colección ``control_otros_gastos_siif`` (borrado
       idempotente por ejercicio).

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            f"{BASE}/siif/generate",
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /siif/generate sin registros; "
                "no se realizó el POST."
            )
            continue
        json_data = dataframe_a_registros(df)
        response = post_request(f"{BASE}/siif", json_body=json_data)
        results.append(f"Ejercicio {ejercicio}: {response}")
    return results


# --------------------------------------------------
def compute_control_otros_gastos_sgf(ejercicios: List[int]) -> List[str]:
    """Calcula la tabla SGF depurada y congela su snapshot.

    Mismo patrón que :func:`compute_control_otros_gastos_siif` sobre
    ``/sgf/generate`` + ``POST /sgf`` (colección
    ``control_otros_gastos_sgf``).
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            f"{BASE}/sgf/generate",
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /sgf/generate sin registros; "
                "no se realizó el POST."
            )
            continue
        json_data = dataframe_a_registros(df)
        response = post_request(f"{BASE}/sgf", json_body=json_data)
        results.append(f"Ejercicio {ejercicio}: {response}")
    return results


# --------------------------------------------------
def compute_control_otros_gastos_cruce(ejercicios: List[int]) -> List[str]:
    """Calcula el cruce en 2 capas y congela AMBAS tablas del snapshot.

    Por cada ejercicio:

    1. ``GET /control/otrosGastos/cruce/generate?ejercicio=X``: el
       backend devuelve ``{pareos, mensual}`` (pareo 1:1 del resto, con
       pre-paso de pagos agrupados por día para el cuit 30500049460, +
       control mensual de fondos permanentes).
    2. ``POST /control/otrosGastos/cruce``: congela las 2 tablas en un
       solo envío (colecciones ``control_otros_gastos_cruce`` y
       ``control_otros_gastos_cruce_mensual``, borrado idempotente por
       ejercicio).

    Nota: este compute alimenta a DOS pestañas (resto y fondos
    permanentes); la familia lo deduplica por identidad para no
    calcularlo ni persistirlo dos veces.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        bloque = fetch_data(
            f"{BASE}/cruce/generate",
            params={"ejercicio": int(ejercicio)},
        )
        pareos = bloque.get("pareos") if isinstance(bloque, dict) else None
        mensual = bloque.get("mensual") if isinstance(bloque, dict) else None
        if not pareos and not mensual:
            results.append(
                f"Ejercicio {ejercicio}: /cruce/generate sin registros; "
                "no se realizó el POST."
            )
            continue
        json_body = {
            "ejercicio": int(ejercicio),
            "pareos": pareos or [],
            "mensual": mensual or [],
        }
        response = post_request(f"{BASE}/cruce", json_body=json_body)
        results.append(f"Ejercicio {ejercicio}: {response}")
    return results



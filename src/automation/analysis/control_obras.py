"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: ICARO vs SGF Resumen de Rendiciones Proveedores
Data required:
    - Icaro
    - SIIF rdeu012
    - SGF Resumen de Rendiciones por Proveedor
    - SGF Listado Proveedores (POR LE MONENTO USO PROVEEDORES DE ICARO)
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/16v2ovmQnS1v73-WxTOK6b9Tx9DRugGc70ufpjVi-rPA
"""

import datetime as dt
import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif.rdeu012 import Rdeu012
from src.constants.endpoints import Endpoints
from src.services import get_sgf_origenes, post_request


# --------------------------------------------------
def sync_control_obras_from_sgf(
    sgf_username: str,
    sgf_password: str,
    token: str,
    ejercicios: List[int],
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

    process_sscc = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SSCC termine antes de devolver el control a Streamlit
    process_sscc.wait()
    print("✅ SGF Finalizado.")


# --------------------------------------------------
async def sync_control_obras_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:

    async with async_playwright() as p:
        # 🔹Rdeu012
        # Obtenemos los meses a descargar
        ## 1. Obtenemos el año y mes actual dinámicamente
        ahora = dt.datetime.now()
        anio_actual = ahora.year
        mes_actual = ahora.month

        meses = []

        # 2. Iteramos por cada año y por cada mes
        for anio in sorted(ejercicios):
            for mes in range(1, 13):
                # Filtro 1: Limitación inferior (desde enero de 2010)
                if anio < 2010:
                    continue

                # Filtro 2: Limitación superior (no pasarse del mes/año actual)
                if anio == anio_actual and mes > mes_actual:
                    break  # Cortamos los meses siguientes de este año
                elif anio > anio_actual:
                    break  # Cortamos por completo si el año es futuro

                # 3. Formateamos a 'mmyyyy' (el :02d asegura el cero a la izquierda)
                periodo_str = f"{mes:02d}{anio}"
                meses.append(periodo_str)

        siif = Rdeu012()
        await siif.login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )
        await siif.go_to_reports()

        results = []
        for mes in meses:
            df_clean = await siif.download_and_process_report(mes=mes)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RDEU012.value, json_body=json_data
                )
                results.append(f"Mes {mes}: {response}")

        await siif.logout()

        print("✅ SIIF Finalizado")
        return results


# --------------------------------------------------
def compute_control_obras(ejercicios: List[int]) -> None:
    try:
        response = post_request(
            Endpoints.CONTROL_OBRAS.value + "/compute",
            json_body=ejercicios,
        )
        # group_by = ["ejercicio", "mes", "cta_cte", "cuit"]
        # params = {
        #     "limit": 0,
        #     "ejercicio": ejercicio,
        # }
        # icaro = fetch_dataframe(
        #     Endpoints.ICARO_CARGA.value + "/netoRDEU", params=params
        # )
        # icaro = icaro.loc[:, group_by + ["importe"]]
        # icaro = icaro.groupby(group_by)["importe"].sum()
        # icaro = icaro.reset_index()
        # icaro = icaro.rename(columns={"importe": "ejecutado_icaro"})
        # # print(f"icaro.shape: {icaro.shape} - icaro.head: {icaro.head()}")
        # sgf = fetch_dataframe(
        #     Endpoints.SGF_RESUMEN_REND_PROV.value + "/uniqueObras", params=params
        # )
        # sgf = sgf.loc[:, group_by + ["importe_bruto"]]
        # sgf = sgf.groupby(group_by)["importe_bruto"].sum()
        # sgf = sgf.reset_index()
        # sgf = sgf.rename(columns={"importe_bruto": "bruto_sgf"})
        # # print(f"sgf.shape: {sgf.shape} - sgf.head: {sgf.head()}")
        # df = pd.merge(icaro, sgf, how="outer")
        # df[["ejecutado_icaro", "bruto_sgf"]] = df[
        #     ["ejecutado_icaro", "bruto_sgf"]
        # ].fillna(0)
        # df["diferencia"] = df.ejecutado_icaro - df.bruto_sgf
        # df = pd.DataFrame(df)
        # df.reset_index(drop=True, inplace=True)
        # json_data = df.to_dict(orient="records")
        # response = post_request(Endpoints.CONTROL_OBRAS.value, json_body=json_data)
        # results.append(f"Ejercicio {ej}: {response}")

    except Exception as e:
        print(f"Error in compute_control_obras: {e}")

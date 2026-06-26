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

import pandas as pd
from playwright.async_api import async_playwright

from src.automation.siif.rdeu012 import Rdeu012
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, post_request


# --------------------------------------------------
def sync_control_obras_from_sgf(
    sscc_username: str,
    sscc_password: str,
    token: str,
    ejercicios: List[int],
    origenes: List[str],
) -> None:

    modulo_runner = "src.automation.sgf.resumen_rend_prov_runner"
    ejercicios_str = ",".join(map(str, ejercicios))
    origenes_str = ",".join(map(str, origenes))

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process_sscc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            modulo_runner,
            sscc_username,
            sscc_password,
            token,
            ejercicios_str,
            origenes_str,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SSCC termine antes de devolver el control a Streamlit
    process_sscc.wait()
    print("✅ SSCC Finalizado.")


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
    for ejercicio in ejercicios:
        try:
            group_by = ["ejercicio", "mes", "cta_cte", "grupo"]
            # icaro = generate_icaro_carga_neto_rdeu(ejercicio=int(ejercicio))
            # icaro = icaro.loc[:, group_by + ["importe"]]
            # icaro = icaro.groupby(group_by)["importe"].sum()
            # icaro = icaro.reset_index()
            # icaro = icaro.rename(columns={"importe": "ejecutado_icaro"})
            # print(f"icaro.shape: {icaro.shape} - icaro.head: {icaro.head()}")
            sgf = generate_resumen_rend_cuit(ejercicio=ejercicio)
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
            # # results.append(f"Ejercicio {ej}: {response}")

        except Exception as e:
            print(f"Error in compute_control_obras: {e}")


# --------------------------------------------------
def generate_resumen_rend_cuit(
    ejercicio: int = dt.datetime.now().year,
) -> pd.DataFrame:
    params = {
        "limit": 0,
        "ejercicio": ejercicio,
    }
    df = fetch_dataframe(Endpoints.SGF_RESUMEN_REND_PROV.value, params=params)
    df = df.loc[df["origen"] != "FUNCIONAMIENTO"]

    # Filtramos los registros de honorarios en EPAM
    df_epam = df.copy()
    keep = ["HONORARIOS"]
    df_epam = df_epam.loc[df_epam["origen"] == "EPAM"]
    df_epam = df_epam.loc[~df_epam.destino.str.contains("|".join(keep))]
    df = df.loc[df["origen"] != "EPAM"]
    df = pd.DataFrame(pd.concat([df, df_epam], ignore_index=True))

    # Filtramos los registros duplicados en la 106
    df_106 = df.copy()
    df_106 = df_106.loc[df_106["cta_cte"] == "106"]
    df_106 = df_106.drop_duplicates(
        subset=["mes", "fecha", "beneficiario", "libramiento", "importe_bruto"]
    )
    df = pd.concat([df[df["cta_cte"] != "106"], df_106], ignore_index=True)

    # Filtramos los registros duplicados en la 07
    df_07 = df.copy()
    df_07 = df_07.loc[df_07["cta_cte"] == "130832-07"]
    df_07 = df_07.sort_values(["libramiento", "destino"], ascending=False)
    df_07 = df_07.drop_duplicates(
        subset=[
            "mes",
            "fecha",
            "beneficiario",
            "libramiento",
            "importe_bruto",
            "gcias",
            "sellos",
            "iibb",
            "suss",
            "invico",
            "seguro",
            "salud",
            "mutual",
            "otras",
            "retenciones",
            "importe_neto",
        ]
    )
    df = pd.concat([df[df["cta_cte"] != "130832-07"], df_07], ignore_index=True)

    # Filtramos los registros duplicados en la 03
    df_03 = df.copy()
    df_03 = df_03.loc[df_03["cta_cte"] == "130832-03"]
    df_03 = df_03.sort_values(["libramiento", "destino"], ascending=False)
    df_03 = df_03.drop_duplicates(
        subset=[
            "mes",
            "fecha",
            "beneficiario",
            "libramiento",
            "importe_bruto",
            "gcias",
            "sellos",
            "iibb",
            "suss",
            "invico",
            "seguro",
            "salud",
            "mutual",
            "otras",
            "retenciones",
            "importe_neto",
        ]
    )
    df = pd.concat([df[df["cta_cte"] != "130832-03"], df_03], ignore_index=True)

    # Filtramos los registros duplicados en la 03
    df_13 = df.copy()
    df_13 = df_13.loc[df_13["cta_cte"] == "130832-13"]
    df_13 = df_13.sort_values(["libramiento", "destino"], ascending=False)
    df_13 = df_13.drop_duplicates(
        subset=[
            "mes",
            "fecha",
            "beneficiario",
            "libramiento",
            "importe_bruto",
            "gcias",
            "sellos",
            "iibb",
            "suss",
            "invico",
            "seguro",
            "salud",
            "mutual",
            "otras",
            "retenciones",
            "importe_neto",
        ]
    )
    df = pd.concat([df[df["cta_cte"] != "130832-13"], df_13], ignore_index=True)

    # Filtramos los registros duplicados en la 221078150
    df_2210178150 = df.copy()
    df_2210178150 = df_2210178150.loc[df_2210178150["cta_cte"] == "2210178150"]
    df_2210178150 = df_2210178150.drop_duplicates(
        subset=["mes", "fecha", "beneficiario", "libramiento", "importe_bruto"]
    )
    # df = df[df["cta_cte"] != "2210178150"]
    df = pd.concat(
        [df[df["cta_cte"] != "2210178150"], df_2210178150], ignore_index=True
    )

    print(df.info())
    print(df.head())

    return df


# --------------------------------------------------
def generate_icaro_carga_neto_rdeu(
    ejercicio: int = dt.datetime.now().year,
) -> pd.DataFrame:
    pass
    # df = get_banco_invico_unified_cta_cte(ejercicio=ejercicio)
    # dep_transf_int = ["034", "004"]
    # dep_pf = ["214", "215"]
    # dep_otros = ["003", "055", "005", "013"]
    # dep_cert_neg = ["18"]
    # df = df.loc[df["movimiento"] == "DEPOSITO"]
    # df = df.loc[
    #     ~df["cod_imputacion"].isin(dep_transf_int + dep_pf + dep_otros + dep_cert_neg)
    # ]
    # if not df.empty:
    #     df["grupo"] = np.where(
    #         df["cta_cte"] == "10270",
    #         "FONAVI",
    #         np.where(
    #             df["cta_cte"].isin(["130832-12", "334", "Macro", "Patagonia"]),
    #             "RECUPEROS",
    #             "OTROS",
    #         ),
    #     )
    #     df.reset_index(drop=True, inplace=True)
    # return df

    # try:
    #     icaro_docs = await get_icaro_carga_unified_cta_cte()
    #     rdeu_docs = await get_siif_rdeu012_unified_cta_cte()

    #     icaro = pd.DataFrame(icaro_docs)
    #     icaro = icaro.loc[icaro["ejercicio"] == ejercicio]
    #     icaro = icaro.loc[~icaro["tipo"].isin(["PA6", "REG"])]
    #     rdeu = pd.DataFrame(rdeu_docs).loc[:, ["nro_comprobante", "saldo", "mes"]]
    #     rdeu = rdeu.drop_duplicates(subset=["nro_comprobante", "mes"])
    #     rdeu = pd.merge(rdeu, icaro, how="inner", copy=False)
    #     rdeu["importe"] = rdeu.saldo * (-1)
    #     rdeu["tipo"] = "RDEU"
    #     rdeu = rdeu.drop(columns=["saldo"])
    #     rdeu = pd.concat([rdeu, icaro], copy=False)
    #     icaro = pd.DataFrame(icaro_docs)
    #     icaro = icaro.loc[icaro["ejercicio"] == ejercicio]
    #     icaro = icaro.loc[icaro["tipo"].isin(["PA6"])]
    #     rdeu = pd.concat([rdeu, icaro], copy=False)
    #     icaro_carga_neto_rdeu = rdeu

    #     # Ajustamos la Deuda Flotante Pagada
    #     rdeu = pd.DataFrame(rdeu_docs)
    #     rdeu = rdeu.drop_duplicates(subset=["nro_comprobante"], keep="last")
    #     rdeu["fecha_hasta"] = rdeu["fecha_hasta"] + pd.tseries.offsets.DateOffset(
    #         months=1
    #     )
    #     rdeu["mes_hasta"] = rdeu["fecha_hasta"].dt.strftime("%m/%Y")
    #     rdeu["ejercicio"] = pd.to_numeric(rdeu["mes_hasta"].str[-4:])

    #     # Incorporamos los comprobantes de gastos pagados
    #     # en periodos posteriores (Deuda Flotante)
    #     if ejercicio is not None:
    #         if isinstance(ejercicio, list):
    #             rdeu = rdeu.loc[rdeu["ejercicio"].isin(ejercicio)]
    #         else:
    #             rdeu = rdeu.loc[rdeu["ejercicio"].isin([ejercicio])]
    #     icaro = pd.DataFrame(icaro_docs)
    #     icaro = icaro.loc[~icaro["tipo"].isin(["PA6", "REG"])]
    #     icaro = icaro.loc[
    #         :,
    #         [
    #             "nro_comprobante",
    #             "actividad",
    #             "partida",
    #             "fondo_reparo",
    #             "nro_certificado",
    #             "avance",
    #             "origen",
    #             "desc_obra",
    #         ],
    #     ]
    #     rdeu = pd.merge(rdeu, icaro, on="nro_comprobante", copy=False)
    #     rdeu["importe"] = rdeu.saldo
    #     rdeu["tipo"] = "RDEU"
    #     rdeu["id_carga"] = rdeu["nro_comprobante"] + "C"
    #     rdeu = rdeu.loc[~rdeu["actividad"].isna()]
    #     rdeu = rdeu.drop(columns=["fecha", "mes"])
    #     rdeu = rdeu.rename(columns={"fecha_hasta": "fecha", "mes_hasta": "mes"})
    #     rdeu = rdeu.loc[
    #         :,
    #         [
    #             "ejercicio",
    #             "nro_comprobante",
    #             "fuente",
    #             "cuit",
    #             "cta_cte",
    #             "tipo",
    #             "importe",
    #             "id_carga",
    #             "actividad",
    #             "partida",
    #             "fondo_reparo",
    #             "nro_certificado",
    #             "avance",
    #             "origen",
    #             "desc_obra",
    #             "fecha",
    #             "mes",
    #         ],
    #     ]
    #     df = pd.concat([rdeu, icaro_carga_neto_rdeu], copy=False)
    #     if ejercicio is not None:
    #         if isinstance(ejercicio, list):
    #             df = df.loc[df["ejercicio"].isin(ejercicio)]
    #         else:
    #             df = df.loc[df["ejercicio"].isin([ejercicio])]
    #     return df
    # except Exception as e:
    #     logger.error(
    #         f"Error retrieving Icaro's Carga Neto Deuda Flotante Data from database: {e}"
    #     )
    #     raise HTTPException(
    #         status_code=500,
    #         detail="Error retrieving Icaro's Carga Neto Deuda Flotante Data from the database",
    #     )

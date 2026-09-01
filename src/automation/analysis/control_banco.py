"""
Author : Fernando Corrales <fscpython@gmail.com>
Purpose: Control Banco SIIF vs SSCC (Banco Real)
Date   : 16-jun-2026
Data required:
    - SIIF rcg01_uejp
    - SIIF rpa03g
    - SIIF rvicon03
    - SIIF rcocc31
    - SSCC Resumen General de Movimientos
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1CRQjzIVzHKqsZE8_E1t8aRQDfWfZALhbe64WcxHiSM4
"""

import os
import subprocess
import sys
from enum import Enum
from typing import List

import numpy as np
import pandas as pd
from playwright.async_api import async_playwright

from src.automation.analysis.siif_unified import get_siif_comprobantes_honorarios
from src.automation.analysis.sscc_unified import get_banco_invico_unified_cta_cte
from src.automation.siif import (
    GtoRpa03g,
    Rcg01Uejp,
    Rcocc31,
    Rvicon03,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, post_request
from src.utils import sanitize_dataframe_for_json


# -------------------------------------------------
class Categoria(str, Enum):
    sin_categoria = "NO Categorizado"
    fonavi = "1.1 Ingreso FO.NA.VI."
    recuperos = "1.2 Cobranza de Cuotas de Viviendas"
    fondos_provinciales = "1.3 Ingreso Fondos Provinciales"
    aporte_empresario = "1.4 Ingreso 3% Aporte Empresario"
    haberes = "2.1 Pago al Personal"
    contratistas = "2.2.1 Pago a Contratistas"
    proveedores = "2.2.2 Pago a Proveedores"
    retenciones = "2.2.3 Pago de Retenciones Contratistas y Proveedores"
    factureros_funcionamiento = "2.3.1 Pago Honorarios y Comisiones (Funcionamiento)"
    factureros_mutual_funcionamiento = (
        "2.3.2 Pago Mutual de Honorarios y Comisiones (Funcionamiento)"
    )
    factureros_embargo_funcionamiento = (
        "2.3.3 Pago Embargo sobre Honorarios (Funcionamiento)"
    )
    factureros_epam = "2.4.1 Pago Honorarios y Comisiones (EPAM)"
    factureros_seguro_funcionamiento = (
        "2.4.2 Pago Seguro de Honorarios (Funcionamiento y EPAM)"
    )
    escribanos = "2.5 Pagos Escribanos (FEI / PFE)"
    viaticos = "2.6.1 Pago Anticipo de Viáticos (PA3 / PAV)"
    viaticos_reembolso = "2.6.2 Reembolso de Viático en exceso (373)"
    viaticos_reversion = "2.6.3 Reversion de Viático (Rev)"


# --------------------------------------------------
async def sync_control_banco_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:

    async with async_playwright() as p:
        connect_siif = await login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )

        results = []
        # 🔹 Rvicon03
        rvicon03 = Rvicon03(siif=connect_siif)
        await rvicon03.go_to_reports()
        for ej in ejercicios:
            df_clean = await rvicon03.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RVICON03.value, json_body=json_data
                )
                results.append(f"RVICON03 Ejercicio {ej}: {response}")

        # 🔹 Rcocc31
        rcocc31 = Rcocc31(siif=connect_siif)
        for ej in ejercicios:
            cuentas_contables = fetch_dataframe(
                Endpoints.SIIF_RVICON03.value, params={"limit": 0, "ejercicio": ej}
            )
            cuentas_contables = cuentas_contables["cta_contable"].unique()
            print(
                f"Para el ejercicio {ej} se bajaran las siguientes cuentas contables: {cuentas_contables}"
            )
            for cta_contable in cuentas_contables:
                df_clean = await rcocc31.download_and_process_report(
                    ejercicio=ej, cta_contable=cta_contable
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_RCOCC31.value, json_body=json_data
                    )
                    results.append(f"RCOCC31 Ejercicio {ej}: {response}")

        # 🔹 Rcg01Uejp
        rcg01uejp = Rcg01Uejp(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rcg01uejp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCG01_UEJP.value, json_body=json_data
                )
                results.append(f"Rcg01Uejp Ejercicio {ej}: {response}")

        # 🔹 GtoRpa03g
        gto_rpa03g = GtoRpa03g(siif=connect_siif)
        # GRUPOS = get_grupos_partidas_siif_list(
        #     update_trigger=st.session_state.grupos_partidas_siif_uploader_iteration
        # )
        GRUPOS = ["1", "2", "3", "4"]
        for ej in ejercicios:
            for grupo in GRUPOS:
                df_clean = await gto_rpa03g.download_and_process_report(
                    ejercicio=ej, grupo_partida=grupo
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_GTO_RPA03G.value, json_body=json_data
                    )
                    results.append(f"GtoRpa03g Ejercicio {ej}: {response}")

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results


# --------------------------------------------------
def sync_control_banco_from_sscc(
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
def generate_banco_siif(
    ejercicio: int,
    netear_pa6: bool = True,
    netear_aporte_empreario: bool = True,
    netear_dev_haberes_erroneos: bool = True,
) -> pd.DataFrame:
    params = {"limit": 0, "ejercicio": ejercicio}
    df = fetch_dataframe(Endpoints.SIIF_RCOCC31.value, params=params)
    # if df.empty:
    #     raise HTTPException(status_code=404, detail="No se encontraron registros")

    # Solo incluimos los registros que tienen movimientos en la cuenta 1112-2-6
    df = df.loc[
        df["nro_entrada"].isin(
            df.loc[df["cta_contable"] == "1112-2-6"]["nro_entrada"].unique()
        )
    ]

    # Quitamos el cierre y la apertura
    df = df.loc[~df["tipo_comprobante"].isin(["APE", "CIE"])]

    columns_to_flip_sign = ["debitos", "creditos", "saldo"]

    # Neteamos los PA6 pagados y ya regularizados
    if netear_pa6:
        params = {"limit": 0, "ejercicio": ejercicio}
        gastos_df = fetch_dataframe(Endpoints.SIIF_RCG01_UEJP.value, params=params)
        pa6_pagados = gastos_df["nro_fondo"].unique().tolist()
        pa6_pagados_df = df.loc[
            (df["tipo_comprobante"] == "PAP") & (df["nro_original"].isin(pa6_pagados))
        ].copy()
        pa6_pagados_df["tipo_comprobante"] = "FSC"
        pa6_pagados_df[columns_to_flip_sign] = pa6_pagados_df[columns_to_flip_sign] * (
            -1
        )
        df = pd.concat([df, pa6_pagados_df])

    # Neteamos el Aporte Empresario tanto en ingresos como en gastos
    if netear_aporte_empreario:
        aporte_empresario_df = df.loc[df["cta_contable"] == "5123-1-1"].copy()
        aporte_empresario_df["tipo_comprobante"] = "FSC"
        aporte_empresario_df[columns_to_flip_sign] = aporte_empresario_df[
            columns_to_flip_sign
        ] * (-1)
        df = pd.concat([df, aporte_empresario_df])
        aporte_empresario_df = df.loc[
            (df["cta_contable"] == "2122-1-2") & (df["auxiliar_1"] == "337")
        ].copy()
        aporte_empresario_df["tipo_comprobante"] = "FSC"
        aporte_empresario_df[columns_to_flip_sign] = aporte_empresario_df[
            columns_to_flip_sign
        ] * (-1)
        df = pd.concat([df, aporte_empresario_df])

    # Neteamos el código 310 de devolución de haberes erroneos tanto en ingresos como en gastos
    if netear_dev_haberes_erroneos:
        hab_erroneos_df = df.loc[
            (df["cta_contable"] == "2122-1-2") & (df["auxiliar_1"] == "310")
        ].copy()
        if not hab_erroneos_df.empty:
            hab_erroneos_df["tipo_comprobante"] = "FSC"
            hab_erroneos_df["cta_contable"] = "6121-1-1"
            df = pd.concat([df, hab_erroneos_df])
            hab_erroneos_df["cta_contable"] = "2122-1-2"
            hab_erroneos_df[columns_to_flip_sign] = hab_erroneos_df[
                columns_to_flip_sign
            ] * (-1)
            df = pd.concat([df, hab_erroneos_df])

    # Agregamos la columna cta_cte desde auxiliar_1 de la cuenta 1112-2-6
    ctas_ctes_df = df.loc[
        df["cta_contable"] == "1112-2-6", ["nro_entrada", "auxiliar_1"]
    ].copy()
    ctas_ctes_df = ctas_ctes_df.drop_duplicates()
    ctas_ctes_df = ctas_ctes_df.rename(columns={"auxiliar_1": "cta_cte"})
    df = df.merge(ctas_ctes_df, on="nro_entrada", how="left")
    df = df.loc[df["cta_contable"] != "1112-2-6"]

    # Mapeamos las cuentas corrientes
    ctas_ctes = fetch_dataframe(Endpoints.CTAS_CTES.value, params={"limit": 0})
    map_to = ctas_ctes.loc[:, ["map_to", "siif_contabilidad_cta_cte"]]
    df = pd.merge(
        df,
        map_to,
        how="left",
        left_on="cta_cte",
        right_on="siif_contabilidad_cta_cte",
    )
    df["cta_cte"] = df["map_to"]
    df.drop(["map_to", "siif_contabilidad_cta_cte"], axis="columns", inplace=True)

    # Agregamos descripción a las cuentas contables
    params = {"limit": 0, "ejercicio": ejercicio}
    ctas_contables_df = fetch_dataframe(Endpoints.SIIF_RVICON03.value, params=params)
    ctas_contables_df = ctas_contables_df.loc[:, ["cta_contable", "desc_cta_contable"]]
    df = pd.merge(df, ctas_contables_df, how="left", on="cta_contable")

    # Agregamos columna para clasificar registros
    df["clase"] = Categoria.sin_categoria.value
    conditions = {
        "5172-4-4": Categoria.fonavi.value,
        "5172-2-1": Categoria.fondos_provinciales.value,
        "1122-1-1": Categoria.recuperos.value,
        "2111-1-1": Categoria.proveedores.value,
        "2111-1-3": Categoria.proveedores.value,
        "2131-1-3": Categoria.proveedores.value,
        "2111-1-4": Categoria.proveedores.value,
        "2131-2-2": Categoria.proveedores.value,
        "2111-1-2": Categoria.contratistas.value,
        "2113-2-9": Categoria.escribanos.value,
        "2122-1-2": Categoria.retenciones.value,
        "2113-1-13": Categoria.viaticos.value,
        "4112-1-3": Categoria.viaticos_reembolso.value,
        "1141-1-4": Categoria.viaticos_reversion.value,
    }
    df["clase"] = df["cta_contable"].map(conditions).fillna(df["clase"])

    ## Pago al personal (Haberes)
    df["clase"] = np.where(
        (df["cta_contable"] == "2121-1-1")  # Pago personal haberes
        | (
            (df["cta_contable"] == "2122-1-2")  # Pago retenciones haberes
            & (
                ~df["auxiliar_1"].str.startswith("1") & (df["auxiliar_1"] != "337")
            )  # 3% INVICO
        )
        | (
            (df["cta_contable"] == "2111-1-3")  # Pago Movilidad y Comisión FONAVI
            & (df["cta_cte"] == "130832-04")
        ),
        Categoria.haberes.value,
        df["clase"],
    )

    ## Pago Embargos sobre Honorarios Funcionamiento
    df["clase"] = np.where(
        (df["cta_contable"] == "2122-1-2")
        & (df["auxiliar_1"] == "255")
        & (df["cta_cte"] == "130832-05"),
        Categoria.factureros_embargo_funcionamiento.value,
        df["clase"],
    )

    ## Para clasificar los pagos de Mutual de factureros funcionamiento
    df["clase"] = np.where(
        (df["cta_contable"] == "2122-1-2")
        & (df["auxiliar_1"] == "341")
        & (df["cta_cte"] == "130832-05"),
        Categoria.factureros_mutual_funcionamiento.value,
        df["clase"],
    )

    ## Para clasificar los pagos de Seguro de factureros funcionamiento y EPAM
    df["clase"] = np.where(
        (df["cta_contable"] == "2122-1-2")
        & (df["auxiliar_1"] == "413")
        & (df["cta_cte"] != "130832-04"),
        Categoria.factureros_seguro_funcionamiento.value,
        df["clase"],
    )

    ## Para clasificar los factureros
    siif_factureros = get_siif_comprobantes_honorarios(ejercicio=ejercicio)
    siif_factureros["nro_comprobante"] = (
        siif_factureros["nro_comprobante"].str.lstrip("0").str[:-3]
    )
    siif_factureros_nro = (
        siif_factureros.loc[
            siif_factureros["cta_cte"] == "130832-05", "nro_comprobante"
        ]
        .unique()
        .tolist()
    )
    df["clase"] = np.where(
        (df["cta_contable"].isin(["2111-1-3", "2111-1-1"]))
        & (df["cta_cte"] == "130832-05")
        & (df["nro_original"].isin(siif_factureros_nro)),
        Categoria.factureros_funcionamiento.value,
        df["clase"],
    )
    siif_factureros_nro = (
        siif_factureros.loc[
            siif_factureros["cta_cte"] == "130832-07", "nro_comprobante"
        ]
        .unique()
        .tolist()
    )
    df["clase"] = np.where(
        (df["cta_contable"].isin(["2111-1-3", "2111-1-1"]))
        & (df["cta_cte"] == "130832-07")
        & (df["nro_original"].isin(siif_factureros_nro)),
        Categoria.factureros_epam.value,
        df["clase"],
    )

    # Ordenamos y seleccionamos columnas finales
    df["nro_entrada"] = pd.to_numeric(df["nro_entrada"], errors="coerce")
    df = df.sort_values(
        ["nro_entrada", "debitos", "creditos", "cta_contable"],
        ascending=[True, False, False, True],
    )
    df["nro_entrada"] = df["nro_entrada"].astype(str)
    df = df.loc[
        :,
        [
            "ejercicio",
            "mes",
            "fecha",
            "fecha_aprobado",
            "nro_entrada",
            "nro_original",
            "cta_contable",
            "tipo_comprobante",
            "debitos",
            "creditos",
            "saldo",
            "auxiliar_1",
            "auxiliar_2",
            "cta_cte",
            "desc_cta_contable",
            "clase",
        ],
    ]

    json_data = sanitize_dataframe_for_json(df).to_dict(orient="records")
    response = post_request(Endpoints.CONTROL_BANCO_SIIF.value, json_body=json_data)

    return df


# --------------------------------------------------
def generate_banco_sscc(
    ejercicio: int = None,
    netear_transf_internas: bool = True,
    netear_reingresos: bool = True,
) -> pd.DataFrame:
    df = get_banco_invico_unified_cta_cte(ejercicio=ejercicio)

    # Neteamos las transferencias internas
    if netear_transf_internas:
        df["cod_imputacion"] = np.where(
            df["cod_imputacion"].isin(["004", "034"]),
            "000",
            df["cod_imputacion"],
        )
        df["imputacion"] = np.where(
            df["cod_imputacion"] == "000",
            "TRANSFERENCIAS INTERNAS (NETAS)",
            df["imputacion"],
        )

    # Neteamos los reingresos de cheques
    if netear_reingresos:
        cheques_df = df.loc[df["cod_imputacion"] == "003", :].copy()
        if not cheques_df.empty:
            imputacion_003 = cheques_df["imputacion"].iloc[0]
            # cheques_df["movimiento"] = cheques_df["concepto"].str.split('\s').str[-1]
            cheques_df["movimiento"] = cheques_df["concepto"].str.extract(r"(\d+)$")[0]
            cheques_df = cheques_df.drop(["cod_imputacion", "imputacion"], axis=1)
            cheques_df = cheques_df.merge(
                df.loc[:, ["movimiento", "cod_imputacion", "imputacion"]],
                how="left",
                on="movimiento",
            )
            cheques_df = cheques_df.dropna(subset=["cod_imputacion", "imputacion"])
            df = pd.concat([df, cheques_df])
            cheques_df["importe"] = cheques_df["importe"] * (-1)
            cheques_df["cod_imputacion"] = "003"
            cheques_df["imputacion"] = imputacion_003
            df = pd.concat([df, cheques_df])

    # Agregamos columna para clasificar registros
    df["clase"] = Categoria.sin_categoria.value
    conditions = {
        "001": Categoria.fonavi.value,
        "012": Categoria.fondos_provinciales.value,
        "002": Categoria.recuperos.value,
        "043": Categoria.factureros_funcionamiento.value,
        "021": Categoria.factureros_epam.value,
        "024": Categoria.haberes.value,
        "059": Categoria.haberes.value,  # Pago Mutual de la Movilidad
        "049": Categoria.factureros_embargo_funcionamiento.value,
        "036": Categoria.escribanos.value,
        "035": Categoria.retenciones.value,
        "029": Categoria.viaticos.value,
        "040": Categoria.viaticos_reembolso.value,
        "005": Categoria.viaticos_reversion.value,
    }
    df["clase"] = df["cod_imputacion"].map(conditions).fillna(df["clase"])

    ## Pago contratistas
    df["clase"] = np.where(
        (
            df["cod_imputacion"].isin(
                ["065", "020", "041", "053", "217", "019", "066", "027", "162"]
            )
        )
        | (
            (df["cod_imputacion"] == "021")  # Pago Serv. y Mat. EPAM
            & (~df["concepto"].str.startswith("0175"))
        ),
        Categoria.contratistas.value,
        df["clase"],
    )

    ## Pago a Proveedores
    df["clase"] = np.where(
        (df["cod_imputacion"].isin(["023", "052", "031", "033", "037"]))
        | (
            (df["cod_imputacion"] == "032")  # Pago Renovación de Seguro
            & (~df["concepto"].str.startswith("SEGURO"))
        ),
        Categoria.proveedores.value,
        df["clase"],
    )

    ## Pago Mutual Factureros (Funcionamiento)
    df["clase"] = np.where(
        (df["clase"] == Categoria.factureros_funcionamiento.value)
        & (df["concepto"].str.startswith("MUTUAL")),
        Categoria.factureros_mutual_funcionamiento.value,
        df["clase"],
    )

    ## Pago Seguro Factureros (Funcionamiento y EPAM)
    df["clase"] = np.where(
        (df["cod_imputacion"] == "032") & (df["concepto"].str.startswith("SEGURO")),
        Categoria.factureros_seguro_funcionamiento.value,
        df["clase"],
    )

    ## Reintegro comisiones imputado como reintegro viaticos
    df["clase"] = np.where(
        (df["cod_imputacion"] == "005") & (df["cta_cte"] == "130832-05"),
        Categoria.factureros_funcionamiento.value,
        df["clase"],
    )
    df["clase"] = np.where(
        (df["cod_imputacion"] == "005") & (df["cta_cte"] == "130832-07"),
        Categoria.factureros_epam.value,
        df["clase"],
    )

    # Ordenamos y seleccionamos columnas finales
    df = df.sort_values(
        ["fecha", "movimiento"],
        ascending=[True, True],
    )

    json_data = sanitize_dataframe_for_json(df).to_dict(orient="records")
    response = post_request(Endpoints.CONTROL_BANCO_SSCC.value, json_body=json_data)

    return df


# --------------------------------------------------
def compute_control_cruzado(ejercicios: List[int]) -> None:
    for ejercicio in ejercicios:
        try:
            groupby_cols = ["ejercicio", "mes", "fecha", "clase", "cta_cte"]
            siif = generate_banco_siif(ejercicio=ejercicio)
            siif["saldo"] = siif["saldo"] * (-1)
            siif = siif.groupby(groupby_cols)["saldo"].sum().reset_index()
            siif = siif.rename(columns={"saldo": "siif_importe"})
            sscc = generate_banco_sscc(ejercicio=ejercicio)
            sscc = sscc.groupby(groupby_cols)["importe"].sum().reset_index()
            sscc = sscc.rename(columns={"importe": "sscc_importe"})
            df = pd.merge(siif, sscc, how="outer", on=groupby_cols)
            df[["siif_importe", "sscc_importe"]] = df[
                ["siif_importe", "sscc_importe"]
            ].fillna(0)
            df["diferencia"] = df.siif_importe - df.sscc_importe
            df = df.sort_values(by=["ejercicio", "mes", "clase", "cta_cte"])

            json_data = sanitize_dataframe_for_json(df).to_dict(orient="records")
            response = post_request(
                Endpoints.CONTROL_BANCO_CRUZADO.value, json_body=json_data
            )
        except Exception as e:
            print(f"Error in compute_control_anual for ejercicio {ejercicio}: {e}")

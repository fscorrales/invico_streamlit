import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd
from playwright.async_api import async_playwright

from src.automation.siif.rci02 import Rci02
from src.constants.endpoints import Endpoints
from src.constants.options import get_ctas_ctes_df
from src.services.api_client import post_request


# --------------------------------------------------
@dataclass
class ControlRecursos:
    ejercicios: List[int]
    rci02_data: pd.DataFrame = field(init=False)

    # --------------------------------------------------
    def sync_control_recursos_from_sscc(
        self, sscc_username: str, sscc_password: str, token: str
    ) -> None:

        modulo_runner = "src.automation.sscc.banco_invico_runner"
        ejercicios_str = ",".join(map(str, self.ejercicios))

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
            ],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env,
        )

        # Esperamos que el SSCC termine antes de devolver el control a Streamlit
        process_sscc.wait()
        print("✅ SSCC Finalizado.")

    # --------------------------------------------------
    async def sync_control_recursos_from_siif(
        self, siif_username: str, siif_password: str
    ) -> List[str]:

        async with async_playwright() as p:
            siif = Rci02()
            # The Rf602 class handles login via SIIFReportManager.login
            await siif.login(
                username=siif_username,
                password=siif_password,
                playwright=p,
                headless=False,
            )
            await siif.go_to_reports()

            results = []
            self.rci02_data = (
                pd.DataFrame()
            )  # Initialize an empty DataFrame to store all data
            for ej in self.ejercicios:
                df_clean = await siif.download_and_process_report(ejercicio=ej)
                if df_clean is not None and not df_clean.empty:
                    self.rci02_data = pd.concat(
                        [self.rci02_data, df_clean], ignore_index=True
                    )  # Append new data to the main DataFrame
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_RCI02.value, json_body=json_data
                    )
                    results.append(f"Ejercicio {ej}: {response}")

            await siif.logout()

            print("✅ SIIF Finalizado")
            return results

    # --------------------------------------------------
    async def compute_control_recursos(self, ejercicio: int) -> None:
        try:
            group_by = ["ejercicio", "mes", "cta_cte", "grupo"]
            siif = await self.generate_siif_comprobantes_recursos(
                ejercicio=int(ejercicio)
            )
            # logger.info(f"siif.shape: {siif.shape}")
            siif = siif.loc[~siif["es_invico"]]
            siif = siif.loc[~siif["es_remanente"]]
            # logger.info(f"siif.shape: {siif.shape}")
            siif = siif.groupby(group_by)["importe"].sum()
            siif = siif.reset_index(drop=False)
            siif = siif.rename(columns={"importe": "recursos_siif"})
            # logger.info(f"siif.head: {siif.head()}")
            sscc = await self.generate_banco_invico(ejercicio=int(ejercicio))
            sscc = sscc.groupby(group_by)["importe"].sum()
            sscc = sscc.reset_index(drop=False)
            sscc = sscc.rename(columns={"importe": "depositos_banco"})
            # logger.info(f"sscc.head: {sscc.head()}")
            df = pd.merge(siif, sscc, how="outer")
            df = df.fillna(0)
            # logger.info(f"df.shape: {df.shape}, df.head: {df.head()}")

        except Exception as e:
            print(f"Error in compute_control_recursos: {e}")

    # --------------------------------------------------
    def generate_siif_comprobantes_recursos(
        self, ejercicio: int = None
    ) -> pd.DataFrame:
        df = self.get_siif_rci02_unified_cta_cte(
            ejercicio=ejercicio,
            filters={"es_verificado": True, "es_remanente": False},
        )
        if not df.empty:
            keep = ["MACRO"]
            df.loc[df.glosa.str.contains("|".join(keep)), "cta_cte"] = "Macro"
            df["grupo"] = np.where(
                df["cta_cte"] == "10270",
                "FONAVI",
                np.where(
                    df["cta_cte"].isin(["130832-12", "334", "Macro", "Patagonia"]),
                    "RECUPEROS",
                    "OTROS",
                ),
            )
            df.reset_index(drop=True, inplace=True)
        return df

    # --------------------------------------------------
    def get_siif_rci02_unified_cta_cte(self, ejercicio: int = None) -> pd.DataFrame:
        """
        Get the rci02 data from the repository.
        """
        df = self.rci02_data.copy()
        # df.reset_index(drop=True, inplace=True)
        ctas_ctes = get_ctas_ctes_df()
        map_to = ctas_ctes.loc[:, ["map_to", "siif_recursos_cta_cte"]]
        df = pd.merge(
            df, map_to, how="left", left_on="cta_cte", right_on="siif_recursos_cta_cte"
        )
        df["cta_cte"] = df["map_to"]
        df.drop(
            ["map_to", "siif_recursos_cta_cte", "_id"], axis="columns", inplace=True
        )
        return df

    # --------------------------------------------------
    async def generate_banco_invico(self, ejercicio: int = None) -> pd.DataFrame:
        dep_transf_int = ["034", "004"]
        dep_pf = ["214", "215"]
        dep_otros = ["003", "055", "005", "013"]
        dep_cert_neg = ["18"]
        filters = {
            "movimiento": "DEPOSITO",
            "cod_imputacion__nin": dep_transf_int + dep_pf + dep_otros + dep_cert_neg,
        }
        df = await self.get_banco_invico_unified_cta_cte(
            ejercicio=ejercicio, filters=filters
        )
        if not df.empty:
            df["grupo"] = np.where(
                df["cta_cte"] == "10270",
                "FONAVI",
                np.where(
                    df["cta_cte"].isin(["130832-12", "334", "Macro", "Patagonia"]),
                    "RECUPEROS",
                    "OTROS",
                ),
            )
            df.reset_index(drop=True, inplace=True)
        return df

    # --------------------------------------------------
    async def get_banco_invico_unified_cta_cte(
        self, ejercicio: int = None, filters: dict = {}
    ) -> pd.DataFrame:
        """
        Get the Banco INVICO data from the repository.
        """
        if ejercicio is not None:
            filters.update({"ejercicio": ejercicio})
        docs = await BancoINVICORepository().safe_find_by_filter(filters=filters)
        # logger.info(f"len(docs): {len(docs)}")
        df = pd.DataFrame(docs)
        df.reset_index(drop=True, inplace=True)
        if not df.empty:
            # logger.info(f"df.shape: {df.shape} - df.head: {df.head()}")
            ctas_ctes = get_ctas_ctes_df()
            map_to = ctas_ctes.loc[:, ["map_to", "sscc_cta_cte"]]
            df = pd.merge(
                df, map_to, how="left", left_on="cta_cte", right_on="sscc_cta_cte"
            )
            df["cta_cte"] = df["map_to"]
            df.drop(["map_to", "sscc_cta_cte"], axis="columns", inplace=True)
            # logger.info(f"df.shape: {df.shape} - df.head: {df.head()}")
        return df

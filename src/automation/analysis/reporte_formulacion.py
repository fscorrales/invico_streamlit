from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import (
    Rf602,
    Rf610,
    RfpP605b,
    Ri102,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services import post_request


# --------------------------------------------------
async def sync_reporte_formulacion_from_siif(
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
        # 🔹 RF602
        rf602 = Rf602(siif=connect_siif)
        await rf602.go_to_reports()
        for ej in ejercicios:
            df_clean = await rf602.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF602.value, json_body=json_data)
                results.append(f"RF602 Ejercicio {ej}: {response}")

        # 🔹 RF610
        rf610 = Rf610(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rf610.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF610.value, json_body=json_data)
                results.append(f"RF610 Ejercicio {ej}: {response}")

        # 🔹 RI102
        ri102 = Ri102(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await ri102.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RI102.value, json_body=json_data)
                results.append(f"RI102 Ejercicio {ej}: {response}")

        # 🔹 RFP_P605B
        rfp_p605b = RfpP605b(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rfp_p605b.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RFP_P605B.value, json_body=json_data
                )
                results.append(f"RFP_P605B Ejercicio {ej}: {response}")

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results

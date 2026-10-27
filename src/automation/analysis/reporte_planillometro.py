from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import (
    Rf610,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services import post_request


# --------------------------------------------------
async def sync_reporte_planillometro_from_siif(
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
        # 🔹 RF610
        rf610 = Rf610(siif=connect_siif)
        await rf610.go_to_reports()
        for ej in ejercicios:
            df_clean = await rf610.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF610.value, json_body=json_data)
                results.append(f"RF610 Ejercicio {ej}: {response}")

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results

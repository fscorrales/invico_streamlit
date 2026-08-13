from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import (
    Rci02,
    Rcocc31,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services import post_request


# --------------------------------------------------
async def sync_control_aporte_empresario_from_siif(
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
        # 🔹 RCI02
        rci02 = Rci02(siif=connect_siif)
        await rci02.go_to_reports()
        for ej in ejercicios:
            df_clean = await rci02.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RCI02.value, json_body=json_data)
                results.append(f"RCI02 Ejercicio {ej}: {response}")

        # 🔹 RCOCC31
        rcocc31 = Rcocc31(siif=connect_siif)
        for ej in ejercicios:
            for cta_contable in ["1112-2-6", "2122-1-2"]:
                df_clean = await rcocc31.download_and_process_report(
                    ejercicio=ej, cta_contable=cta_contable
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_RCOCC31.value, json_body=json_data
                    )
                    results.append(
                        f"Rcocc31 Ejercicio {ej} y cta. contable {cta_contable}: {response}"
                    )

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results

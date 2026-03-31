import os
import subprocess
import sys

from playwright.async_api import async_playwright

from src.automation.siif.rci02 import Rci02
from src.constants.endpoints import Endpoints
from src.services.api_client import post_request


# --------------------------------------------------
def sync_control_recursos_from_sscc(
    sscc_username: str, sscc_password: str, ejercicios: list[int], token: str
) -> None:

    modulo_runner = "src.automation.sscc.banco_invico_runner"
    ejercicios_str = ",".join(map(str, ejercicios))

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
    siif_username: str, siif_password: str, ejercicios: list[int]
) -> None:

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
        for ej in ejercicios:
            df_clean = await siif.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RCI02.value, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await siif.logout()

        print("✅ SIIF Finalizado")
        return results

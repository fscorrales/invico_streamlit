import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif.rci02 import Rci02
from src.constants.endpoints import Endpoints
from src.services.api_client import fetch_dataframe, post_request


# --------------------------------------------------
def sync_control_recursos_from_sscc(
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
async def sync_control_recursos_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:

    async with async_playwright() as p:
        siif = Rci02()
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


# --------------------------------------------------
def compute_control_recursos(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce SIIF vs SSCC delegado al backend (on-demand).

    Por cada ejercicio:

    1. ``GET /control/controlRecursos/generate?ejercicio=X``: el backend
       arma el cruce con sus propias colecciones (rci02 y Banco INVICO),
       sin descargar los crudos al cliente.
    2. ``POST /control/controlRecursos``: congela el snapshot del
       ejercicio en MongoDB (borrado idempotente por ejercicio), que es
       lo que luego leen el ``GET``, la exportación a Excel y el Google
       Sheet.

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            Endpoints.CONTROL_RECURSOS.value + "/generate",
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /generate no devolvió registros; "
                "no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(Endpoints.CONTROL_RECURSOS.value, json_body=json_data)
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results

from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import (
    Rci02,
    Rcocc31,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services.api_client import fetch_dataframe, post_request


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


# --------------------------------------------------
def compute_control_aporte_empresario(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce Recurso 3% vs Retención 337 delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlAporteEmpresario/generateIcaro?ejercicio=X``:
       el backend arma el cruce con sus propias colecciones (rci02,
       rcocc31 e ICARO), sin procesar nada en el cliente.
    2. ``POST /control/controlAporteEmpresario``: congela el snapshot del
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
            Endpoints.CONTROL_APORTE_EMPRESARIO.value + "/generateIcaro",
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /generateIcaro no devolvió registros; "
                "no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(
            Endpoints.CONTROL_APORTE_EMPRESARIO.value, json_body=json_data
        )
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results

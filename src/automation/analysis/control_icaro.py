from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import (
    GtoRpa03g,
    Rcg01Uejp,
    Rf602,
    Rf610,
    Rfondo07tp,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services.api_client import fetch_dataframe, post_request


# --------------------------------------------------
async def sync_control_icaro_from_siif(
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

        # 🔹 Rfondo07tp
        rfondo07tp = Rfondo07tp(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rfondo07tp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RFONDO07TP.value, json_body=json_data
                )
                results.append(f"Rfondo07tp Ejercicio {ej}: {response}")

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
def compute_control_icaro_anual(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del Control Anual SIIF vs ICARO delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlIcaro/computeControlAnual?ejercicio=X&limit=0``:
       el backend arma el control con sus propias colecciones (SIIF e
       ICARO), sin procesar nada en el cliente.
    2. ``POST /control/controlIcaro/anual``: congela el snapshot del
       ejercicio en la colección ``control_icaro_anual`` (borrado
       idempotente por ejercicio), que es lo que luego lee el ``GET`` de
       la página y la exportación a Excel/Google Sheet.

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        # limit=0: sin truncar (el FullFilter trae limit por defecto 100
        # y compute_control_anual aplica head() solo cuando limit > 0).
        df = fetch_dataframe(
            Endpoints.CONTROL_ICARO.value + "/computeControlAnual",
            params={"ejercicio": int(ejercicio), "limit": 0},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /computeControlAnual no devolvió "
                "registros; no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(
            Endpoints.CONTROL_ICARO_ANUAL.value, json_body=json_data
        )
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results


# --------------------------------------------------
def compute_control_icaro_comprobantes(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del Control de Comprobantes SIIF vs ICARO delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlIcaro/computeControlComprobantes?ejercicio=X&limit=0``:
       el backend arma el control con sus propias colecciones (SIIF e
       ICARO), sin procesar nada en el cliente.
    2. ``POST /control/controlIcaro/comprobantes``: congela el snapshot del
       ejercicio en la colección ``control_icaro_comprobantes`` (borrado
       idempotente por ejercicio), que es lo que luego lee el ``GET`` de
       la página.

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        # limit=0: sin truncar (compute_control_comprobantes reutiliza
        # get_siif_gastos, que aplica head() solo cuando limit > 0).
        df = fetch_dataframe(
            Endpoints.CONTROL_ICARO.value + "/computeControlComprobantes",
            params={"ejercicio": int(ejercicio), "limit": 0},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /computeControlComprobantes no devolvió "
                "registros; no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(
            Endpoints.CONTROL_ICARO_COMPROBANTES.value, json_body=json_data
        )
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results


# --------------------------------------------------
def compute_control_icaro_pa6(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del Control PA6 SIIF vs ICARO delegado al backend.

    Por cada ejercicio:

    1. ``GET /control/controlIcaro/computeControlPA6?ejercicio=X&limit=0``:
       el backend arma el control con sus propias colecciones (SIIF e
       ICARO), sin procesar nada en el cliente.
    2. ``POST /control/controlIcaro/pa6``: congela el snapshot del
       ejercicio en la colección ``control_icaro_pa6`` (borrado
       idempotente por ejercicio), que es lo que luego lee el ``GET`` de
       la página.

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    results: List[str] = []
    for ejercicio in ejercicios:
        # limit=0: sin truncar (compute_control_pa6 reutiliza
        # get_siif_pa6 y get_siif_gastos, que aplican head() solo
        # cuando limit > 0).
        df = fetch_dataframe(
            Endpoints.CONTROL_ICARO.value + "/computeControlPA6",
            params={"ejercicio": int(ejercicio), "limit": 0},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: /computeControlPA6 no devolvió "
                "registros; no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(Endpoints.CONTROL_ICARO_PA6.value, json_body=json_data)
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results

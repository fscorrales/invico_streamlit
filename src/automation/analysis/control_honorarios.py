import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import GtoRpa03g, Rcg01Uejp, login, logout
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_sgf_origenes, post_request


# --------------------------------------------------
def sync_control_honorarios_from_sgf(
    sgf_username: str, sgf_password: str, token: str, ejercicios: List[int]
) -> None:

    modulo_runner = "src.automation.sgf.resumen_rend_prov_runner"
    ejercicios_str = ",".join(map(str, ejercicios))
    origenes_str = ",".join(get_sgf_origenes())

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        # En PRODUCCIÓN (.exe): Pasamos el flag genérico Y LUEGO el string del módulo
        args = [
            sys.executable,
            "--automation",
            modulo_runner,  # 🚀 Se convierte en sys.argv[1] antes de que el arranque lo limpie
            sgf_username,
            sgf_password,
            token,
            ejercicios_str,
            origenes_str,
        ]
    else:
        # En DESARROLLO (.py): Tu comando tradicional por consola con -m
        args = [
            sys.executable,
            "-m",
            modulo_runner,
            sgf_username,
            sgf_password,
            token,
            ejercicios_str,
            origenes_str,
        ]

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process_sgf = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SGF termine antes de devolver el control a Streamlit
    process_sgf.wait()
    print("✅ SGF Finalizado.")


# --------------------------------------------------
def sync_control_honorarios_from_sscc(
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
async def sync_control_honorarios_from_siif(
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

        # 🔹Rcg01_Uejp
        rcg01_uejp = Rcg01Uejp(siif=connect_siif)
        await rcg01_uejp.go_to_reports()
        for ej in ejercicios:
            await rcg01_uejp.download_and_process_report(ejercicio=ej)
            rcg01_uejp.cta_cte_unifier()
            df_clean = rcg01_uejp.clean_df
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCG01_UEJP.value, json_body=json_data
                )
                results.append(f"Ejercicio {ej}: {response}")

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
def _compute_y_persistir(ruta_generate: str, ejercicios: List[int]) -> List[str]:
    """GET /generate por ejercicio → POST del snapshot en su colección.

    Compartido por ambos cruces de honorarios (SIIF vs Slave y SGF vs
    Slave): el backend arma el cruce on-demand con sus propias
    colecciones y luego se congela el snapshot con un POST (borrado
    idempotente por ejercicio).

    Los errores de red o de API se propagan a quien invoca (el modal de
    automatización los notifica con ``st.error``): no se tragan aquí.

    Args:
        ruta_generate: Ruta del endpoint on-demand (p.ej.
            ``/control/controlHonorarios/generateSIIFVsSlave``).
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    endpoint_snapshot = Endpoints.CONTROL_HONORARIOS.value
    ruta_snapshot = _snapshot_de(ruta_generate)
    results: List[str] = []
    for ejercicio in ejercicios:
        df = fetch_dataframe(
            endpoint_snapshot + ruta_generate,
            params={"ejercicio": int(ejercicio)},
        )
        if df.empty:
            results.append(
                f"Ejercicio {ejercicio}: el generate no devolvió registros; "
                "no se realizó el POST."
            )
            continue

        json_data = df.to_dict(orient="records")
        response = post_request(
            endpoint_snapshot + ruta_snapshot, json_body=json_data
        )
        results.append(f"Ejercicio {ejercicio}: {response}")

    return results


def _snapshot_de(ruta_generate: str) -> str:
    """Mapea la ruta /generate* a la ruta del snapshot correspondiente."""
    if "SIIF" in ruta_generate:
        return "/siifVsSlave"
    return "/sgfVsSlave"


# --------------------------------------------------
def compute_control_siif_vs_slave(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce SIIF vs Slave delegado al backend (on-demand).

    Por cada ejercicio:

    1. ``GET /control/controlHonorarios/generateSIIFVsSlave?ejercicio=X``
       : el backend arma el cruce (discrepancias SIIF vs Slave).
    2. ``POST /control/controlHonorarios/siifVsSlave``: congela el
       snapshot en la colección ``control_honorarios_siif_vs_slave``.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    return _compute_y_persistir("/generateSIIFVsSlave", ejercicios)


# --------------------------------------------------
def compute_control_sgf_vs_slave(ejercicios: List[int]) -> List[str]:
    """
    Pipeline del cruce SGF vs Slave delegado al backend (on-demand).

    Por cada ejercicio:

    1. ``GET /control/controlHonorarios/generateSGFVsSlave?ejercicio=X``
       : el backend arma el cruce (diferencias SGF vs Slave).
    2. ``POST /control/controlHonorarios/sgfVsSlave``: congela el
       snapshot en la colección ``control_honorarios_sgf_vs_slave``.

    Args:
        ejercicios: Ejercicios a recalcular.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    return _compute_y_persistir("/generateSGFVsSlave", ejercicios)

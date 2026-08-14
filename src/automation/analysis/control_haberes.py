import datetime as dt
import os
import subprocess
import sys
from typing import List

from playwright.async_api import async_playwright

from src.automation.siif import GtoRpa03g, Rcg01Uejp, Rcocc31, Rdeu012, login, logout
from src.constants.endpoints import Endpoints
from src.services.api_client import post_request


# --------------------------------------------------
def sync_control_haberes_from_sscc(
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
async def sync_control_haberes_from_siif(
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
            df_clean = await rcg01_uejp.download_and_process_report(ejercicio=ej)
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

        # 🔹Rdeu012
        # Obtenemos los meses a descargar
        ## 1. Obtenemos el año y mes actual dinámicamente
        ahora = dt.datetime.now()
        anio_actual = ahora.year
        mes_actual = ahora.month

        meses = []

        # 2. Iteramos por cada año y por cada mes
        for anio in sorted(ejercicios):
            for mes in range(1, 13):
                # Filtro 1: Limitación inferior (desde enero de 2010)
                if anio < 2010:
                    continue

                # Filtro 2: Limitación superior (no pasarse del mes/año actual)
                if anio == anio_actual and mes > mes_actual:
                    break  # Cortamos los meses siguientes de este año
                elif anio > anio_actual:
                    break  # Cortamos por completo si el año es futuro

                # 3. Formateamos a 'mmyyyy' (el :02d asegura el cero a la izquierda)
                periodo_str = f"{mes:02d}{anio}"
                meses.append(periodo_str)

        rdeu012 = Rdeu012(siif=connect_siif)
        for mes in meses:
            df_clean = await rdeu012.download_and_process_report(mes=mes)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RDEU012.value, json_body=json_data
                )
                results.append(f"Mes {mes}: {response}")

        # 🔹 Rcocc31
        rcocc31 = Rcocc31(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rcocc31.download_and_process_report(
                ejercicio=ej, cta_contable="2122-1-2"
            )
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCOCC31.value, json_body=json_data
                )
                results.append(f"RF610 Ejercicio {ej}: {response}")

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results

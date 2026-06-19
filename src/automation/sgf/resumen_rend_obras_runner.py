import os
import sys
import time
from pathlib import Path

from src.automation.sgf.connect_sgf import login
from src.automation.sgf.resumen_rend_obras import ResumenRendObras
from src.constants.endpoints import Endpoints
from src.services.api_client import post_request
from src.utils.handling_path import get_download_sgf_path


# --------------------------------------------------
def run():
    if len(sys.argv) < 3:
        print("Faltan credenciales")
        return

    username = sys.argv[1]
    password = sys.argv[2]
    token = sys.argv[3]
    # Recibimos el string "2024,2025" y lo convertimos en lista ['2024', '2025']
    ejercicios_raw = sys.argv[4] if len(sys.argv) > 3 else ""
    ejercicios = ejercicios_raw.split(",") if ejercicios_raw else []
    origenes_raw = sys.argv[5] if len(sys.argv) > 3 else ""
    origenes = origenes_raw.split(",") if origenes_raw else []

    print("🚀 Iniciando automatización SGF Resumen Rendiciones Obras...")

    save_path = Path(
        os.path.join(get_download_sgf_path(), "Resumen de Rendiciones Obras")
    )

    # Verifica si la carpeta NO existe, y la crea
    if not os.path.exists(save_path):
        # exist_ok=True evita errores si la carpeta se creó justo un milisegundo antes
        os.makedirs(save_path, exist_ok=True)

    try:
        with login(username, password) as conn:
            print(f"✅ Login exitoso: {username}")
            resumen_rend = ResumenRendObras(sgf=conn)

            results = []
            for origen in origenes:
                # Quitamos espacios por las dudas que el string
                origenes = origen.strip()
                if not origen:
                    continue

                for ejercicio in ejercicios:
                    # Quitamos espacios por las dudas que el string venga "2024, 2025"
                    ejercicio = ejercicio.strip()
                    if not ejercicio:
                        continue

                    resumen_rend.download_report(
                        dir_path=save_path, ejercicios=str(ejercicio), origenes=origen
                    )
                    filename = (
                        f"{str(ejercicio)}-resumen_rend_obras_{origen.lower()}.csv"
                    )
                    print(
                        f"✅ Reporte descargado: {Path(os.path.join(save_path, filename))}"
                    )
                    resumen_rend.read_csv_file(Path(os.path.join(save_path, filename)))
                    resumen_rend.process_dataframe()
                    df_clean = resumen_rend.clean_df
                    if df_clean is not None and not df_clean.empty:
                        # Send to backend
                        print(f"✅ Enviando ejercicio {ejercicio} a backend...")
                        json_data = df_clean.to_dict(orient="records")
                        response = post_request(
                            Endpoints.SGF_RESUMEN_REND_OBRAS.value,
                            json_body=json_data,
                            token=token,
                        )
                        results.append(
                            f"Ejercicio {ejercicio} y origen {origen}: {response}"
                        )

            return results

    except Exception as e:
        print(f"❌ Error en el runner: {e}")
        time.sleep(10)  # Para que no se cierre la consola y veas el error


# --------------------------------------------------
if __name__ == "__main__":
    run()

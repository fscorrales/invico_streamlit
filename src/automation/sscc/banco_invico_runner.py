import os
import sys
import time
from pathlib import Path

from src.automation.sscc.banco_invico import BancoINVICO
from src.automation.sscc.connect_sscc import login
from src.services.api_client import post_request
from src.utils.handling_path import get_download_sscc_path


# --------------------------------------------------
def run():
    if len(sys.argv) < 3:
        print("Faltan credenciales")
        return

    username = sys.argv[1]
    password = sys.argv[2]
    endpoint = sys.argv[3]
    # Recibimos el string "2024,2025" y lo convertimos en lista ['2024', '2025']
    ejercicios_raw = sys.argv[4] if len(sys.argv) > 4 else ""
    ejercicios = ejercicios_raw.split(",") if ejercicios_raw else []

    print("🚀 Iniciando automatización Banco INVICO...")

    save_path = Path(os.path.join(get_download_sscc_path(), "Banco INVICO"))

    # Verifica si la carpeta NO existe, y la crea
    if not os.path.exists(save_path):
        # exist_ok=True evita errores si la carpeta se creó justo un milisegundo antes
        os.makedirs(save_path, exist_ok=True)

    try:
        with login(username, password) as conn:
            print(f"✅ Login exitoso: {username}")
            banco_invico = BancoINVICO(sscc=conn)

            results = []
            for ejercicio in ejercicios:
                # Quitamos espacios por las dudas que el string venga "2024, 2025"
                ejercicio = ejercicio.strip()
                if not ejercicio:
                    continue

                banco_invico.download_report(
                    dir_path=save_path, ejercicios=str(ejercicio)
                )
                filename = str(ejercicio) + "-bancoINVICO.csv"
                banco_invico.read_csv_file(Path(os.path.join(save_path, filename)))
                banco_invico.process_dataframe()
                df_clean = banco_invico.clean_df
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(endpoint, json_body=json_data)
                    results.append(f"Ejercicio {ejercicio}: {response}")

            return results

    except Exception as e:
        print(f"❌ Error en el runner: {e}")
        time.sleep(10)  # Para que no se cierre la consola y veas el error


# --------------------------------------------------
if __name__ == "__main__":
    run()

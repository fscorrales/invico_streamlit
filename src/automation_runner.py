import sys
import time
from pathlib import Path

# Aseguramos que el script vea la carpeta src
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.automation.sscc.banco_invico import BancoINVICO
from src.automation.sscc.connect_sscc import login


def run():
    if len(sys.argv) < 3:
        print("Faltan credenciales")
        return

    username = sys.argv[1]
    password = sys.argv[2]

    try:
        with login(username, password) as conn:
            print(f"✅ Login exitoso: {username}")
            banco_invico = BancoINVICO(sscc=conn)

            # Aquí podrías pasar los ejercicios que necesites (quizás via sys.argv también)
            # banco_invico.download_report(...)

            print("🚀 Automatización completada.")
            time.sleep(2)  # Para que llegues a leer el mensaje en la consola

    except Exception as e:
        print(f"❌ Error en el runner: {e}")
        time.sleep(10)  # Para que no se cierre la consola y veas el error


if __name__ == "__main__":
    run()

import os
import subprocess


def run_streamlit_app():
    # Obtiene la  ruta del script de Streamlit
    script_path = os.path.join(os.path.dirname(__file__), "app.py")

    # Ejecuta Streamlit con la ruta del script
    subprocess.run(["streamlit", "run", script_path])

    # # Ensure the current working directory is the script's directory
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # os.chdir(script_dir)

    # # Run the Streamlit app using subprocess
    # subprocess.run(["streamlit", "run", "streamlit_app.py"])


if __name__ == "__main__":
    run_streamlit_app()

# poetry run python -m run
# poetry run streamlit run src/main.py

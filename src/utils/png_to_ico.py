"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 16-jun-2026
Purpose: Convert PNG to ICO
"""

from pathlib import Path

import typer
from PIL import Image

# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(help="Convert PNG to ICO", add_completion=False)


# --------------------------------------------------
@app.command()
def main(
    file: Path = typer.Option(
        None,
        "--file",
        "-f",
        help="PNG's full file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    try:
        # Cargamos el PNG de alta resolución que descargaste
        img = Image.open(file)

        # Definimos los tamaños estándar que Windows exige para un ejecutable profesional
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

        # Guardamos el archivo .ico empaquetando todas las capas de tamaño
        img.save("invico_automation.ico", sizes=icon_sizes)
        typer.secho("¡Archivo .ico multicapa creado con éxito!")

    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()

    # From /invico_streamlit

    # poetry run python -m src.utils.png_to_ico -f "D:\Datos INVICO\IT\invico_streamlit\icono_invico.png"

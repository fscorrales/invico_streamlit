#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 28-aug-2025
Purpose: Migrate from Planillometro Historico (Patricia) in XLSX
"""

__all__ = ["PlanillometroHist"]


from pathlib import Path

import numpy as np
import pandas as pd
import typer

from src.utils.handling_files import read_xls
from src.utils.print_tables import print_rich_table


# --------------------------------------------------
def validate_excel_file(value: Path):
    # Typer ya validó que el archivo existe y es legible.
    # Solo validamos extensión e integridad.
    if value and value.suffix.lower() not in [".xlsx", ".xls"]:
        raise typer.BadParameter(
            f"El archivo '{value}' no parece ser un archivo Excel (.xlsx o .xls)"
        )

    try:
        # Intentamos leer solo la primera fila para validar que no esté corrupto
        pd.read_excel(value, nrows=1)
    except Exception as e:
        raise typer.BadParameter(f"Error al abrir el archivo Excel: {e}")

    return value


# --------------------------------------------------
class PlanillometroHist:
    # --------------------------------------------------
    def __init__(self):
        self.clean_df = pd.DataFrame()

    # --------------------------------------------------
    def from_excel(self, excel_path: Path) -> pd.DataFrame:
        df = read_xls(excel_path, header=0)
        df = df.replace("", None)
        df["desc_programa"] = np.where(
            df["proy"].isna(), df["prog"] + " - " + df["Descripción"], np.nan
        )
        df["desc_programa"] = df["desc_programa"].ffill()
        df["desc_subprograma"] = df["subprog"] + " - --"
        df["desc_proyecto"] = np.where(
            df["obra"].isna(), df["proy"] + " - " + df["Descripción"], np.nan
        )
        df["desc_proyecto"] = df["desc_proyecto"].ffill()
        df["desc_actividad"] = np.where(
            ~df["estructura"].isna(), df["obra"] + " - " + df["Descripción"], np.nan
        )
        df = df.dropna(subset=["estructura"])
        df["acum_2008"] = df["acum_2008"].astype(float)
        df = df.loc[
            :,
            [
                "desc_programa",
                "desc_subprograma",
                "desc_proyecto",
                "desc_actividad",
                "actividad",
                "partida",
                "estructura",
                "alta",
                "acum_2008",
            ],
        ]
        self.clean_df = df
        return self.clean_df


# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(
    help="Migrate from Planillometro Historico in XLSX to MongoDB", add_completion=False
)


# --------------------------------------------------
@app.command()
def main(
    file: Path = typer.Option(
        None,
        "--file",
        "-f",
        help="XLS de Planillometro Historico (Patricia) report's full file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        callback=validate_excel_file,
    ),
):
    """
    Lee, procesa y escribe el reporte planillometro_hist de Patricia.
    """
    try:
        siif = PlanillometroHist()
        siif.from_excel(excel_path=file)
        print_rich_table(siif.clean_df, title=f"Datos del archivo: {file.name}")
    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()
    # From /invico_streamlit

    # poetry run python -m src.automation.siif.planillometro_hist -f "D:\Proyectos IT\invico_streamlit\src\automation\siif\planillometro_hist.xls"
    # poetry run python -m src.automation.siif.planillometro_hist -f"C:\IT\Proyectos\Python\invico_streamlit\src\automation\siif\planillometro_hist.xls"

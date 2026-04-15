#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 28-mar-2026
Purpose: Migrate from Ctas Ctes in XLSX to MongoDB
"""

from pathlib import Path

import pandas as pd
import typer

from src.constants.endpoints import Endpoints
from src.migration.migration_client import MigrationClient

from ...utils import (
    print_rich_table,
    read_xls,
)


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
def get_df_from_excel(excel_path: Path) -> pd.DataFrame:
    df = read_xls(excel_path, header=0)
    df = df.replace("NA", None)
    return df


# --------------------------------------------------
def migrate_df_to_mongodb(endpoint: str, df: pd.DataFrame) -> None:
    """Migrate DataFrame to MongoDB."""
    client = MigrationClient(token="token_bypassed")
    try:
        records = df.to_dict(orient="records")
        # El cliente maneja internamente el login y el POST
        result = client.post_batch(endpoint=endpoint, records=records)
        # post_request(endpoint=endpoint, json_body=records, token=token)
        print(f"Successfully migrated Rf602's {len(records)} records to MongoDB.")

    except Exception as e:
        print(f"Error migrar el DataFrame a MongoDB: {e}")


# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(
    help="Migrate from Ctas Ctes in XLSX to MongoDB", add_completion=False
)


# --------------------------------------------------
@app.command()
def main(
    file: Path = typer.Option(
        None,
        "--file",
        "-f",
        help="XLSX de Cuentas Corrientes report's full file path",
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
        df = get_df_from_excel(excel_path=file)
        print_rich_table(df, title=f"Datos del archivo: {file.name}")
        migrate_df_to_mongodb(endpoint=Endpoints.CTAS_CTES.value, df=df)
    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()
    # From /invico_streamlit

    # poetry run python -m src.migration.sscc.ctas_ctes -f "D:\Proyectos IT\invico_streamlit\src\migration\sscc\ctas_ctes_desc.xlsx"
    # poetry run python -m src.migration.sscc.ctas_ctes -f "C:\IT\Proyectos\Python\invico_streamlit\src\migration\sscc\ctas_ctes_desc.xlsx"+
    # poetry run python -m src.migration.sscc.ctas_ctes -f "D:\Datos INVICO\Python INVICO\invico_streamlit\src\migration\sscc\ctas_ctes_desc.xlsx"

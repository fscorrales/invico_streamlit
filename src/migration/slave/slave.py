#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 28-ago-2026
Purpose: Migrate from old Icaro.sqlite to new DB
"""

__all__ = ["SlaveMongoMigrator"]


import json
import os
from pathlib import Path

import pandas as pd
import typer

from ...constants.endpoints import Endpoints
from ...utils import print_rich_table, read_mdb_file
from ..migration_client import MigrationClient

# Firma oficial de encabezado para archivos Microsoft Access Jet Database (.mdb)
MDB_MAGIC_BYTES = b"\x00\x01\x00\x00Standard Jet DB"


# --------------------------------------------------
def validate_mdb_file(value: Path):
    if value is None:
        return value

    # Convertimos a string y normalizamos barras
    path_str = os.path.normpath(str(value))

    # Si detectamos que es una ruta de red pero le falta una barra inicial (común en Typer/Click)
    if path_str.startswith("\\") and not path_str.startswith("\\\\"):
        path_str = "\\" + path_str

    # Creamos un nuevo objeto Path con la ruta corregida
    fixed_path = Path(path_str)

    # 1. Validar existencia del archivo
    if not fixed_path.exists():
        raise typer.BadParameter(
            f"No se pudo encontrar el archivo en la red: '{path_str}'.\n"
            "Tip: Intenta poner la ruta entre comillas dobles en la terminal."
        )

    # 2. Validar extensión (.mdb o .accdb)
    if fixed_path.suffix.lower() not in [".mdb", ".accdb"]:
        raise typer.BadParameter(
            f"El archivo '{fixed_path.name}' no tiene una extensión válida de Microsoft Access (.mdb o .accdb)."
        )

    # 3. Validar integridad de encabezado (Magic Bytes)
    try:
        with open(fixed_path, "rb") as f:
            header = f.read(19)
            # Para archivos .mdb antiguos/estándar verificamos la firma Jet
            if fixed_path.suffix.lower() == ".mdb" and MDB_MAGIC_BYTES not in header:
                raise typer.BadParameter(
                    f"El archivo '{fixed_path.name}' no es una base de datos Access (.mdb) válida o está corrupto."
                )
    except typer.BadParameter:
        raise
    except Exception as e:
        raise typer.BadParameter(f"Error al leer e inspeccionar el archivo MDB: {e}")

    return fixed_path


# --------------------------------------------------
class SlaveMongoMigrator:
    # --------------------------------------------------
    def __init__(self, mdb_path: Path):
        self.mdb = mdb_path

    # --------------------------------------------------
    def migrate_df_to_mongodb(
        self, table: str, endpoint: str, df: pd.DataFrame
    ) -> None:
        """Migrate DataFrame to MongoDB."""
        # client = MigrationClient(token="token_bypassed")
        client = MigrationClient()
        client.login()
        try:
            records = df.to_dict(orient="records")

            # Aplicamos tu FIX directamente aquí
            clean_records = json.loads(
                json.dumps(
                    records,
                    default=lambda x: (
                        x.isoformat() if hasattr(x, "isoformat") else str(x)
                    ),
                )
            )

            # El cliente maneja internamente el login y el POST
            result = client.post_batch(endpoint=endpoint, records=clean_records)
            # post_request(endpoint=endpoint, json_body=records, token=token)
            print(f"Successfully migrated {table}'s {len(records)} records to MongoDB.")

        except Exception as e:
            print(f"Error migrar el DataFrame a MongoDB: {e}")

    # --------------------------------------------------
    def migrate_factureros(self):
        """Migrate FACTUREROS table to MongoDB."""
        table = "PRECARIZADOS"
        df = read_mdb_file(mdb_path=self.mdb, table_name=table)

        # Validación defensiva por si la lectura devolvió un DataFrame vacío
        if df.empty:
            print(f"⚠️ La tabla {table} está vacía o no se pudo extraer información.")
            return

        df.rename(
            columns={
                "Agentes": "beneficiario",
                "Actividad": "actividad",
                "Partida": "partida",
            },
            inplace=True,
        )

        df = df.drop_duplicates()
        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.SLAVE_FACTUREROS.value, df=df
        )

    # --------------------------------------------------
    def migrate_honorarios(self):
        """Migrate HONORARIOS Facturareros table to MongoDB."""
        table = "LIQUIDACIONHONORARIOS"
        df = read_mdb_file(mdb_path=self.mdb, table_name=table)

        # Validación defensiva por si la lectura devolvió un DataFrame vacío
        if df.empty:
            print(f"⚠️ La tabla {table} está vacía o no se pudo extraer información.")
            return

        df.rename(
            columns={
                "Fecha": "fecha",
                "Proveedor": "beneficiario",
                "Sellos": "sellos",
                "Seguro": "seguro",
                "Tipo": "tipo",
                "Comprobante": "nro_comprobante",
                "MontoBruto": "importe_bruto",
                "IIBB": "iibb",
                "LibramientoPago": "lp",
                "OtraRetencion": "otras_retenciones",
                "Anticipo": "anticipo",
                "Descuento": "descuento",
                "Actividad": "actividad",
                "Partida": "partida",
            },
            inplace=True,
        )

        # df["fecha"] = pd.to_timedelta(df["fecha"], unit="D") + pd.Timestamp(
        #     "1970-01-01"
        # )
        df["ejercicio"] = df["fecha"].dt.year
        df["mes"] = df["fecha"].dt.strftime("%m/%Y")
        df["mutual"] = 0
        df["embargo"] = 0
        keep = ["NoSIIF"]
        df = df.loc[~df.nro_comprobante.str.contains("|".join(keep))]

        # df = df.loc[
        #     :,
        #     [
        #         "ejercicio",
        #         "mes",
        #         "fecha",
        #         "nro_comprobante",
        #         "tipo",
        #         "beneficiario",
        #         "actividad",
        #         "partida",
        #         "importe_bruto",
        #         "iibb",
        #         "lp",
        #         "sellos",
        #         "seguro",
        #         "anticipo",
        #         "descuento",
        #         "mutual",
        #         "embargo",
        #     ],
        # ]

        df["updated_at"] = pd.Timestamp.now()

        ejercicios = df["ejercicio"].unique()
        for ejercicio in ejercicios:
            df_ejercicio = df.loc[df["ejercicio"] == ejercicio]
            self.migrate_df_to_mongodb(
                table=table, endpoint=Endpoints.SLAVE_HONORARIOS.value, df=df_ejercicio
            )

        print_rich_table(df, title=f"Tabla Exportada: {table}")

    # --------------------------------------------------
    def migrate_all(self):
        return_schema = []
        return_schema.append(self.migrate_factureros())
        return_schema.append(self.migrate_honorarios())
        return return_schema


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
        help="MDB database file path",
        exists=False,
        file_okay=True,
        dir_okay=False,
        readable=False,
        callback=validate_mdb_file,
    ),
):
    """
    Lee, procesa y escribe el reporte planillometro_hist de Patricia.
    """
    try:
        migrator = SlaveMongoMigrator(
            mdb_path=file,
        )
        migrator.migrate_honorarios()
        typer.secho(
            f"✅ Migración completada con éxito desde {file.name}.",
            fg=typer.colors.GREEN,
        )
    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()
    # From /invico_streamlit

    # poetry run python -m src.migration.slave.slave -f "D:\Datos INVICO\IT\invico_streamlit\src\migration\slave\Slave.accdb"

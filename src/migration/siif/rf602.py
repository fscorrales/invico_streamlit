#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 13-mar-2026
Purpose: Migrate SIIF's rf602 (Prespuesto de Gastos por Fuente) from SQLite to MongoDB
"""

__all__ = ["sync_rf602_to_mongodb"]

import argparse
import os

import pandas as pd

from ...services.api_client import post_request
from ...utils import (
    get_df_from_sql_table,
)

ENDPOINT = "/siif/rf602"


# --------------------------------------------------
def get_args():
    """Get command-line arguments"""

    parser = argparse.ArgumentParser(
        description="Migrate SIIF's rf602 (Prespuesto de Gastos por Fuente) from SQLite to MongoDB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # parser.add_argument(
    #     "-u",
    #     "--base_url",
    #     metavar="base_url",
    #     default=None,
    #     type=str,
    #     help="API's Base URL (also can be set with the environment variable BASE_URL)",
    # )

    parser.add_argument(
        "-s",
        "--sqlite_path",
        metavar="sqlite_path",
        default=None,
        type=str,
        help="Path to the SQLite database file containing the rf602 data to migrate (also can be set with the environment variable SQLITE_PATH)",
    )

    args = parser.parse_args()

    if args.sqlite_path is None:
        from ...utils.hangling_path import get_sqlite_path

        args.sqlite_path = os.path.join(get_sqlite_path(), "siif.sqlite")

        if args.sqlite_path is None:
            parser.error("--sqlite_path is required.")

    return args


# --------------------------------------------------
def get_df_from_sqlite(sqlite_path: str) -> pd.DataFrame:
    """Download, process and sync the rf602 report to the repository."""
    try:
        df = get_df_from_sql_table(sqlite_path, table="ppto_gtos_fte_rf602")
        df.drop(columns=["id"], inplace=True)
        df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce")
        # df = df.loc[df["ejercicio"] < 2025]
        df = df.loc[df["ejercicio"] == 2025]

        return df

    except Exception as e:
        print(f"Error migrar y sincronizar el reporte: {e}")


# --------------------------------------------------
def migrate_df_to_mongodb(endpoint: str, df: pd.DataFrame) -> None:
    """Migrate DataFrame to MongoDB."""
    try:
        records = df.to_dict(orient="records")
        post_request(endpoint=endpoint, json_body=records)
        print(f"Successfully migrated {len(records)} records to MongoDB.")

    except Exception as e:
        print(f"Error migrar el DataFrame a MongoDB: {e}")


# --------------------------------------------------
def sync_rf602_to_mongodb(sqlite_path: str, endpoint: str) -> None:
    """Download, process and sync the rf602 report to the repository."""
    try:
        df = get_df_from_sqlite(sqlite_path=sqlite_path)
        ejercicios = df["ejercicio"].unique()
        for ejercicio in ejercicios:
            df_ejercicio = df.loc[df["ejercicio"] == ejercicio]
            migrate_df_to_mongodb(endpoint=endpoint, df=df_ejercicio)

    except Exception as e:
        print(f"Error migrar y sincronizar el reporte: {e}")


# --------------------------------------------------
def main():
    """Make a jazz noise here"""

    args = get_args()

    print(f"SQLite Path: {args.sqlite_path}")

    sync_rf602_to_mongodb(
        sqlite_path=args.sqlite_path,
        endpoint=ENDPOINT,
    )

    # save_path = os.path.dirname(
    #     os.path.abspath(inspect.getfile(inspect.currentframe()))
    # )

    # async with async_playwright() as p:
    #     connect_siif = await login(
    #         args.username, args.password, playwright=p, headless=False
    #     )
    #     try:
    #         rf602 = Rf602(siif=connect_siif)
    #         await rf602.go_to_reports()
    #         await rf602.go_to_specific_report()
    #         for ejercicio in args.ejercicios:
    #             if args.download:
    #                 await rf602.download_report(ejercicio=str(ejercicio))
    #                 await rf602.save_xls_file(
    #                     save_path=save_path,
    #                     file_name=str(ejercicio) + "-rf602.xls",
    #                 )
    #             await rf602.read_xls_file(args.file)
    #             print(rf602.df)
    #             await rf602.process_dataframe()
    #             print(rf602.clean_df)
    #     except Exception as e:
    #         print(f"Error al iniciar sesión: {e}")
    #     finally:
    # await rf602.logout()


# --------------------------------------------------
if __name__ == "__main__":
    main()
    # From /invico_streamlit

    # poetry run python -m src.migration.siif.rf602

#!/usr/bin/env python3
"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Working With Files in Python
Source: https://realpython.com/working-with-files-in-python/#:~:text=To%20get%20a%20list%20of,scandir()%20in%20Python%203.
"""

__all__ = ["get_df_from_sql_table", "read_xls_file", "read_csv_file", "get_df_from_mdb"]


import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Union

import pandas as pd


# --------------------------------------------------
def get_df_from_sql_table(sqlite_path: str, table: str) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)


# --------------------------------------------------
def read_xls_file(
    file_path: Union[Path, str, BytesIO], header: int = None
) -> pd.DataFrame:
    """ "Read from xls report"""
    df = pd.read_excel(
        file_path, index_col=None, header=header, na_filter=False, dtype=str
    )
    if header is None:
        df.columns = [str(x) for x in range(df.shape[1])]
    return df


# --------------------------------------------------
def read_csv_file(file_path: Union[Path, str, BytesIO]) -> pd.DataFrame:
    """Read csv file"""
    try:
        nombres_columnas = [str(i) for i in range(100)]
        df = pd.read_csv(
            file_path,
            names=nombres_columnas,  # Forzamos a que acepte hasta 100 columnas
            index_col=None,
            header=None,
            na_filter=False,
            dtype=str,
            encoding="ISO-8859-1",
        )
        df.columns = [str(x) for x in range(df.shape[1])]
        return df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return pd.DataFrame()


# --------------------------------------------------
def get_df_from_mdb(mdb_path: Union[Path, str], table_name: str) -> pd.DataFrame:
    """
    Lee una tabla desde un archivo Access (.mdb) intentando primero con pyodbc
    y haciendo fallback a access_parser si falla.
    """
    path_str = str(mdb_path)

    # INTENTO 1: pyodbc (Motor nativo ODBC de Windows)
    try:
        import pyodbc

        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={path_str};"
        )
        with pyodbc.connect(conn_str) as conn:
            query = f"SELECT * FROM [{table_name}]"
            df = pd.read_sql_query(query, conn)
            print(
                f"✅ Tabla '{table_name}' leída exitosamente con pyodbc ({len(df)} registros)."
            )
            return df

    except Exception as e_odbc:
        print(
            f"⚠️ No se pudo leer '{table_name}' con pyodbc ({e_odbc}). Intentando con access_parser..."
        )

    # INTENTO 2: access_parser (Pure Python)
    try:
        from access_parser import AccessParser

        db = AccessParser(path_str)
        if table_name in db.catalog:
            data = db.parse_table(table_name)
            df = pd.DataFrame(data)
            print(
                f"✅ Tabla '{table_name}' leída exitosamente con access_parser ({len(df)} registros)."
            )
            return df
        else:
            print(f"❌ La tabla '{table_name}' no existe en el catálogo MDB.")
            return pd.DataFrame()

    except Exception as e_parser:
        print(
            f"❌ Error crítico leyendo la tabla '{table_name}' con access_parser: {e_parser}"
        )
        return pd.DataFrame()

#!/usr/bin/env python3
"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Working With Files in Python
Source: https://realpython.com/working-with-files-in-python/#:~:text=To%20get%20a%20list%20of,scandir()%20in%20Python%203.
"""

__all__ = [
    "get_df_from_sql_table",
]


import sqlite3

import pandas as pd


# --------------------------------------------------
def get_df_from_sql_table(sqlite_path: str, table: str) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {table}", conn)

#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 19-jun-2026
Purpose: Read, process and write SGF's 'Resumen Rend Prov' report
"""

__all__ = ["ResumenRendProv"]


import datetime as dt
import inspect
import os
import time
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd
import typer
from pywinauto import keyboard

from src.automation.sgf.connect_sgf import (
    SGFReportManager,
    login,
)
from src.services import cta_cte_unifier
from src.utils.print_tables import print_rich_table


# --------------------------------------------------
class ResumenRendProv(SGFReportManager):
    # --------------------------------------------------
    def download_report(
        self,
        dir_path: Path,
        ejercicios: Union[List, str] = str(dt.datetime.now().year),
        origenes: Union[List, str] = "EPAM",
    ) -> None:
        try:
            if not isinstance(ejercicios, list):
                ejercicios = [ejercicios]
            if not isinstance(origenes, list):
                origenes = [origenes]
            for origen in origenes:
                for ejercicio in ejercicios:
                    # Open menu Consulta General de Movimientos
                    self.sgf.main.menu_select("Informes->Resumen de Rendiciones")

                    dlg_resumen_rend = self.sgf.main.child_window(
                        title="Informes - Resumen de Rendiciones", control_type="Window"
                    )
                    dlg_resumen_rend.wait("exists")

                    int_ejercicio = int(ejercicio)
                    if int_ejercicio > 2010 and int_ejercicio <= dt.datetime.now().year:
                        campo_desde = dlg_resumen_rend.child_window(
                            control_type="Pane", found_index=1
                        )
                        campo_hasta = dlg_resumen_rend.child_window(
                            control_type="Pane", found_index=2
                        )
                        # Fecha Desde
                        campo_desde.click_input()  # Hace foco y cae en el AÑO por defecto
                        time.sleep(0.5)
                        keyboard.send_keys(ejercicio)  # Escribe el año (ej. 2026)

                        keyboard.send_keys("{LEFT}")  # Se mueve al MES
                        time.sleep(0.5)
                        keyboard.send_keys("01")  # Escribe el mes

                        keyboard.send_keys("{LEFT}")  # Se mueve al DÍA
                        time.sleep(0.5)
                        keyboard.send_keys("01")  # Escribe el día

                        # Fecha Hasta
                        fecha_hasta = dt.datetime(
                            year=(int_ejercicio), month=12, day=31
                        )
                        fecha_hasta = min(fecha_hasta, dt.datetime.now())
                        str_dia = fecha_hasta.strftime("%d")
                        str_mes = fecha_hasta.strftime("%m")
                        str_anio = fecha_hasta.strftime("%Y")

                        campo_hasta.click_input()  # Hace foco y cae en el AÑO por defecto
                        time.sleep(0.5)
                        keyboard.send_keys(str_anio)  # Escribe el año

                        keyboard.send_keys("{LEFT}")  # Se mueve al MES
                        time.sleep(0.5)
                        keyboard.send_keys(str_mes)  # Escribe el mes

                        keyboard.send_keys("{LEFT}")  # Se mueve al DÍA
                        time.sleep(0.5)
                        keyboard.send_keys(str_dia)  # Escribe el día

                        time.sleep(0.5)

                        # Origen
                        cmb_origen = self.sgf.main.child_window(
                            auto_id="24", control_type="ComboBox"
                        ).wrapper_object()
                        cmb_origen.type_keys("%{DOWN}")
                        cmb_origen.type_keys(
                            origen, with_spaces=True
                        )  # EPAM, OBRAS, FUNCIONAMIENTO
                        keyboard.send_keys("{ENTER}")
                        btn_exportar = self.sgf.main.child_window(
                            title="Exportar", auto_id="4", control_type="Button"
                        ).wait("enabled ready active", timeout=60)

                        # Exportar
                        btn_exportar.click()
                        btn_accept = self.sgf.main.child_window(
                            title="Aceptar", auto_id="9", control_type="Button"
                        ).wait("exists enabled visible ready", timeout=360)
                        btn_accept.click()
                        time.sleep(5)

                        # Armamos el nombre del reporte y su ruta absoluta temporal
                        report_name = (
                            f"{ejercicio}-resumen_rend_prov_{origen.lower()}.csv"
                        )
                        # Forzamos a que se guarde directo en tu Escritorio de forma absoluta
                        temp_file_path = os.path.join(dir_path, report_name)

                        # Como la ventana "Exportar" tiene el foco y el cursor está en el campo Nombre:
                        # Borramos lo que haya y mandamos la ruta completa con el teclado del sistema
                        keyboard.send_keys("^a{BACKSPACE}")
                        time.sleep(0.5)
                        keyboard.send_keys(temp_file_path, with_spaces=True)
                        time.sleep(1)

                        # En lugar de buscar el botón Guardar por código, presionamos ENTER.
                        # En las ventanas de diálogo de Windows, ENTER ejecuta la acción principal (Guardar).
                        keyboard.send_keys("{ENTER}")
                        time.sleep(2)

                        # # Si llega a aparecer el cartel de "El archivo ya existe, ¿desea reemplazarlo?"
                        # # mandamos una "S" o un "ENTER" para confirmar el reemplazo
                        # keyboard.send_keys("{ENTER}")
                        # time.sleep(2)

                        self.sgf.main.wait("active", timeout=120)

                        # Cerrar ventana
                        keyboard.send_keys("{F10}")

        except Exception as e:
            print(f"Ocurrió un error: {e}, {type(e)}")
            self.logout()

    # --------------------------------------------------
    def process_dataframe(self, dataframe: pd.DataFrame = None) -> pd.DataFrame:
        """ "Transform read xls file"""
        if dataframe is None:
            df = self.df.copy()
        else:
            df = dataframe.copy()
        df["origen"] = df["6"].str.split("-", n=1).str[0]
        df["origen"] = df["origen"].str.split("=", n=1).str[1]
        df["origen"] = df["origen"].str.replace('"', "")
        df["origen"] = df["origen"].str.strip()

        if df.loc[0, "origen"] == "OBRAS":
            df = df.rename(
                columns={
                    "23": "beneficiario",
                    "25": "libramiento",
                    "26": "fecha",
                    "27": "movimiento",
                    "24": "cta_cte",
                    "28": "importe_bruto",
                    "29": "gcias",
                    "30": "sellos",
                    "31": "iibb",
                    "32": "suss",
                    "33": "invico",
                    "34": "otras",
                    "35": "importe_neto",
                }
            )
            df["destino"] = ""
            df["seguro"] = "0"
            df["salud"] = "0"
            df["mutual"] = "0"
        else:
            df = df.rename(
                columns={
                    "26": "beneficiario",
                    "27": "destino",
                    "29": "libramiento",
                    "30": "fecha",
                    "31": "movimiento",
                    "28": "cta_cte",
                    "32": "importe_bruto",
                    "33": "gcias",
                    "34": "sellos",
                    "35": "iibb",
                    "36": "suss",
                    "37": "invico",
                    "38": "seguro",
                    "39": "salud",
                    "40": "mutual",
                    "41": "importe_neto",
                }
            )
            df["otras"] = "0"

        df["ejercicio"] = df["fecha"].str[-4:]
        df["mes"] = df["fecha"].str[3:5] + "/" + df["ejercicio"]
        df["cta_cte"] = np.where(
            df["beneficiario"] == "CREDITO ESPECIAL", "130832-07", df["cta_cte"]
        )

        df = df.loc[
            :,
            [
                "origen",
                "ejercicio",
                "mes",
                "fecha",
                "beneficiario",
                "destino",
                "libramiento",
                "movimiento",
                "cta_cte",
                "importe_bruto",
                "gcias",
                "sellos",
                "iibb",
                "suss",
                "invico",
                "seguro",
                "salud",
                "mutual",
                "otras",
                "importe_neto",
            ],
        ]

        df.loc[:, "importe_bruto":] = df.loc[:, "importe_bruto":].apply(
            lambda x: x.str.replace(",", "").astype(float)
        )

        df["retenciones"] = df.loc[:, "gcias":"otras"].sum(axis=1)

        df["importe_bruto"] = np.where(
            df["origen"] == "EPAM",
            df["importe_bruto"] + df["invico"],
            df["importe_bruto"],
        )

        df["ejercicio"] = df["fecha"].str[-4:]
        df["mes"] = df["fecha"].str[3:5] + "/" + df["ejercicio"]
        df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce")
        df["cta_cte"] = np.where(
            df["beneficiario"] == "CREDITO ESPECIAL", "130832-07", df["cta_cte"]
        )

        df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y")
        df["fecha"] = df["fecha"].apply(
            lambda x: x.to_pydatetime() if pd.notnull(x) else None
        )

        self.clean_df = df
        return self.clean_df

    # --------------------------------------------------
    def cta_cte_unifier(self, token: Optional[str] = None):
        self.clean_df = cta_cte_unifier(
            original_df=self.clean_df, cta_cte_nexo="sgf_cta_cte", token=token
        )

    # --------------------------------------------------
    def add_cuit_from_desc_prov(self):
        pass


# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(
    help="Read, process and write SGF's 'Resumen Rendición Proveedores' report",
    add_completion=False,
)


# --------------------------------------------------
@app.command()
def main(
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Username for SGF access"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for SGF access"
    ),
    ejercicios: List[int] = typer.Option(
        [dt.datetime.now().year],
        "--ejercicios",
        "-e",
        help="Ejercicios to download from SGF",
    ),
    origenes: List[str] = typer.Option(
        ["EPAM"],
        "--origenes",
        "-o",
        help="Origenes to download from SGF",
    ),
    download: bool = typer.Option(
        False, "--download", "-d", help="Download report from SGF"
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="SGF csv report's full file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """
    Lee, procesa y escribe el reporte Resumen Rendición Proveedores del SGF.
    """

    # 1. Validación de lógica de negocio (Exclusión mutua)
    if file and download:
        typer.secho(
            "❌ Error: No puedes usar --file y --download al mismo tiempo.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    # Validación de ejercicios
    ejercicios_ok = []
    for ejercicio in ejercicios:
        if ejercicio not in list(range(2020, dt.datetime.now().year + 1)):
            typer.secho(
                f"❌ Error: Ejercicio {ejercicio} fuera del rango permitido (2010-{dt.datetime.now().year}).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        else:
            ejercicios_ok.append(ejercicio)

    ejercicios = ejercicios_ok

    # Validación de ejercicios
    origenes_ok = []
    for origen in origenes:
        if origen not in ["EPAM", "OBRAS", "FUNCIONAMIENTO"]:
            typer.secho(
                f"❌ Error: Origen {origen} fuera del rango permitido ({['EPAM', 'OBRAS', 'FUNCIONAMIENTO']}).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        else:
            origenes_ok.append(origen)

    origenes = origenes_ok

    # 2. Carga de credenciales (Lógica que tenías en get_args)
    if username is None or password is None:
        try:
            from ...config import settings

            username = username or settings.SGF_USERNAME
            password = password or settings.SGF_PASSWORD
        except ImportError:
            pass

        if not username or not password:
            typer.secho(
                "❌ Error: Se requieren credenciales (vía argumentos o config).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    save_path = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe()))
    )

    # 3. Lógica de ejecución
    try:
        if download:
            with login(username, password) as conn:
                resumen_rend = ResumenRendProv(sgf=conn)
                typer.echo("⏳ Descargando reporte banco_invico...")
                for origen in origenes:
                    for ejercicio in ejercicios:
                        resumen_rend.download_report(
                            dir_path=save_path,
                            ejercicios=str(ejercicio),
                            origenes=origen,
                        )
                        typer.secho(
                            f"✅ Origen {origen} y ejercicio {ejercicio} descargado con éxito.",
                            fg=typer.colors.GREEN,
                        )
                        filename = (
                            f"{str(ejercicio)}-resumen_rend_prov_{origen.lower()}.csv"
                        )
                        resumen_rend.read_csv_file(
                            Path(os.path.join(save_path, filename))
                        )
                        resumen_rend.process_dataframe()
                        print_rich_table(
                            resumen_rend.clean_df,
                            title=f"Resumen Rend. Prov. {origen} {ejercicio}",
                        )
        else:
            resumen_rend = ResumenRendProv()
            # 1. Lectura y Procesamiento
            typer.echo(f"⏳ Procesando archivo: {file.name}...")
            resumen_rend.read_csv_file(file)
            resumen_rend.process_dataframe()
            typer.secho(
                f"✅ Archivo {file.name} procesado con éxito.",
                fg=typer.colors.GREEN,
            )
            print_rich_table(
                resumen_rend.clean_df, title=f"Datos del archivo: {file.name}"
            )
    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()

    # From /invico_streamlit

    # poetry run python -m src.automation.sgf.resumen_rend_prov -d
    # poetry run python -m src.automation.sgf.resumen_rend_prov -f "D:\Datos INVICO\IT\invico_streamlit\src\automation\sgf\2026-resumen_rend_prov_epam.csv"

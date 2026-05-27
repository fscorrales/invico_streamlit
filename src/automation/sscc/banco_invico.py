#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 11-jul-2025
Purpose: Read, process and write SSCC's 'Banco INVICO' report
"""

__all__ = ["BancoINVICO"]


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

from src.automation.sscc.connect_sscc import (
    SSCCReportManager,
    login,
)
from src.utils.print_tables import print_rich_table


# --------------------------------------------------
class BancoINVICO(SSCCReportManager):
    # --------------------------------------------------
    def download_report(
        self,
        dir_path: Path,
        ejercicios: Union[List, str] = str(dt.datetime.now().year),
    ) -> None:
        try:
            if not isinstance(ejercicios, list):
                ejercicios = [ejercicios]
            for ejercicio in ejercicios:
                # Open menu Consulta General de Movimientos
                self.sscc.main.menu_select("Informes->Consulta General de Movimientos")

                dlg_consulta_gral_mov = self.sscc.main.child_window(
                    title="Consulta General de Movimientos (Vista No Actualizada)",
                    control_type="Window",
                )
                dlg_consulta_gral_mov.wait("exists")

                int_ejercicio = int(ejercicio)
                if int_ejercicio > 2010 and int_ejercicio <= dt.datetime.now().year:
                    campo_desde = dlg_consulta_gral_mov.child_window(
                        control_type="Pane", found_index=1
                    )
                    campo_hasta = dlg_consulta_gral_mov.child_window(
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
                    fecha_hasta = dt.datetime(year=(int_ejercicio), month=12, day=31)
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

                    # Actualizar
                    time.sleep(1)
                    keyboard.send_keys("{F5}")
                    vertical_scroll = self.sscc.main.child_window(
                        title="Vertical",
                        auto_id="NonClientVerticalScrollBar",
                        control_type="ScrollBar",
                        found_index=0,
                    )
                    vertical_scroll.wait("exists enabled visible ready", timeout=120)

                    # Exportar
                    keyboard.send_keys("{F7}")
                    btn_accept = self.sscc.main.child_window(
                        title="Aceptar", auto_id="9", control_type="Button"
                    )
                    btn_accept.wait("exists enabled visible ready")
                    btn_accept.click()
                    time.sleep(5)

                    # Armamos el nombre del reporte y su ruta absoluta temporal
                    report_name = f"{ejercicio}-bancoINVICO.csv"
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

                    # Si llega a aparecer el cartel de "El archivo ya existe, ¿desea reemplazarlo?"
                    # mandamos una "S" o un "ENTER" para confirmar el reemplazo
                    keyboard.send_keys("{ENTER}")
                    time.sleep(2)

                    dlg_consulta_gral_mov = self.sscc.main.child_window(
                        title="Consulta General de Movimientos", control_type="Window"
                    )
                    dlg_consulta_gral_mov.wait("active", timeout=60)

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
        df = df.replace(to_replace="[\r\n]", value="")
        df["21"] = df["21"].str.strip()
        df = df.assign(
            fecha=df["20"],
            ejercicio=df["20"].str[-4:],
            mes=df["20"].str[3:5] + "/" + df["20"].str[-4:],
            cta_cte=df["22"],
            movimiento=df["21"],
            es_cheque=np.where(
                (df["21"] == "DEBITO") | (df["21"] == "DEPOSITO"), False, True
            ),
            concepto=df["23"],
            beneficiario=df["24"],
            moneda=df["25"],
            libramiento=df["26"],
            imputacion=df["27"],
            importe=df["28"].str.replace(",", "").astype(float),
        )
        df[["cod_imputacion", "imputacion"]] = df["imputacion"].str.split(
            pat="-", n=1, expand=True
        )
        df = df.loc[
            :,
            [
                "ejercicio",
                "mes",
                "fecha",
                "cta_cte",
                "movimiento",
                "es_cheque",
                "beneficiario",
                "importe",
                "concepto",
                "moneda",
                "libramiento",
                "cod_imputacion",
                "imputacion",
            ],
        ]

        df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y")
        df["fecha"] = df["fecha"].apply(
            lambda x: x.to_pydatetime() if pd.notnull(x) else None
        )

        self.clean_df = df
        return self.clean_df


# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(
    help="Read, process and write SSCC's 'Banco INVICO' report", add_completion=False
)


# --------------------------------------------------
@app.command()
def main(
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Username for SSCC access"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for SSCC access"
    ),
    ejercicios: List[int] = typer.Option(
        [dt.datetime.now().year],
        "--ejercicios",
        "-e",
        help="Ejercicios to download from SSCC",
    ),
    download: bool = typer.Option(
        False, "--download", "-d", help="Download report from SSCC"
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="SSCC csv report's full file path",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """
    Lee, procesa y escribe el reporte banco_invico del SIIF.
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

    # 2. Carga de credenciales (Lógica que tenías en get_args)
    if username is None or password is None:
        try:
            from ...config import settings

            username = username or settings.SSCC_USERNAME
            password = password or settings.SSCC_PASSWORD
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
                banco_invico = BancoINVICO(sscc=conn)
                typer.echo("⏳ Descargando reporte banco_invico...")
                for ejercicio in ejercicios:
                    banco_invico.download_report(
                        dir_path=save_path, ejercicios=str(ejercicio)
                    )
                    typer.secho(
                        f"✅ Ejercicio {ejercicio} descargado con éxito.",
                        fg=typer.colors.GREEN,
                    )
                    filename = str(ejercicio) + "-bancoINVICO.csv"
                    banco_invico.read_csv_file(Path(os.path.join(save_path, filename)))
                    banco_invico.process_dataframe()
                    print_rich_table(
                        banco_invico.clean_df, title=f"Banco INVICO {ejercicio}"
                    )
        else:
            banco_invico = BancoINVICO()
            # 1. Lectura y Procesamiento
            typer.echo(f"⏳ Procesando archivo: {file.name}...")
            banco_invico.read_csv_file(file)
            banco_invico.process_dataframe()
            typer.secho(
                f"✅ Archivo {file.name} procesado con éxito.",
                fg=typer.colors.GREEN,
            )
            print_rich_table(
                banco_invico.clean_df, title=f"Datos del archivo: {file.name}"
            )
    except Exception as e:
        typer.secho(
            f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
        )


# --------------------------------------------------
if __name__ == "__main__":
    app()

    # From /invico_streamlit

    # poetry run python -m src.automation.sscc.banco_invico -d
    # poetry run python -m src.automation.sscc.banco_invico -f "D:\Datos INVICO\R Gestion INVICO\invico_streamlit\src\automation\sscc\2026-bancoINVICO.csv"

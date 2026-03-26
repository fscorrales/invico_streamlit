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
from pywinauto import findwindows, keyboard, mouse

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
                ).wait("exists")

                int_ejercicio = int(ejercicio)
                if int_ejercicio > 2010 and int_ejercicio <= dt.datetime.now().year:
                    # Fecha Desde
                    ## Click on año desde
                    time.sleep(1)
                    mouse.click(coords=(495, 205))
                    keyboard.send_keys(ejercicio)
                    ## Click on mes desde
                    time.sleep(1)
                    mouse.click(coords=(470, 205))
                    keyboard.send_keys("01")
                    ## Click on día desde
                    time.sleep(1)
                    mouse.click(coords=(455, 205))
                    keyboard.send_keys("01")

                    # Fecha Hasta
                    fecha_hasta = dt.datetime(year=(int_ejercicio), month=12, day=31)
                    fecha_hasta = min(fecha_hasta, dt.datetime.now())
                    fecha_hasta = dt.datetime.strftime(fecha_hasta, "%d/%m/%Y")
                    ## Click on año hasta
                    time.sleep(1)
                    mouse.click(coords=(610, 205))
                    keyboard.send_keys(ejercicio)
                    ## Click on mes hasta
                    time.sleep(1)
                    mouse.click(coords=(590, 205))
                    keyboard.send_keys(fecha_hasta[3:5])
                    ## Click on día hasta
                    time.sleep(1)
                    mouse.click(coords=(575, 205))
                    keyboard.send_keys(fecha_hasta[0:2])

                    # Actualizar
                    time.sleep(1)
                    keyboard.send_keys("{F5}")
                    vertical_scroll = self.sscc.main.child_window(
                        title="Vertical",
                        auto_id="NonClientVerticalScrollBar",
                        control_type="ScrollBar",
                        found_index=0,
                    ).wait("exists enabled visible ready", timeout=120)

                    # Exportar
                    keyboard.send_keys("{F7}")
                    btn_accept = self.sscc.main.child_window(
                        title="Aceptar", auto_id="9", control_type="Button"
                    ).wait("exists enabled visible ready")
                    btn_accept.click()
                    time.sleep(5)
                    export_dlg_handles = findwindows.find_windows(title="Exportar")
                    if export_dlg_handles:
                        export_dlg = self.sscc.app.window_(handle=export_dlg_handles[0])

                    btn_escritorio = export_dlg.child_window(
                        title="Escritorio", control_type="TreeItem", found_index=1
                    ).wrapper_object()
                    btn_escritorio.click_input()

                    cmb_tipo = export_dlg.child_window(
                        title="Tipo:",
                        auto_id="FileTypeControlHost",
                        control_type="ComboBox",
                    ).wrapper_object()
                    cmb_tipo.type_keys("%{DOWN}")
                    cmb_tipo.select("Archivo ASCII separado por comas (*.csv)")

                    cmb_nombre = export_dlg.child_window(
                        title="Nombre:",
                        auto_id="FileNameControlHost",
                        control_type="ComboBox",
                    ).wrapper_object()
                    cmb_nombre.click_input()
                    report_name = (
                        str(ejercicio)
                        + " - Bancos - Consulta General de Movimientos.csv"
                    )
                    cmb_nombre.type_keys(report_name, with_spaces=True)
                    btn_guardar = export_dlg.child_window(
                        title="Guardar", auto_id="1", control_type="Button"
                    ).wrapper_object()
                    btn_guardar.click()

                    # self.sscc.main.wait("active", timeout=120)

                    dlg_consulta_gral_mov = self.sscc.main.child_window(
                        title="Consulta General de Movimientos", control_type="Window"
                    ).wait("active", timeout=60)

                    # Cerrar ventana
                    keyboard.send_keys("{F10}")

                    # Move file to destination
                    time.sleep(2)
                    self.move_report(dir_path, report_name)

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
                    filename = (
                        str(ejercicio)
                        + " - Bancos - Consulta General de Movimientos.csv"
                    )
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

    # poetry run python -m src.automation.siif.rvicon03 -d
    # poetry run python -m src.automation.siif.rvicon03 -f "D:\Proyectos IT\invico_streamlit\src\automation\siif\2026-rvicon03.xls"

#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 29-dic-2025
Purpose: Read, process and write SGV's Informe Evolución de Saldos por Barrios report
"""

__all__ = ["SaldosBarriosEvolucion"]

import argparse
import asyncio
import datetime as dt
import inspect
import os
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from playwright.async_api import Download, async_playwright

from src.automation.sgv.connect_sgv import (
    ReportCategory,
    SGVReportManager,
    login,
)
from src.utils.print_tables import print_rich_table


# --------------------------------------------------
def get_args():
    """Get command-line arguments"""

    parser = argparse.ArgumentParser(
        description="Read, process and write SGV's Informe Evolución de Saldos por Barrios report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-u",
        "--username",
        help="Username for SGV access",
        metavar="username",
        type=str,
        default=None,
    )

    parser.add_argument(
        "-p",
        "--password",
        help="Password for SGV access",
        metavar="password",
        type=str,
        default=None,
    )

    parser.add_argument(
        "-e",
        "--ejercicios",
        metavar="ejercicios",
        default=[dt.datetime.now().year],
        type=int,
        choices=range(2010, dt.datetime.now().year + 1),
        nargs="+",
        help="Ejercicios to download from SGV",
    )

    parser.add_argument(
        "-d", "--download", help="Download report from SGV", action="store_true"
    )

    parser.add_argument(
        "--headless", help="Run browser in headless mode", action="store_true"
    )

    parser.add_argument(
        "-f",
        "--file",
        metavar="xls_file",
        default=None,
        type=argparse.FileType("r"),
        help="SGV' Informe Evolución de Saldos por Barrios.xls report. Must be in the same folder",
    )

    args = parser.parse_args()

    if args.username is None or args.password is None:
        from ...config import settings

        args.username = settings.SGV_USERNAME
        args.password = settings.SGV_PASSWORD
        if args.username is None or args.password is None:
            parser.error("Both --username and --password are required.")

    if args.file and args.download:
        parser.error("You cannot use --file and --download together. Choose one.")

    return args


# --------------------------------------------------
class SaldosBarriosEvolucion(SGVReportManager):
    # --------------------------------------------------
    async def download_and_process_report(
        self, ejercicio: int = dt.datetime.now().year, mes: int = 12
    ) -> pd.DataFrame:
        """Download and process the rf602 report for a specific year."""
        try:
            await self.go_to_specific_report()
            self.download = await self.download_report(
                ejercicio=str(ejercicio), mes=str(mes)
            )
            if self.download is None:
                raise ValueError("No se pudo descargar el reporte rf602.")
            await self.read_xls_file()
            return await self.process_dataframe()
        except Exception as e:
            print(f"Error al descargar y procesar el reporte: {e}")

    # --------------------------------------------------
    async def go_to_specific_report(self) -> None:
        await self.go_to_report(report=ReportCategory.SaldosBarriosEvolucion)
        # await self.select_report_module(module=ReportCategory.Gastos)
        # await self.select_specific_report_by_id(report_id="38")

    # --------------------------------------------------
    async def download_report(
        self, ejercicio: str = str(dt.datetime.now().year), mes: str = "12"
    ) -> Download:
        try:
            self.download = None
            # Getting DOM elements
            (
                input_ejercicio,
                input_mes,
            ) = await self.sgv.reports_page.locator(
                "//table[@class='tablaFiltros']//input"
            ).all()
            # input_ejercicio = self.sgv.reports_page.locator(
            #     "//input[@id='ctl00_ContentPlacePrincipal_ucInformeEvolucionDeSaldosPorBarrio_txtAño_TextBox1']"
            # )

            await input_mes.clear()
            await input_mes.fill(str(mes))
            await input_ejercicio.clear()
            await input_ejercicio.fill(str(ejercicio))
            await input_ejercicio.press("Enter")

            await self.sgv.reports_page.wait_for_load_state("networkidle")
            btn_export = self.sgv.reports_page.locator(
                "//a[@id='ctl00_ContentPlacePrincipal_ucInformeEvolucionDeSaldosPorBarrio_rpInformeEvoSaldosPorBarrio_ctl05_ctl04_ctl00_ButtonLink']"
            )
            await btn_export.click()

            await self.sgv.reports_page.wait_for_load_state("networkidle")
            btn_to_excel = self.sgv.reports_page.locator("//a[@title='Excel']")
            async with self.sgv.context.expect_page() as popup_info:
                async with self.sgv.reports_page.expect_download() as download_info:
                    await btn_to_excel.click()  # Se abre el popup aquí

            popup_page = await popup_info.value  # Obtener la ventana emergente
            self.download = await download_info.value  # Obtener el archivo descargado

            # Cerrar la ventana emergente (si realmente se abrió)
            if popup_page:
                await popup_page.close()

            # await self.go_back_to_reports_list()

            return self.download

        except Exception as e:
            print(f"Error al descargar el reporte: {e}")
            # await self.logout()

    # --------------------------------------------------
    async def process_dataframe(self, dataframe: pd.DataFrame = None) -> pd.DataFrame:
        """ "Transform read xls file"""
        if dataframe is None:
            df = self.df.copy()
        else:
            df = dataframe.copy()

        df["ejercicio"] = pd.to_numeric(df.iloc[1, 0][-5:][0:4], errors="coerce")
        df = df.iloc[6:-1, [0, 1, 2, 3, 4, 6, 7]]
        df.rename(
            {
                "0": "cod_barrio",
                "1": "barrio",
                "2": "saldo_inicial",
                "3": "amortizacion",
                "4": "cambios",
                "6": "saldo_final",
            },
            axis="columns",
            inplace=True,
        )
        df["cod_barrio"] = df["cod_barrio"].astype(str)
        cols = ["saldo_inicial", "amortizacion", "cambios", "saldo_final"]
        for col in cols:
            df[col] = df[col].astype(float)
        df["amortizacion"] = df["amortizacion"] * (-1)
        cols = df.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df = df[cols]

        self.clean_df = df
        return self.clean_df


# ──────────────────────────────────────────────
# Inicialización de Typer
# ──────────────────────────────────────────────

app = typer.Typer(
    help="Read, process and write SGV's Informe Evolución de Saldos por Barrios report",
    add_completion=False,
)


# --------------------------------------------------
@app.command()
def main(
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="Username for SGV access"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p", help="Password for SGV access"
    ),
    ejercicios: List[int] = typer.Option(
        [dt.datetime.now().year],
        "--ejercicios",
        "-e",
        help="Ejercicios to download from SGV",
    ),
    download: bool = typer.Option(
        False, "--download", "-d", help="Download report from SGV"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run browser in headless mode"
    ),
    file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="SGV' Informe Evolución de Saldos por Barrios.xls report. Must be in the same folder",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """
    Read, process and write SGV's Informe Evolución de Saldos por Barrios report.
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
        if ejercicio not in list(range(2010, dt.datetime.now().year + 1)):
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

            username = username or settings.SGV_USERNAME
            password = password or settings.SGV_PASSWORD
        except ImportError:
            pass

        if not username or not password:
            typer.secho(
                "❌ Error: Se requieren credenciales (vía argumentos o config).",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    # 3. Ejecución de la lógica asíncrona
    asyncio.run(
        run_automation(username, password, ejercicios, download, headless, file)
    )


# --------------------------------------------------
async def run_automation(username, password, ejercicios, download, headless, file):
    """
    Lógica de ejecución asíncrona de Playwright.
    """
    # Determinamos la ruta de guardado
    save_path = os.path.dirname(
        os.path.abspath(inspect.getfile(inspect.currentframe()))
    )

    async with async_playwright() as p:
        try:
            if download:
                typer.echo("⏳ Descargando reporte SGV Saldos Barrios Evolución...")

                # 1. Login
                connect_sgv = await login(
                    username, password, playwright=p, headless=headless
                )

                # 2. Navegación inicial
                sgv = SaldosBarriosEvolucion(sgv=connect_sgv)
                await sgv.go_to_specific_report()

                # 3. Bucle de ejercicios
                for ejercicio in ejercicios:
                    typer.echo(f"⏳ Procesando ejercicio: {ejercicio}...")
                    # Descarga y guardado físico
                    await sgv.download_report(ejercicio=str(ejercicio))
                    await sgv.save_xls_file(
                        save_path=save_path,
                        file_name=str(ejercicio)
                        + "-InformeEvolucionDeSaldosPorBarrio.xls",
                    )
                    # Feedback visual de éxito
                    typer.secho(
                        f"✅ Ejercicio {ejercicio} descargado con éxito.",
                        fg=typer.colors.GREEN,
                    )

                    # 4. Lectura y Procesamiento
                    await sgv.read_xls_file()
                    # print(siif.df)
                    await sgv.process_dataframe()
                    # Feedback visual de éxito
                    typer.secho(
                        f"✅ Ejercicio {ejercicio} procesado con éxito.",
                        fg=typer.colors.GREEN,
                    )
                    print_rich_table(
                        sgv.clean_df, title=f"Resultados Ejercicio {ejercicio}"
                    )

                # 5. Logout
                await sgv.logout()

            else:
                sgv = SaldosBarriosEvolucion()
                # 1. Lectura y Procesamiento
                typer.echo(f"⏳ Procesando archivo: {file.name}...")
                await sgv.read_xls_file(file)
                await sgv.process_dataframe()
                typer.secho(
                    f"✅ Archivo {file.name} procesado con éxito.",
                    fg=typer.colors.GREEN,
                )
                print_rich_table(sgv.clean_df, title=f"Datos del archivo: {file.name}")

        except Exception as e:
            typer.secho(
                f"💥 Error durante la ejecución: {e}", fg=typer.colors.RED, err=True
            )


# --------------------------------------------------
if __name__ == "__main__":
    app()
    # From /invicofapy

    # poetry run python -m src.automation.sgv.saldos_barrios_evolucion -d -e 2025

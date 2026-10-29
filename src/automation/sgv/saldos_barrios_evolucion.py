#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 29-dic-2025
Purpose: Read, process and write SGV's Informe Evolución de Saldos por Barrios report
"""

__all__ = ["SaldosBarriosEvolucion"]

import asyncio
import datetime as dt
import inspect
import os
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
from playwright.async_api import Download, Page, async_playwright

from src.automation.sgv.connect_sgv import (
    ReportCategory,
    SGVReportManager,
    login,
)
from src.utils.print_tables import print_rich_table

# Timeouts (en segundos) para la captura de la ventana emergente y la descarga
POPUP_TIMEOUT: int = 30
DOWNLOAD_TIMEOUT: int = 120


# --------------------------------------------------
class SaldosBarriosEvolucion(SGVReportManager):
    # --------------------------------------------------
    async def download_and_process_report(
        self, ejercicio: int = dt.datetime.now().year, mes: int = 12
    ) -> pd.DataFrame:
        """Download and process the rf602 report for a specific year."""
        await self.go_to_specific_report()
        self.download = await self.download_report(
            ejercicio=str(ejercicio), mes=str(mes)
        )
        if self.download is None:
            raise ValueError("No se pudo descargar el reporte rf602.")
        await self.read_xls_file()
        return await self.process_dataframe()

    # --------------------------------------------------
    async def go_to_specific_report(self) -> None:
        await self.go_to_report(report=ReportCategory.SaldosBarriosEvolucion)
        # await self.select_report_module(module=ReportCategory.Gastos)
        # await self.select_specific_report_by_id(report_id="38")

    # --------------------------------------------------
    async def download_report(
        self, ejercicio: str = str(dt.datetime.now().year), mes: str = "12"
    ) -> Download:
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

        # Al hacer clic en Excel se abre una ventana nueva y desde allí se
        # dispara la descarga (mecanismo similar a los reportes de SIIF)
        loop = asyncio.get_running_loop()
        popup_future: asyncio.Future[Page] = loop.create_future()
        download_future: asyncio.Future[Download] = loop.create_future()
        popup_pages: List[Page] = []

        def on_download(download: Download) -> None:
            if not download_future.done():
                download_future.set_result(download)

        def on_new_page(page: Page) -> None:
            popup_pages.append(page)
            # Escuchar también a nivel de página por si el popup es el origen
            page.on("download", on_download)
            if not popup_future.done():
                popup_future.set_result(page)

        self.sgv.context.on("page", on_new_page)
        self.sgv.context.on("download", on_download)
        try:
            await btn_to_excel.click()

            # 1. Esperar el primer evento: la ventana emergente o la descarga
            done, _ = await asyncio.wait(
                (popup_future, download_future),
                timeout=POPUP_TIMEOUT,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                raise TimeoutError(
                    "No se abrió ninguna ventana ni se inició la descarga al "
                    "hacer clic en el reporte Excel (SGV)."
                )

            # 2. Si la descarga todavía no llegó, esperarla desde el popup
            if not download_future.done():
                popup_page = popup_future.result()
                await popup_page.wait_for_load_state("domcontentloaded")
                # Si el popup se redirigió al login, lanzamos error explícito
                if "login" in popup_page.url.lower():
                    raise RuntimeError(
                        "La sesión expiró al intentar generar el reporte en SGV."
                    )
                try:
                    self.download = await asyncio.wait_for(
                        download_future, timeout=DOWNLOAD_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        "Se abrió la ventana del reporte pero la descarga no se "
                        f"inició dentro de los {DOWNLOAD_TIMEOUT} segundos."
                    ) from None
            else:
                self.download = download_future.result()

            return self.download
        finally:
            self.sgv.context.remove_listener("page", on_new_page)
            self.sgv.context.remove_listener("download", on_download)
            # Cerrar la ventana emergente (si realmente se abrió)
            for popup_page in popup_pages:
                if not popup_page.is_closed():
                    await popup_page.close()

            # await self.go_back_to_reports_list()

    # --------------------------------------------------
    async def process_dataframe(self, dataframe: pd.DataFrame = None) -> pd.DataFrame:
        """ "Transform read xls file"""
        if dataframe is None:
            if self.df is None:
                raise ValueError(
                    "No se ha leído ningún archivo: 'self.df' es None. "
                    "Ejecutá read_xls_file() antes de process_dataframe()."
                )
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
                    if sgv.download is None:
                        raise ValueError(
                            f"No se pudo descargar el reporte del ejercicio {ejercicio}."
                        )
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
                    df = await sgv.read_xls_file()
                    if df is None:
                        raise ValueError(
                            f"No se pudo leer el archivo del ejercicio {ejercicio}."
                        )
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

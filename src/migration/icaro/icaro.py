#!/usr/bin/env python3
"""
Author : Fernando Corrales <fscpython@gmail.com>
Date   : 20-jun-2025
Purpose: Migrate from old Icaro.sqlite to new DB
"""

__all__ = ["IcaroMongoMigrator"]


import json
import os
import sqlite3
from pathlib import Path

import pandas as pd
import typer

from ...constants.endpoints import Endpoints
from ...utils import get_df_from_sql_table, print_rich_table
from ..migration_client import MigrationClient


# --------------------------------------------------
def validate_sqlite_file(value: Path):
    if value is None:
        return value

    # Convertimos a string y normalizamos barras
    path_str = os.path.normpath(str(value))

    # Si detectamos que es una ruta de red pero le falta una barra inicial (común en Typer/Click)
    if path_str.startswith("\\") and not path_str.startswith("\\\\"):
        path_str = "\\" + path_str

    # Creamos un nuevo objeto Path con la ruta corregida
    fixed_path = Path(path_str)

    if not fixed_path.exists():
        raise typer.BadParameter(
            f"No se pudo encontrar el archivo en la red: '{path_str}'.\n"
            "Tip: Intenta poner la ruta entre comillas dobles en la terminal."
        )

    # Validar integridad SQLite (usando la ruta corregida)
    try:
        conn = sqlite3.connect(f"file:{fixed_path}?mode=ro", uri=True)
        conn.execute("PRAGMA schema_version;")
        conn.close()
    except Exception as e:
        raise typer.BadParameter(f"Error de base de datos: {e}")

    return fixed_path

    # # 1. Validar extensión (opcional pero recomendado)
    # # Comúnmente .db, .sqlite, .sqlite3
    # valid_extensions = [".db", ".sqlite", ".sqlite3"]
    # if value and value.suffix.lower() not in valid_extensions:
    #     # Solo lanzamos advertencia o error si quieres ser estricto con la extensión
    #     # Si prefieres ser flexible, puedes comentar este bloque if.
    #     raise typer.BadParameter(
    #         f"El archivo '{value}' no tiene una extensión de SQLite válida {valid_extensions}"
    #     )

    # # 2. Validar integridad de la base de datos
    # try:
    #     # Intentamos abrir la conexión
    #     # uri=True ayuda si el path tiene caracteres especiales
    #     conn = sqlite3.connect(f"file:{value}?mode=ro", uri=True)
    #     cursor = conn.cursor()

    #     # Ejecutamos un PRAGMA rápido para verificar que el encabezado es correcto
    #     # y que realmente es un archivo de base de datos SQLite.
    #     cursor.execute("PRAGMA schema_version;")
    #     cursor.fetchone()

    #     conn.close()
    # except sqlite3.DatabaseError as e:
    #     raise typer.BadParameter(
    #         f"El archivo no es una base de datos SQLite válida o está corrupto: {e}"
    #     )
    # except Exception as e:
    #     raise typer.BadParameter(f"Error inesperado al validar SQLite: {e}")

    # return value


# --------------------------------------------------
class IcaroMongoMigrator:
    # --------------------------------------------------
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path

    # --------------------------------------------------
    def migrate_df_to_mongodb(
        self, table: str, endpoint: str, df: pd.DataFrame
    ) -> None:
        """Migrate DataFrame to MongoDB."""
        client = MigrationClient(token="token_bypassed")
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

    # # --------------------------------------------------
    # async def migrate_programas(self) -> RouteReturnSchema:
    #     df = self.from_sql("PROGRAMAS")
    #     df.rename(
    #         columns={"Programa": "programa", "DescProg": "desc_programa"}, inplace=True
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=ProgramasReport, field_id="programa"
    #     )
    #     # await self.programas_repo.delete_all()
    #     # await self.programas_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.programas_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Programas Migration",
    #         logger=logger,
    #         label="Tabla Programas de ICARO",
    #     )

    # # --------------------------------------------------
    # async def migrate_subprogramas(self) -> RouteReturnSchema:
    #     df = self.from_sql("SUBPROGRAMAS")
    #     df.rename(
    #         columns={
    #             "Programa": "programa",
    #             "Subprograma": "subprograma",
    #             "DescSubprog": "desc_subprograma",
    #         },
    #         inplace=True,
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=SubprogramasReport, field_id="subprograma"
    #     )
    #     # await self.subprogramas_repo.delete_all()
    #     # await self.subprogramas_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.subprogramas_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Subprogramas Migration",
    #         logger=logger,
    #         label="Tabla Subprogramas de ICARO",
    #     )

    # # --------------------------------------------------
    # async def migrate_proyectos(self) -> RouteReturnSchema:
    #     df = self.from_sql("PROYECTOS")
    #     df.rename(
    #         columns={
    #             "Subprograma": "subprograma",
    #             "Proyecto": "proyecto",
    #             "DescProy": "desc_proyecto",
    #         },
    #         inplace=True,
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=ProyectosReport, field_id="proyecto"
    #     )
    #     # await self.proyectos_repo.delete_all()
    #     # await self.proyectos_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.proyectos_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Proyectos Migration",
    #         logger=logger,
    #         label="Tabla Proyectos de ICARO",
    #     )

    # # --------------------------------------------------
    # async def migrate_actividades(self) -> RouteReturnSchema:
    #     df = self.from_sql("ACTIVIDADES")
    #     df.rename(
    #         columns={
    #             "Proyecto": "proyecto",
    #             "Actividad": "actividad",
    #             "DescAct": "desc_actividad",
    #         },
    #         inplace=True,
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=ActividadesReport, field_id="actividad"
    #     )
    #     # await self.actividades_repo.delete_all()
    #     # await self.actividades_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.actividades_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Actividades Migration",
    #         logger=logger,
    #         label="Tabla Actividades de ICARO",
    #     )

    # --------------------------------------------------
    def migrate_estructuras(self):
        """Migrate ESTRUCTURAS table to MongoDB."""

        # Programas
        table = "PROGRAMAS"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={"Programa": "estructura", "DescProg": "desc_estructura"},
            inplace=True,
        )

        # Subprogramas
        table = "SUBPROGRAMAS"
        df_aux = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df_aux.rename(
            columns={
                "Subprograma": "estructura",
                "DescSubprog": "desc_estructura",
            },
            inplace=True,
        )
        df_aux.drop(["Programa"], axis=1, inplace=True)
        df = pd.concat([df, df_aux], ignore_index=True)

        # Proyectos
        table = "PROYECTOS"
        df_aux = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df_aux.rename(
            columns={
                "Proyecto": "estructura",
                "DescProy": "desc_estructura",
            },
            inplace=True,
        )
        df_aux.drop(["Subprograma"], axis=1, inplace=True)
        df = pd.concat([df, df_aux], ignore_index=True)
        # await self.estructuras_repo.save_all(df.to_dict(orient="records"))

        # Actividades
        table = "ACTIVIDADES"
        df_aux = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df_aux.rename(
            columns={
                "Actividad": "estructura",
                "DescAct": "desc_estructura",
            },
            inplace=True,
        )
        df_aux.drop(["Proyecto"], axis=1, inplace=True)
        df = pd.concat([df, df_aux], ignore_index=True)

        table = "ESTRUCTURAS"
        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_ESTRUCTURAS.value, df=df
        )

    # --------------------------------------------------
    def migrate_ctas_ctes(self):
        """Migrate CUENTASBANCARIAS table to MongoDB."""
        table = "CUENTASBANCARIAS"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "CuentaAnterior": "cta_cte_anterior",
                "Cuenta": "cta_cte",
                "Descripcion": "desc_cta_cte",
                "Banco": "banco",
            },
            inplace=True,
        )

        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_CTAS_CTES.value, df=df
        )

    # # --------------------------------------------------
    # async def migrate_fuentes(self) -> RouteReturnSchema:
    #     df = self.from_sql("FUENTES")
    #     df.rename(
    #         columns={
    #             "Fuente": "fuente",
    #             "Descripcion": "desc_fuente",
    #             "Abreviatura": "abreviatura",
    #         },
    #         inplace=True,
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=FuentesReport, field_id="fuente"
    #     )
    #     # await self.fuentes_repo.delete_all()
    #     # await self.fuentes_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.fuentes_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Fuentes Migration",
    #         logger=logger,
    #         label="Tabla Fuentes de ICARO",
    #     )

    # # --------------------------------------------------
    # async def migrate_partidas(self) -> RouteReturnSchema:
    #     df = self.from_sql("PARTIDAS")
    #     df.rename(
    #         columns={
    #             "Grupo": "grupo",
    #             "DescGrupo": "desc_grupo",
    #             "PartidaParcial": "partida_parcial",
    #             "DescPartidaParcial": "desc_partida_parcial",
    #             "Partida": "partida",
    #             "DescPartida": "desc_partida",
    #         },
    #         inplace=True,
    #     )

    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=PartidasReport, field_id="partida"
    #     )
    #     # await self.partidas_repo.delete_all()
    #     # await self.partidas_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.partidas_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Partidas Migration",
    #         logger=logger,
    #         label="Tabla Partidas de ICARO",
    #     )

    # # --------------------------------------------------
    # async def migrate_proveedores(self) -> RouteReturnSchema:
    #     df = self.from_sql("PROVEEDORES")
    #     df.rename(
    #         columns={
    #             "Codigo": "codigo",
    #             "Descripcion": "desc_proveedor",
    #             "Domicilio": "domicilio",
    #             "Localidad": "localidad",
    #             "Telefono": "telefono",
    #             "CUIT": "cuit",
    #             "CondicionIVA": "condicion_iva",
    #         },
    #         inplace=True,
    #     )
    #     # Validar datos usando Pydantic
    #     validate_and_errors = validate_and_extract_data_from_df(
    #         dataframe=df, model=ProveedoresReport, field_id="codigo"
    #     )

    #     # await self.proveedores_repo.delete_all()
    #     # await self.proveedores_repo.save_all(df.to_dict(orient="records"))
    #     return await sync_validated_to_repository(
    #         repository=self.proveedores_repo,
    #         validation=validate_and_errors,
    #         delete_filter=None,
    #         title="ICARO Proveedores Migration",
    #         logger=logger,
    #         label="Tabla Proveedores de ICARO",
    #     )

    # --------------------------------------------------
    def migrate_obras(self):
        """Migrate OBRAS table to MongoDB."""
        table = "OBRAS"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "Localidad": "localidad",
                "CUIT": "cuit",
                "Imputacion": "actividad",
                "Partida": "partida",
                "Fuente": "fuente",
                "MontoDeContrato": "monto_contrato",
                "Adicional": "monto_adicional",
                "Cuenta": "cta_cte",
                "NormaLegal": "norma_legal",
                "Descripcion": "desc_obra",
                "InformacionAdicional": "info_adicional",
            },
            inplace=True,
        )

        df = df.loc[
            :,
            [
                "actividad",
                "partida",
                "fuente",
                "desc_obra",
                "cuit",
                "cta_cte",
                "norma_legal",
                "localidad",
                "info_adicional",
                "monto_contrato",
                "monto_adicional",
            ],
        ]

        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_OBRAS.value, df=df
        )

    # --------------------------------------------------
    def migrate_carga(self):
        """Migrate CARGA table to MongoDB."""
        table = "CARGA"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "Fecha": "fecha",
                "Fuente": "fuente",
                "CUIT": "cuit",
                "Importe": "importe",
                "FondoDeReparo": "fondo_reparo",
                "Cuenta": "cta_cte",
                "Avance": "avance",
                "Certificado": "nro_certificado",
                "Comprobante": "nro_comprobante",
                "Obra": "desc_obra",
                "Origen": "origen",
                "Tipo": "tipo",
                "Imputacion": "actividad",
                "Partida": "partida",
            },
            inplace=True,
        )
        df = df.loc[~df.actividad.isnull()]
        df["fecha"] = pd.to_timedelta(df["fecha"], unit="D") + pd.Timestamp(
            "1970-01-01"
        )
        df["id_carga"] = df["nro_comprobante"] + "C"
        df.loc[df["tipo"] == "PA6", "id_carga"] = df["nro_comprobante"] + "F"
        df["ejercicio"] = df["fecha"].dt.year
        df["mes"] = (
            df["fecha"].dt.month.astype(str).str.zfill(2)
            + "/"
            + df["ejercicio"].astype(str)
        )

        df = df.loc[
            :,
            [
                "ejercicio",
                "mes",
                "fecha",
                "id_carga",
                "nro_comprobante",
                "tipo",
                "fuente",
                "actividad",
                "partida",
                "cta_cte",
                "cuit",
                "importe",
                "fondo_reparo",
                "avance",
                "nro_certificado",
                "desc_obra",
                "origen",
            ],
        ]

        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_CARGA.value, df=df
        )

    # --------------------------------------------------
    def migrate_retenciones(self):
        """Migrate RETENCIONES table to MongoDB."""
        table = "RETENCIONES"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "Codigo": "codigo",
                "Importe": "importe",
                "Comprobante": "nro_comprobante",
                "Tipo": "tipo",
            },
            inplace=True,
        )
        df["ejercicio"] = pd.to_numeric(
            "20" + df["nro_comprobante"].str[-2:], errors="coerce"
        )
        df["id_carga"] = df["nro_comprobante"] + "C"
        df.loc[df["tipo"] == "PA6", "id_carga"] = df["nro_comprobante"] + "F"
        df.drop(["nro_comprobante", "tipo"], axis=1, inplace=True)

        df = df.loc[:, ["ejercicio", "id_carga", "codigo", "importe"]]

        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_RETENCIONES.value, df=df
        )

    # --------------------------------------------------
    def migrate_certificados(self):
        """Migrate CERTIFICADOS table to MongoDB."""
        table = "CERTIFICADOS"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "NroComprobanteSIIF": "nro_comprobante",
                "TipoComprobanteSIIF": "tipo",
                "Origen": "origen",
                "Periodo": "ejercicio",
                "Beneficiario": "beneficiario",
                "Obra": "desc_obra",
                "NroCertificado": "nro_certificado",
                "MontoCertificado": "monto_certificado",
                "FondoDeReparo": "fondo_reparo",
                "ImporteBruto": "importe_bruto",
                "IIBB": "iibb",
                "LP": "lp",
                "SUSS": "suss",
                "GCIAS": "gcias",
                "INVICO": "invico",
                "ImporteNeto": "importe_neto",
            },
            inplace=True,
        )
        df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce")
        df["otras_retenciones"] = 0
        df["cod_obra"] = df["desc_obra"].str.split(" ", n=1).str[0]
        df.loc[df["nro_comprobante"] != "", "id_carga"] = df["nro_comprobante"] + "C"
        df.loc[df["tipo"] == "PA6", "id_carga"] = df["nro_comprobante"] + "F"
        df.drop(["nro_comprobante", "tipo"], axis=1, inplace=True)

        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_CERTIFICADOS.value, df=df
        )

    # --------------------------------------------------
    def migrate_resumen_rend_obras(self):
        """Migrate RESUMENRENDOBRAS table to MongoDB."""
        table = "EPAM"
        df = get_df_from_sql_table(sqlite_path=self.sqlite_path, table=table)
        df.rename(
            columns={
                "NroComprobanteSIIF": "nro_comprobante",
                "TipoComprobanteSIIF": "tipo",
                "Origen": "origen",
                "Obra": "desc_obra",
                "Periodo": "ejercicio",
                "Beneficiario": "beneficiario",
                "LibramientoSGF": "nro_libramiento_sgf",
                "FechaPago": "fecha",
                "ImporteBruto": "importe_bruto",
                "IIBB": "iibb",
                "TL": "lp",
                "Sellos": "sellos",
                "SUSS": "suss",
                "GCIAS": "gcias",
                "ImporteNeto": "importe_neto",
            },
            inplace=True,
        )
        df["destino"] = ""
        df["movimiento"] = ""
        df["seguro"] = 0
        df["salud"] = 0
        df["mutual"] = 0
        df["cod_obra"] = df["desc_obra"].str.split("-", n=1).str[0]
        df["fecha"] = pd.to_timedelta(df["fecha"], unit="D") + pd.Timestamp(
            "1970-01-01"
        )
        df["ejercicio"] = df["fecha"].dt.year
        df["mes"] = (
            df["fecha"].dt.month.astype(str).str.zfill(2)
            + "/"
            + df["ejercicio"].astype(str)
        )
        df.loc[df["nro_comprobante"] != "", "id_carga"] = df["nro_comprobante"] + "C"
        df.loc[df["tipo"] == "PA6", "id_carga"] = df["nro_comprobante"] + "F"
        df.drop(["nro_comprobante", "tipo"], axis=1, inplace=True)
        # df["fecha"] = df["fecha"].apply(
        #     lambda x: x.to_pydatetime() if pd.notnull(x) else None
        # )
        df["updated_at"] = pd.Timestamp.now()
        print_rich_table(df, title=f"Tabla Exportada: {table}")

        self.migrate_df_to_mongodb(
            table=table, endpoint=Endpoints.ICARO_RESUMEN_REND_OBRAS.value, df=df
        )

    # --------------------------------------------------
    def migrate_all(self):
        return_schema = []
        # return_schema.append(await self.migrate_programas())
        # return_schema.append(await self.migrate_subprogramas())
        # return_schema.append(await self.migrate_proyectos())
        # return_schema.append(await self.migrate_actividades())
        return_schema.append(self.migrate_estructuras())
        return_schema.append(self.migrate_ctas_ctes())
        # return_schema.append(await self.migrate_fuentes())
        # return_schema.append(await self.migrate_partidas())
        # return_schema.append(await self.migrate_proveedores())
        return_schema.append(self.migrate_obras())
        return_schema.append(self.migrate_carga())
        return_schema.append(self.migrate_retenciones())
        return_schema.append(self.migrate_certificados())
        return_schema.append(self.migrate_resumen_rend_obras())
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
        help="SQLite database file path",
        exists=False,
        file_okay=True,
        dir_okay=False,
        readable=False,
        callback=validate_sqlite_file,
    ),
):
    """
    Lee, procesa y escribe el reporte planillometro_hist de Patricia.
    """
    try:
        migrator = IcaroMongoMigrator(
            sqlite_path=file,
        )
        migrator.migrate_certificados()
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

    # poetry run python -m src.migration.icaro.icaro -f "\\192.168.0.149\Compartida CONTABLE\R Apps (Compartida)\R Output\SQLite Files\ICARO.sqlite"

"""Modelos Pydantic/DTOs compartidos del sistema INVICO.

Capa de datos pura: aquí solo viven definiciones de esquemas (enums de
dominio, DTOs de autenticación, modelos de reportes y respuestas
estandarizadas de la API). Prohibido importar Streamlit, HTTPX, Pywinauto
ni Playwright en esta capa (ver ``AGENTS.md`` §1): los servicios y vistas
importan de este módulo, nunca al revés.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


# -------------------------------------------------
class Role(str, Enum):
    """Roles de usuario reconocidos por el sistema."""

    ADMIN = "admin"
    USER = "user"
    PENDING = "pending"


# -------------------------------------------------
class Origen(str, Enum):
    """Origen de los comprobantes de rendición (SGF)."""

    EPAM = "EPAM"
    OBRAS = "OBRAS"
    FUNCIONAMIENTO = "FUNCIONAMIENTO"


# -------------------------------------------------
class FuenteFinanciamientoSIIF(str, Enum):
    """Fuentes de financiamiento registradas en el SIIF."""

    f_10 = "10"
    f_11 = "11"
    f_12 = "12"
    f_13 = "13"
    f_14 = "14"
    f_15 = "15"


# -------------------------------------------------
class TipoComprobanteSIIF(str, Enum):
    """Tipos de comprobante del SIIF relevantes para el sistema."""

    adelanto_contratista = "PA6"
    anticipo_viatico = "PA3"
    reversion_viatico = "REV"


# -------------------------------------------------
class GrupoPartidaSIIF(int, Enum):
    """Grupos de partidas del SIIF."""

    sueldos = 1
    bienes_consumo = 2
    servicios = 3
    bienes_capital = 4


# ──────────────────────────────────────────────
# Users & Auth
# ──────────────────────────────────────────────


# -------------------------------------------------
class LoginUser(BaseModel):
    """Credenciales de acceso (POST /auth/login)."""

    username: str
    password: str


# -------------------------------------------------
class UserRegistrationForm(BaseModel):
    """Datos de registro de usuario (POST /auth/register)."""

    username: str
    password: str


# -------------------------------------------------
class CreateUser(BaseModel):
    """Alta de usuario desde el panel de administración (POST /users/)."""

    username: str
    password: str
    role: Role = Role.USER


# -------------------------------------------------
class PublicStoredUser(BaseModel):
    """Modelo de usuario devuelto por el backend (/users/me)."""

    id: str
    username: str
    role: Role


# -------------------------------------------------
class UpdateUserRole(BaseModel):
    """Cambio de rol de un usuario (PATCH /users/{id}/role)."""

    role: Role = Role.USER


# -------------------------------------------------
class ExternalCredentialIn(BaseModel):
    """Credencial de un sistema externo asociado al usuario.

    Los campos ``camelCase`` respetan el contrato del backend.
    """

    systemName: str
    externalUsername: str
    externalPassword: str


# ──────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────


# -------------------------------------------------
class BancoINVICOReport(BaseModel):
    ejercicio: int
    mes: str
    fecha: datetime
    cta_cte: str
    movimiento: Optional[str] = None
    es_cheque: bool
    beneficiario: Optional[str] = None
    importe: float
    concepto: Optional[str] = None
    moneda: Optional[str] = None
    libramiento: Optional[str] = None
    cod_imputacion: str
    imputacion: str


# -------------------------------------------------
class ControlRecursosReport(BaseModel):
    ejercicio: int
    mes: str
    cta_cte: str
    grupo: str
    recursos_siif: float
    depositos_banco: float


# -------------------------------------------------
class ResumenRendProvReport(BaseModel):
    origen: Origen
    ejercicio: int
    mes: str
    fecha: datetime
    beneficiario: str
    destino: str
    libramiento_sgf: str
    movimiento: str
    cta_cte: str
    importe_bruto: float
    gcias: float
    sellos: float
    iibb: float
    suss: float
    invico: float
    seguro: float
    salud: float
    mutual: float
    otras: float
    retenciones: float
    importe_neto: float


# -------------------------------------------------
class Rf602Report(BaseModel):
    ejercicio: int
    estructura: str
    fuente: FuenteFinanciamientoSIIF
    programa: str
    subprograma: str
    proyecto: str
    actividad: str
    grupo: str
    partida: str
    org: str
    credito_original: float
    credito_vigente: float
    comprometido: float
    ordenado: float
    saldo: float
    pendiente: float


# -------------------------------------------------
class Rf610Report(BaseModel):
    ejercicio: int
    estructura: str
    programa: str
    desc_programa: Optional[str] = None
    subprograma: str
    desc_subprograma: Optional[str] = None
    proyecto: str
    desc_proyecto: Optional[str] = None
    actividad: str
    desc_actividad: Optional[str] = None
    grupo: str
    desc_grupo: str
    partida: str
    desc_partida: str
    credito_original: float
    credito_vigente: float
    comprometido: float
    ordenado: float
    saldo: float


# -------------------------------------------------
# Reportes del Planillometro (SGV)
# -------------------------------------------------
class ObrasRecuperadasReport(BaseModel):
    ejercicio: int
    cod_barrio: str
    estructura: str
    importe: float
    notas: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# -------------------------------------------------
class ObrasDesactivadasReport(BaseModel):
    ejercicio: int
    cta_contable: str
    estructura: str
    importe: float
    notas: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# -------------------------------------------------
class SaldosBarriosEvolucionReport(BaseModel):
    ejercicio: int
    cod_barrio: str
    barrio: str
    saldo_inicial: float
    amortizacion: float
    cambios: float
    saldo_final: float

# -------------------------------------------------
class ReportePlanillometroReport(BaseModel):
    desc_programa: Optional[str] = None
    desc_subprograma: Optional[str] = None
    desc_proyecto: Optional[str] = None
    desc_actividad: Optional[str] = None
    estructura: Optional[str] = None
    partida: Optional[str] = None
    desc_obra: Optional[str] = None
    fuente: Optional[str] = None
    alta: str
    ejercicio: int
    ejecucion: float
    acum: float
    en_curso: float
    terminadas_ant: float
    terminadas_actual: float


# ──────────────────────────────────────────────
# API Route Responses
# ──────────────────────────────────────────────


# -------------------------------------------------
class ErrorsDetails(BaseModel):
    loc: str
    msg: str
    error_type: str


# -------------------------------------------------
class ErrorsWithDocId(BaseModel):
    doc_id: str
    details: List[ErrorsDetails]


# -------------------------------------------------
class RouteReturnSchema(BaseModel):
    title: Optional[str] = None
    deleted: int = 0
    added: int = 0
    errors: List[ErrorsWithDocId] = []


# -------------------------------------------------
class ValidationError(BaseModel):
    """Error de validación de un documento (formato FastAPI/Pydantic).

    No confundir con ``src.utils.exceptions.ValidationError``, que es la
    excepción de la aplicación.
    """

    loc: List[Any]
    msg: str
    type: str


# -------------------------------------------------
class HTTPValidationError(BaseModel):
    detail: Optional[List[ValidationError]] = None
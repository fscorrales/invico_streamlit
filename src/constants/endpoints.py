from enum import Enum


# -------------------------------------------------
class Endpoints(str, Enum):
    SIIF_RF602 = "/siif/rf602/"
    SIIF_RF610 = "/siif/rf610/"
    USERS = "/users/"
    CONTROL_RECURSOS = "/control/controlRecursos/"
    SGF_RESUMEN_REND_PROV = "/sgf/resumenRendProv/"
    SSCC_BANCO_INVICO = "/sscc/bancoINVICO/"

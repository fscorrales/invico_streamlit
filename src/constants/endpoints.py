from enum import Enum


# -------------------------------------------------
class Endpoints(str, Enum):
    SIIF = "/siif"
    SIIF_RCI02 = "/siif/rci02"
    SIIF_RF602 = "/siif/rf602"
    SIIF_RF610 = "/siif/rf610"
    SIIF_RCG01_UEJP = "/siif/rcg01Uejp"
    SIIF_RPA03G = "/siif/rpa03g"
    SIIF_RFONDO07TP = "/siif/rfondo07tp"
    SIIF_RFONDOS04 = "/siif/rfondos04"
    SIIF_RFP_P605B = "/siif/rfpP605b"
    USERS = "/users"
    CONTROL_RECURSOS = "/control/controlRecursos"
    SGF_RESUMEN_REND_PROV = "/sgf/resumenRendProv"
    SSCC_BANCO_INVICO = "/sscc/bancoINVICO"
    CTAS_CTES = "/sscc/ctasCtes"
    ICARO_CARGA = "/icaro/carga"

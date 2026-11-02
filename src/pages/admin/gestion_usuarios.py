"""Página: Gestión de Usuarios (solo admin).

Permite listar usuarios con sus roles múltiples, aprobar registros
pendientes, agregar/quitar roles y eliminar usuarios mediante las APIs:

- ``GET /users/`` (listado completo).
- ``PATCH /users/{id}/approve`` (quita ``pending`` y otorga ``user``).
- ``PATCH /users/{id}/role`` (reemplaza la lista completa de roles).
- ``DELETE /users/delete_hard/{id}`` (baja permanente del usuario).
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.components.buttons import button_cancel, button_submit
from src.constants.endpoints import Endpoints
from src.models.schemas import Role
from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    delete_request,
    fetch_dataframe,
    patch_request,
)

ENDPOINT = Endpoints.USERS.value
FLASH_KEY = "gestion_usuarios_flash"
ROLE_OPTIONS: list[str] = [role.value for role in Role]


# --------------------------------------------------
def _as_roles(value: Any) -> list[str]:
    """Normaliza la columna ``roles`` a una lista de strings.

    Args:
        value: Valor crudo de la celda (lista, string o nulo).

    Returns:
        Lista de roles como strings (vacía si no hay valor utilizable).
    """
    if isinstance(value, list):
        return [str(role) for role in value]
    if isinstance(value, str) and value:
        return [value]
    return []


# --------------------------------------------------
def _roles_a_texto(roles: list[str]) -> str:
    """Une los roles en una cadena legible para tablas y captions."""
    return ", ".join(roles) if roles else "-"


# --------------------------------------------------
def _roles_de(df: pd.DataFrame, user_id: Any) -> list[str]:
    """Retorna los roles del usuario ``user_id`` dentro del DataFrame."""
    roles = df.loc[df["id"] == user_id, "roles"].iloc[0]
    return _as_roles(roles)


# --------------------------------------------------
def _username_de(df: pd.DataFrame, user_id: Any) -> str:
    """Retorna el username del usuario ``user_id`` dentro del DataFrame."""
    return str(df.loc[df["id"] == user_id, "username"].iloc[0])


# --------------------------------------------------
def _format_user(user_id: Any, df: pd.DataFrame) -> str:
    """Etiqueta ``username (roles)`` para los ``selectbox`` de usuarios."""
    return f"{_username_de(df, user_id)} ({_roles_a_texto(_roles_de(df, user_id))})"


# --------------------------------------------------
def _guardar_flash(message: str, icon: str = "✅") -> None:
    """Deja un mensaje persistente que se mostrará tras el próximo rerun."""
    st.session_state[FLASH_KEY] = {"message": message, "icon": icon}


# --------------------------------------------------
def _mostrar_flash() -> None:
    """Muestra y limpia el mensaje pendiente guardado por ``_guardar_flash``."""
    flash = st.session_state.pop(FLASH_KEY, None)
    if flash:
        st.success(f"{flash['icon']} {flash['message']}")


# --------------------------------------------------
def _aprobar_usuario(user_id: Any) -> None:
    """Aprueba un usuario pendiente (``PATCH /users/{id}/approve``)."""
    try:
        patch_request(f"{ENDPOINT}/{user_id}/approve")
        _guardar_flash("Usuario aprobado exitosamente. Ya puede acceder con su rol.")
        st.rerun()
    except (APIConnectionError, APIResponseError) as e:
        st.error(f"Error al aprobar: {e}")


# --------------------------------------------------
def _actualizar_roles(user_id: Any, nuevos_roles: list[str]) -> None:
    """Reemplaza los roles de un usuario (``PATCH /users/{id}/role``).

    Args:
        user_id: Identificador del usuario a actualizar.
        nuevos_roles: Lista completa y definitiva de roles del usuario.
    """
    try:
        patch_request(
            f"{ENDPOINT}/{user_id}/role",
            json_body={"roles": nuevos_roles},
        )
        _guardar_flash(f"Roles actualizados: {_roles_a_texto(nuevos_roles)}.")
        st.rerun()
    except (APIConnectionError, APIResponseError) as e:
        st.error(f"Error al cambiar roles: {e}")


# --------------------------------------------------
def _limpiar_filtros_roles() -> None:
    """Resetea los multiselect de roles al cambiar de usuario seleccionado."""
    st.session_state.pop("roles_a_agregar", None)
    st.session_state.pop("roles_a_quitar", None)


# --------------------------------------------------
@st.dialog("Confirmar Eliminación PERMANENTE", width="small")
def _modal_eliminar_usuario(user_id: Any, username: str) -> None:
    """Modal de confirmación para eliminar un usuario de forma permanente.

    Ejecuta ``DELETE /users/delete_hard/{id}`` al confirmar. El token se
    lee de ``st.session_state`` y se pasa explícitamente, siguiendo el
    patrón de ``modal_delete_registro_gral`` (``src/views/modals.py``).

    Args:
        user_id: Identificador del usuario a eliminar.
        username: Nombre de usuario (para la advertencia visual).
    """
    token = st.session_state.get("token")

    st.warning(f"⚠️ ¿Estás seguro de que deseás eliminar al usuario **{username}**?")
    st.write("Esta acción es permanente y revocará de inmediato su acceso al sistema.")

    st.markdown("---")
    with st.container(horizontal=True, horizontal_alignment="center", gap="large"):
        if button_cancel("Cancelar", key="user_delete_cancel"):
            st.rerun()

        if button_submit("Sí, Eliminar", key="user_delete_confirm"):
            with st.spinner("Eliminando usuario..."):
                try:
                    delete_request(f"{ENDPOINT}/delete_hard/{user_id}", token=token)
                    _guardar_flash(
                        f"Usuario '{username}' eliminado correctamente.",
                        icon="🗑️",
                    )
                    st.rerun()
                except (APIConnectionError, APIResponseError) as e:
                    st.error(f"Error al eliminar: {e}")


# st.sidebar.header("Gestión de Usuarios")
st.markdown("# Administración de Usuarios")
st.write(
    "Panel de administración para gestionar usuarios del "
    "sistema. Permite aprobar registros pendientes, administrar "
    "sus múltiples roles y eliminar usuarios."
)

_mostrar_flash()

# --- Carga de usuarios ---
try:
    with st.spinner("Cargando lista de usuarios..."):
        df = fetch_dataframe(ENDPOINT, params={"limit": None})

    if df.empty:
        st.info("No se encontraron usuarios.")
        st.stop()

    # Normaliza la columna ``roles`` a listas de strings una sola vez.
    df = df.copy()
    df["roles"] = df["roles"].apply(_as_roles)

    pendientes = df[df["roles"].apply(lambda roles: "pending" in roles)]
    administradores = df[df["roles"].apply(lambda roles: "admin" in roles)]
    user_ids = df["id"].tolist()

    # --- Listado de usuarios ---
    st.write(f"### Usuarios registrados: {len(df)}")

    col_total, col_pend, col_admin = st.columns(3)
    col_total.metric("Total de usuarios", len(df))
    col_pend.metric("Pendientes de aprobación", len(pendientes))
    col_admin.metric("Administradores", len(administradores))

    df_vista = df.copy()
    df_vista["roles"] = df_vista["roles"].apply(_roles_a_texto)
    st.dataframe(df_vista, width="stretch", hide_index=True)

    st.divider()

    # --- Aprobar usuarios pendientes ---
    st.write("### ⏳ Aprobar usuarios pendientes")

    if pendientes.empty:
        st.success("No hay usuarios pendientes de aprobación.")
    else:
        for _, row in pendientes.iterrows():
            with st.container(border=True):
                col_user, col_roles, col_btn = st.columns(
                    [3, 3, 2], vertical_alignment="center"
                )
                col_user.write(f"**{row['username']}**")
                col_roles.caption(
                    "Roles actuales: " + _roles_a_texto(_as_roles(row["roles"]))
                )
                if col_btn.button(
                    "✅ Aprobar",
                    key=f"approve_{row['id']}",
                    width="stretch",
                ):
                    _aprobar_usuario(row["id"])

    st.divider()

    # --- Administra de roles (agregar / quitar) ---
    st.write("### 🔄 Administrar roles")

    user_to_change = st.selectbox(
        "Seleccionar usuario",
        options=user_ids,
        format_func=lambda uid: _format_user(uid, df),
        key="role_change_user",
        on_change=_limpiar_filtros_roles,
    )

    current_roles = _roles_de(df, user_to_change)
    st.caption(f"Roles actuales: {_roles_a_texto(current_roles)}")

    col_agregar, col_quitar = st.columns(2)
    roles_a_agregar = col_agregar.multiselect(
        "Roles a agregar",
        options=[rol for rol in ROLE_OPTIONS if rol not in current_roles],
        key="roles_a_agregar",
    )
    roles_a_quitar = col_quitar.multiselect(
        "Roles a quitar",
        options=current_roles,
        key="roles_a_quitar",
    )

    if st.button("💾 Aplicar cambios", key="btn_aplicar_roles"):
        nuevos_roles = [rol for rol in current_roles if rol not in roles_a_quitar]
        for rol in roles_a_agregar:
            if rol not in nuevos_roles:
                nuevos_roles.append(rol)

        if not nuevos_roles:
            st.warning("Debe mantener al menos un rol activo en el usuario.")
        elif nuevos_roles == current_roles:
            st.info("No se detectaron cambios en los roles.")
        else:
            _actualizar_roles(user_to_change, nuevos_roles)

    st.divider()

    # --- Eliminar usuario ---
    st.write("### 🗑️ Eliminar usuario")

    user_to_delete = st.selectbox(
        "Seleccionar usuario a eliminar",
        options=user_ids,
        format_func=lambda uid: _format_user(uid, df),
        key="delete_user",
    )
    roles_to_delete = _roles_de(df, user_to_delete)
    username_to_delete = _username_de(df, user_to_delete)

    current_username = (st.session_state.get("user") or {}).get("username")
    es_mismo_usuario = username_to_delete == current_username
    es_unico_admin = "admin" in roles_to_delete and len(administradores) == 1

    if es_mismo_usuario:
        st.warning("No podés eliminar tu propio usuario.")
    elif es_unico_admin:
        st.warning(
            "No se puede eliminar al único administrador del sistema. "
            "Asigná el rol admin a otro usuario antes de continuar."
        )
    elif st.button("🗑️ Eliminar usuario", key="btn_eliminar_usuario"):
        _modal_eliminar_usuario(user_to_delete, username_to_delete)

except APIConnectionError as e:
    st.error(f"⚠️ Error de conexión: {e}")
except APIResponseError as e:
    st.error(f"⚠️ Error de API: {e}")

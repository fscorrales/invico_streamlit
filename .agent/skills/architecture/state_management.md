# State Management & JWT

## Session State como Única Fuente de Verdad
Cualquier script o componente debe confiar en `st.session_state` para determinar si el usuario ha iniciado sesión y sus roles.
NUNCA "suponer" que un usuario está logueado localmente sin validar el estado.

## RBAC Structure (Role-Based Access Control)
El estado de la aplicación debe incluir un JWT decodificado o los claims almacenados en:
```python
st.session_state["token"] = jwt_token
st.session_state["user"] = {
    "role": "admin", # admin | user | pending
    "username": "...",
    ...
}
```

- **Sidebar Dinámico:** El sidebar debe renderizarse según el rol. Si el rol es `pending`, mostrar vista bloqueada o mensaje en espera. Si es `admin`, mostrar acceso a "Gestión de usuarios".

## Flujo Recomendado
1. Inicio de App -> Comprobar Token
2. Si no hay token o es inválido -> Renderizar Login
3. Si hay token -> Renderizar Sidebar basado en `st.session_state["user"]["role"]`

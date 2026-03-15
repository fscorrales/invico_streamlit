import httpx

from src.services.models import PublicStoredUser

from ..config import settings

BASE_URL = settings.BASE_URL
DEFAULT_TIMEOUT = 60.0


# --------------------------------------------------
class AuthenticationError(Exception):
    """Custom exception for authentication failures."""

    pass


# --------------------------------------------------
class APIError(Exception):
    """Custom exception for general API errors."""

    pass


# --------------------------------------------------
class APIConnectionError(Exception):
    """Error de conexión con el servidor."""

    pass


# --------------------------------------------------
class APIResponseError(Exception):
    """Error en la respuesta del servidor."""

    pass


def login(username: str, password: str) -> str:
    """
    Autentica al usuario contra el backend y devuelve el token JWT.
    """
    if not username or not password:
        raise ValueError("Usuario y contraseña son requeridos.")

    data = {"username": username, "password": password}

    try:
        response = httpx.post(
            f"{BASE_URL}/auth/login", data=data, timeout=settings.DEFAULT_TIMEOUT
        )

        if not (200 <= response.status_code < 300):
            raise APIResponseError(
                f"Error de API ({response.status_code}): {response.text}"
            )
        if response.status_code == 401 or response.status_code == 404:
            raise AuthenticationError("Credenciales incorrectas")
        # if response.status_code != 200:
        #     raise APIError(f"Error de API: {response.text}")
        if response.status_code == 503:
            raise APIConnectionError(
                "El servidor está despertando. Reintente en unos segundos..."
            )

        # El backend típicamente devuelve {"access_token": "...", "token_type": "bearer"}
        token_data = response.json()
        if "access_token" not in token_data:
            raise APIError("Respuesta de token inválida del servidor.")

        return token_data["access_token"]

    except httpx.RequestError as e:
        raise APIError(f"Error de conexión con el servidor: {str(e)}")


def register(username: str, password: str) -> None:
    """
    Registra un nuevo usuario en el sistema.
    """
    if not username or not password:
        raise ValueError("Usuario y contraseña son requeridos.")

    data = {"username": username, "password": password}

    try:
        response = httpx.post(
            f"{BASE_URL}/auth/register", data=data, timeout=settings.DEFAULT_TIMEOUT
        )

        if response.status_code == 400:
            # Errores comunes: usuario ya existe, contraseña débil, etc.
            raise APIResponseError(f"No se pudo registrar: {response.text}")

        if not (200 <= response.status_code < 300):
            raise APIResponseError(
                f"Error de API ({response.status_code}): {response.text}"
            )

    except httpx.RequestError as e:
        raise APIError(f"Error de conexión con el servidor: {str(e)}")


def get_current_user(token: str) -> PublicStoredUser:
    """
    Obtiene los datos del usuario logueado utilizando el token JWT.
    """
    if not token:
        raise ValueError("Token no proporcionado.")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = httpx.get(f"{BASE_URL}/users/me", headers=headers)

        if response.status_code == 401:
            raise AuthenticationError(
                "Token expirado o inválido. Inicie sesión nuevamente."
            )

        if response.status_code != 200:
            raise APIError(f"Error al obtener usuario: {response.text}")

        # Parse and validate the response against the Pydantic model natively
        return PublicStoredUser(**response.json())

    except httpx.RequestError as e:
        raise APIError(f"Error de conexión con el servidor: {str(e)}")

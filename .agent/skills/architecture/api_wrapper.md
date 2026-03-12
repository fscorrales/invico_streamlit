# API Wrapper

## Conexión a Render (FastAPI)
- **URL Base:** `https://invico-back.onrender.com/`
- **Repositorio:** Utilizar el patrón de Repositorio (ej. `UserRepository`). `st.session_state` interactúa con el repositorio, y el repositorio realiza la llamada a la red.

## Type Hints & Pydantic Models (Programación Defensiva)
1. **Modelos:** Crea modelos Pydantic importables (`src/services/models.py`) que representen las respuestas exactas documentadas en el `/docs` de la API de Render.
2. **Validación:** Recibe el JSON parseado de `httpx` (o `requests`) y pásalo a Pydantic. Si falla la validación, eleva una excepción gestionada tempranamente.

## Early Returns
Evita profundamente el anidamiento de `if`/`else`.
```python
def fetch_data(item_id: int):
    if not item_id:
        raise ValueError("Invalid ID")
    
    response = httpx.get(f"{API_URL}/items/{item_id}")
    if response.status_code != 200:
        raise APIError(response.text)
        
    return ItemModel(**response.json())
```

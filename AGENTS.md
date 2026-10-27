# AGENT RULES: Estándares de Calidad y Arquitectura (Frontend INVICO)

## 1. Separación Estricta de Responsabilidades (SoC)
- **Módulos de Datos (`src/models/schemas.py`):** Pura definición de esquemas Pydantic/DTOs (`RouteReturnSchema`, filtros, etc.). Prohibido importar Streamlit, HTTPX, Pywinauto o Playwright en esta capa.
- **Módulos de Servicio (`src/services/`):** 
  - Contienen la comunicación HTTP mediante `httpx` (`api_client.py`, `auth_service.py`, `data_fetcher.py`).
  - **Permitido:** Se autoriza el uso de `@st.cache_data` / `@st.cache_resource` para optimización de consultas en `src/services/selectors.py` y el manejo/re-elevación de excepciones personalizadas (`APIConnectionError`, `APIResponseError`).
  - **Restricción:** No deben contener widgets interactivos de entrada de datos (`st.button`, `st.text_input`, `st.file_uploader`), los cuales pertenecen a componentes de UI o Vistas.
- **Capa de Vistas y Plantillas (`src/views/`):**
  - La plantilla maestra `report_template` (`src/views/aux_tables.py`) debe orquestar los filtros combinados (`itertools.product`), renderizado de dataframes, exportación a Excel binario (`fetch_excel_stream`) y apertura de modales.
  - No debe acoplarse directamente a la lógica de automatización; debe recibir callbacks (`on_update`) para invocar modales o disparar subprocesos de forma agnóstica.
- **Capa de Automatización (`src/automation/`):**
  - Scripts de escritorio (**pywinauto**) y web (**playwright**) desacoplados.
  - Contiene runners independientes (`banco_invico_runner.py`, `resumen_rend_obras_runner.py`, etc.).

---

## 2. Arquitectura de Automatizaciones (Pywinauto / Playwright)
- **Prohibición Directa:** Ningún bot de escritorio o scraping web pesado debe ejecutarse directamente en el hilo principal de Streamlit para evitar bloqueos del Event Loop o timeouts.
- **Mecanismo Subprocess:** Toda automatización debe ejecutarse mediante `subprocess.Popen` lanzando una consola independiente en Windows (`creationflags=subprocess.CREATE_NEW_CONSOLE`).
- **Compatibilidad con Binario Compilado (`.exe`):**
  - Al crear un nuevo *runner* en `src/automation/`, se debe agregar obligatoriamente a la lista `HIDDEN_IMPORTS` en `compile.py`.
  - La invocación desde el runner debe soportar la detección de binario congelado (`getattr(sys, 'frozen', False)`) y enviar el flag `--automation <modulo_runner>`.

---

## 3. Manejo Riguroso de Errores y Excepciones
- **Prohibido Silenciar Errores:** Queda estrictamente prohibido el uso de bloques `try...except` vacíos o capturas genéricas que oculten excepciones.
- **Flujo de Excepciones HTTPX:**
  1. Capturar errores de red (`httpx.RequestError`, `httpx.HTTPStatusError`) en `src/services/api_client.py` y transformarlos en excepciones claras de la aplicación.
  2. Notificar al usuario final mediante componentes estéticos (`st.error()`, `st.toast()`).
  3. Para exportaciones con `StreamingResponse` de FastAPI, asegurar el flag `follow_redirects=True` en `httpx` para prevenir caídas silenciosas por redirecciones 307 de Koyeb.
- **Resumen de Mutaciones (`RouteReturnSchema`):**
  - Las operaciones `POST` exitosas no deben mostrar nada bajo las tablas o dentro de los modales, solo el toast. Si hay errores, mostrar `st.warning` + métricas + expander de detalles (`doc_id`, `loc`, `msg`) para inconsistencias de Pydantic/MongoDB.

---

## 4. Estilo de Código Python (PEP 8)
- **Formateo:** Cumplimiento estricto de PEP 8. Usar exactamente 4 espacios por nivel de sangría.
- **Nombres:** Usar `snake_case` para variables, funciones y módulos; `CamelCase` para clases y modelos Pydantic; `UPPER_CASE` para constantes y Enums. Evitar nombres ambiguos o de una sola letra.
- **Tipado Estático (Type Hints):** Todas las firmas de funciones y métodos deben incluir *type hints* explícitos.

---

## 5. Control de Cambios y Git (Límites)
- Queda **prohibido** ejecutar comandos autónomos de Git (`git add`, `git commit`, `git push`, `git checkout`) sin la autorización y confirmación explícita del usuario.
# PLAN MAESTRO: Frontend Streamlit INVICO + API Koyeb (Poetry + HTTPX + Subprocess)

## 1. Contexto y Objetivos

Desarrollar y consolidar la interfaz principal de escritorio/web local (**INVICO**) construida sobre Python Streamlit. La aplicación gestiona dependencias mediante Poetry y se empaqueta como un ejecutable autónomo (`.exe`) para Windows vía PyInstaller (`compile.py` / `run.py`).

La aplicación se conecta a la API remota alojada en **Koyeb** (FastAPI + MongoDB Atlas) mediante `httpx`. Su propósito principal es:

* Visualizar y auditar tablas auxiliares del sistema y reportes presupuestarios (SIIF, SSCC, SGF, etc.).


* Orquestar automatizaciones de escritorio (**pywinauto**) y web (**playwright**) desacopladas de la interfaz principal mediante subprocesos independientes.


* Descargar, procesar, cruzar y exportar reportes consolidados (Excel / Google Sheets) con validaciones estructuradas.



---

## 2. Gestión de Entorno y Dependencias (Poetry)

* **Gestor:** Poetry (`pyproject.toml` / `poetry.lock`).


* **Rango de Python soportado:** `">=3.12,<3.15"` (garantiza compatibilidad estricta con PyInstaller).


* **Dependencias principales:**
* `streamlit`

* `httpx`

* `pandas`

* `openpyxl` / `xlsxwriter`

* `pydantic` / `pydantic-settings` / `pydantic-extra-types`

* `python-dotenv`

* `playwright`

* `pywinauto`


* **Dependencias de desarrollo (group `dev`):**
* `pyinstaller`

* `typer`




---

## 3. Arquitectura del Proyecto

```text
invico_streamlit/
├── pyproject.toml                  # Configuración de Poetry (versión, dependencias, rango Python)
├── poetry.lock                     # Lockfile de dependencias
├── run.py                          # Entrypoint lanzador para PyInstaller y ruteador de runners
├── compile.py                      # Script constructor ejecutable (PyInstaller API)
├── app.py                          # Entrypoint principal de Streamlit (Navegación / Shell)
├── icono_invico.ico                # Isologotipo de la aplicación
├── .streamlit/
│   └── config.toml                 # Configuración de tema visual, servidor y UI
└── src/
    ├── .env                        # Variables de entorno (API_BASE_URL, etc.)
    ├── automation/                 # Scripts de automatización desacoplados
    │   ├── sgf/                    # Automatizaciones SGF
    │   │   ├── resumen_rend_obras_runner.py
    │   │   └── resumen_rend_prov_runner.py
    │   ├── sscc/                   # Automatizaciones SSCC
    │   │   ├── banco_invico.py
    │   │   └── banco_invico_runner.py
    │   └── siif/                   # Automatizaciones SIIF (Playwright)
    ├── components/                 # Átomos y moléculas de UI (Widgets reutilizables)
    │   ├── buttons.py              # Botones con estilos/acciones estándar
    │   ├── text_inputs.py         # Inputs de búsqueda/filtros
    │   ├── multiselects.py         # Selectores múltiples parametrizados
    │   └── dataframes.py           # Vistas tabulares configuradas
    ├── config/
    │   └── base_config.py          # Carga de variables de entorno y timeouts
    ├── constants/
    │   ├── endpoints.py            # Enums con los paths de la API en Koyeb
    │   └── options.py              # Listas estáticas/dinámicas para selectores
    ├── migration/                  # Utility scripts para SQLite / MongoDB
    ├── models/                     # Esquemas Pydantic / DTOs
    │   └── schemas.py              # RouteReturnSchema, FilterModels, etc.
    ├── pages/                      # Páginas de la Multipage App
    │   ├── admin.py
    │   ├── controles.py
    │   ├── reportes.py
    │   └── tablas_auxiliares.py
    ├── services/                   # Capa de comunicación HTTP e integración
    │   ├── api_client.py           # Cliente httpx (fetch_dataframe, fetch_excel_stream, post)
    │   ├── auth_service.py         # Manejo de tokens y sesiones
    │   ├── data_fetcher.py         # Orquestación de peticiones complejas / combinaciones
    │   └── selectors.py            # Proveedores de datos cacheados (@st.cache_data)
    ├── utils/
    │   └── handling_path.py        # Mapeo dinámico de rutas relativas y PyInstaller (_MEIPASS)
    └── views/                      # Organismos UI y Modales
        ├── aux_tables.py           # Plantilla maestra reutilizable para vistas tabulares
        └── modals.py               # Diálogos reutilizables para credenciales e inicio de robots

```

---

## 4. Estándares Técnicos y Normas de Desarrollo

### A. Comunicación con API Koyeb (`httpx`)

* Las consultas `GET` a endpoints de reporte deben procesarse sanitizando parámetros y manejando la serialización de filtros `queryFilter`.


* Para descargas de archivos/reportes mediante `StreamingResponse` de FastAPI, se debe utilizar `fetch_excel_stream` activando `follow_redirects=True` (prevención de redirecciones 307 de Koyeb) y capturando los bytes en objetos `BytesIO` para consumirlos con `st.download_button`.


* Los retornos de mutaciones (`POST`) deben seguir la estructura estandarizada `RouteReturnSchema` (`title`, `deleted`, `added`, `errors`) para ser representados en pantalla mediante métricas y expanders de detalles.



### B. Arquitectura de Automatizaciones (Pywinauto / Playwright)

* Ningún bot de escritorio o scraping web debe ejecutarse directamente en el hilo de Streamlit.


* **Mecanismo Subprocess:** Toda automatización debe invocarse mediante `subprocess.Popen` lanzando una nueva consola en Windows (`creationflags=subprocess.CREATE_NEW_CONSOLE`).


* **Compatibilidad con el `.exe` compilado:** El script `run.py` intercepta el flag `--automation` al inicio para ejecutar el módulo objetivo (`importlib.import_module`) mediante su función `run()` y finalizar con `sys.exit(0)` sin levantar el servidor de Streamlit.



### C. Vistas y Componentes Reutilizables

* La vista maestra `report_template` (`src/views/aux_tables.py`) debe orquestar los filtros combinados (`itertools.product`), la renderización de la tabla, los exportadores a Excel y la apertura de modales de actualización inyectados por parámetro.


* Las funciones de selección estáticas o de consulta frecuente deben ubicarse en `src/services/selectors.py` usando el decorador `@st.cache_data(ttl=...)`.



---

## 5. Estrategia de Compilación y Distribución (`compile.py`)

1. **Gestión de Recursos y Configuración:**
* Cargar `.streamlit/config.toml` asegurando la inyección de la variable de entorno `STREAMLIT_CONFIG_DIR` en `run.py` apuntando a `sys._MEIPASS`.


* Pasar los metadatos y código de librerías críticas usando `--collect-all` y `--copy-metadata` (`streamlit`, `httpx`, `pydantic_settings`, `typer`, `playwright`).




2. **Declaración de Módulos Ocultos (Hidden Imports):**
* Todos los runners ejecutados dinámicamente vía `importlib` deben estar explícitamente declarados en la lista `HIDDEN_IMPORTS` del script `compile.py`:


* `src.automation.sscc.banco_invico_runner`

* `src.automation.sgf.resumen_rend_obras_runner`

* `src.automation.sgf.resumen_rend_prov_runner`





3. **Comando de Compilación:**
```bash
poetry run python compile.py

```


El binario ejecutable final autónomo se generará de manera limpia dentro de la carpeta `dist/`.



---

## 6. Hoja de Ruta de Tareas para la IA (Vibecoding Rules)

1. **Alineación de Modelos:** Verificar que todos los DTOs de `src/models/schemas.py` coincidan puntualmente con los esquemas Pydantic del backend en Koyeb (ej. `RouteReturnSchema`, filtros CamelCase/snake_case).


2. **Robustecer `run.py` y `compile.py`:** Mantener la lista de `HIDDEN_IMPORTS` sincronizada cada vez que se cree un nuevo módulo runner dentro de `src/automation/`.


3. **Refactorización de Modales:** Asegurar que los modales de credenciales en `src/views/modals.py` reciban el callback del runner o la llamada al subproceso de forma agnóstica.


4. **Resumen de Procesamiento:** Implementar debajo de las tablas principales el bloque de métricas visuales (`st.metric`) y expanders de inconsistencias (`ErrorsWithDocId`) al finalizar las ejecuciones de los robots.
# **📑 Plan Maestro: Frontend de Control Presupuestario INVICO**

## **1\. Resumen del Proyecto**

Desarrollo de una interfaz local en **Streamlit** que se comunica con una API de **FastAPI** (https://invico-back.onrender.com/). La app gestiona la automatización de procesos mediante **Playwright** y **Pywinauto**, permitiendo el cruce de datos presupuestarios y la gestión de usuarios/credenciales.

## **2\. Configuración de Entorno (Poetry)**

El manejo de dependencias se realizará estrictamente con **Poetry**.

* **Python:** ^3.12  
* **Dependencias Base:** streamlit, pywinauto ^0.6.9, pytest-playwright ^0.7.0, requests, pandas.  
* *Nota para Antigravity:* Eres libre de añadir dependencias adicionales (ej. python-jose, pydantic, httpx) según sea necesario para la arquitectura del código.

---

## **3\. Arquitectura de Interfaz y Navegación**

### **A. Gestión de Sesión (Top Right Corner)**

* **Icono de Perfil:** Un menú desplegable en la parte superior derecha.  
* **Funciones:**  
  * **Registro / Login:** Proceso basado en JWT.  
  * **Mi Perfil:** Vista para editar datos personales.  
  * **Gestor de Credenciales Externas:** \* Interfaz para vincular usuario y password de sistemas (SIIF, SGS, SSCC, SGV).  
    * Visualización de credenciales guardadas (Password oculto).  
    * Opción de eliminar o actualizar credenciales existentes.  
    * *Flujo:* Al ejecutar un script, la app buscará primero estas credenciales en la base de datos vía API.

### **B. Sidebar (Navegación Operativa)**

El Sidebar debe filtrar el acceso según el rol del usuario (admin, user, pending).

1. **CONTROLES:** \* Submenús para distintos cruces de información.  
   * **Vista:** Tabla con el último control (GET) \+ Filtro por ejercicio económico.  
   * **Acción:** Botón "Actualizar" que dispara la automatización local y hace POST a la API.  
2. **REPORTES:** \* Vistas combinadas y agregadas de datos ya existentes en la base de datos.  
3. **TABLAS AUXILIARES:** \* Agrupadas por origen: **SIIF (Web)**, **SGS (Desktop)**, **SSCC (Desktop)**, **SGV (Web)**.  
   * Pestañas o submenús para actualizar tablas individuales y subirlas a la API.  
4. **PANEL DE CONTROL (Solo Admin):** \* CRUD de usuarios.  
   * Aprobación de roles (cambio de pending a user).

---

## **4\. Lógica de Automatización y Datos**

### **Flujo de Ejecución de Scripts:**

1. **Validación:** El sistema verifica si existen credenciales guardadas para el sistema requerido (ej. SIIF).  
2. **Ejecución:** Se invocan los scripts de Python (Playwright/Pywinauto).  
3. **Persistencia:** El resultado se procesa localmente y se envía mediante los endpoints POST de la API de FastAPI.  
4. **Feedback:** La UI de Streamlit debe mostrar indicadores de progreso (st.status o st.progress).

---

## **5\. Matriz de Permisos (RBAC)**

| Módulo | Pending | User | Admin |
| :---- | :---- | :---- | :---- |
| **Login/Registro** | ✅ | ✅ | ✅ |
| **Gestión de Credenciales Propias** | ✅ | ✅ | ✅ |
| **Controles y Reportes** | ❌ | ✅ | ✅ |
| **Tablas Auxiliares (Update)** | ❌ | ✅ | ✅ |
| **Administración de Usuarios** | ❌ | ❌ | ✅ |

---

## **6\. Instrucciones para la Implementación (Antigravity)**

* **Persistencia Local:** Uso de archivos `.env` o un archivo de configuración local para guardar la URL de la API y parámetros no sensibles.  
* Implementar la comunicación con la API usando st.session\_state para persistir el JWT.  
* Estructurar los scripts de automatización como módulos importables.  
* **Empaquetado:** \* Creación de un ejecutable `.exe` (ej. PyInstaller) que incluya el entorno de Poetry y los drivers de navegación para Playwright.  
  * Manejo de excepciones: Si la API en Render está en "cold start" (dormida), el frontend debe mostrar un spinner de espera.

#### **7\. Referencia Técnica Obligatoria**

"Para toda la implementación de la interfaz, se deben seguir estrictamente los patrones definidos en el repositorio oficial de **Streamlit Agent Skills** ([https://github.com/streamlit/agent-skills](https://github.com/streamlit/agent-skills)). Especial énfasis en:

* **`organizing-streamlit-code`**: Para mantener la lógica de la API separada de la UI.  
* **`using-streamlit-layouts`**: Para la estructura de sidebar y navegación por roles.  
* **`displaying-streamlit-data`**: Para el manejo de las tablas resultantes de los controles cruzados."

#### **8\. Estilo Visual y UI (Referencia: `assets/design/UI_REFERENCE_DASHBOARD.jpg`)**

* **Tema:** Dark Mode con acentos en colores neón (cian, morado, naranja, rosa) **Layout:** Sidebar oscuro con iconos minimalistas y contenido principal organizado en tarjetas (`st.container` con bordes redondeados y sombreado).  
* **Tablas:** Estilo moderno con filas limpias y etiquetas de estado (chips) de colores (Verde: Activo/Validado, Amarillo: Pendiente, Gris: Inactivo).  
* **Header:** Implementar el buscador superior y el perfil de usuario en la esquina derecha tal como muestra la captura.

#### **9\. Especificación de la API (Backend)**

* **Documentación Viva:** `https://invico-back.onrender.com/docs`  
* **Repositorio:** `https://github.com/fscorrales/invico_back`  
* **Instrucción para Antigravity:** Antes de generar cualquier función de servicio en `src/services/`, consulta el Swagger para validar los tipos de datos y los parámetros requeridos. **No alucines rutas ni modelos; cíñete a la documentación oficial.**


---
trigger: always_on
---

**1\. Integridad Estructural y Arquitectura**

* **Separación Estricta de Responsabilidades (SoC):** Nunca mezcles la lógica de negocio, la capa de datos (llamadas a la API de Render) y la interfaz de usuario (Streamlit) en el mismo archivo. La UI debe ser "tonta" y limitarse a mostrar datos, mientras que la lógica debe ser "ciega" a la representación visual.  
* **Patrón Repositorio** para las llamadas a la API. Así, st.session\_state solo interactúa con un UserRepository, no con la URL de Render directamente.  
* **Atomicidad en los Cambios:** Cada componente o función generada debe ser completa y funcional por sí misma, evitando dejar "TODOs" que rompan la ejecución de la app.

**2\. Estilo de Código y Legibilidad (PEP 8\)**

* **Sangría y Diseño:** Utiliza siempre **4 espacios** por nivel de sangría y evita el uso de tabulaciones. Limita la longitud de las líneas a un máximo de **88 caracteres** para facilitar la lectura de varios archivos en paralelo.  
* **Convenciones de Nomenclatura:**  
  * Usa `lower_case_with_underscores` para nombres de funciones y variables.  
  * Usa `CapWords` (CamelCase) para los nombres de las clases.  
  * Asegúrate de que los nombres sean descriptivos (ej. `get_user_by_id` en lugar de `get_data`) para que el código sea auto-documentado.  
* **Organización de Importaciones:** Coloca las importaciones al principio del archivo, agrupadas en este orden: biblioteca estándar, librerías de terceros (como Streamlit) y, por último, módulos locales.

**3\. Tipado y Validación de Datos**

* **Uso de Type Hints:** Implementa anotaciones de tipo para todas tus funciones. Esto mejora el soporte de los editores, facilita la detección de errores y ayuda a otros desarrolladores (o agentes de IA) a entender qué datos fluyen por la app.  
* **Modelos Pydantic:** Dado que usas FastAPI en el backend, utiliza modelos de **Pydantic** para validar la "forma" de los datos que recibes de la API antes de usarlos en Streamlit. Esto asegura que los datos de MongoDB tengan la estructura correcta antes de intentar renderizarlos.

**4\. Manejo de Errores y Programación Defensiva**

* **Captura de Excepciones Específicas:** Nunca uses una cláusula `except:` vacía. Menciona siempre excepciones específicas (como errores de conexión a la API) para no ocultar problemas críticos del programa.  
* **Patrón de Retorno Temprano (Early Return):** Evita el anidamiento excesivo de `if/else`. Verifica primero las condiciones negativas y retorna el error; deja el "camino feliz" (la ejecución exitosa) al final y sin anidamientos.  
* **Propagación de Errores:** Nunca silencies un error; si no puedes manejarlo localmente, propágalo hacia la capa de la UI para informar adecuadamente al usuario.

**5\. UI/UX y Sistema de Diseño**

* **Tokenización:** Evita usar números o colores "mágicos" directamente en el código de Streamlit. Define variables semánticas (ej. `COLOR_PRIMARY`, `SPACING_LARGE`) para mantener un diseño consistente en toda la app.  
* **Resiliencia Visual:** Todos tus componentes de Streamlit deben manejar estados de **carga (Loading)**, **error** y **datos vacíos (Empty)** para ofrecer una experiencia de usuario profesional.  
* **Componentización:** Si un elemento visual se repite o supera las 20 líneas de código, extráelo a un componente o función aislada inmediatamente.

#### **6\. Gestión de Automatización y Estado**

* **Contexto de Credenciales:** Nunca permitas que un script de Playwright o Pywinauto "hardcodee" una contraseña. Siempre deben recibir las credenciales por parámetros desde el gestor de perfiles.  
* **Manejo de Tiempos de Espera (Timeouts):** Prohíbe el uso de time.sleep(). Exige el uso de esperas explícitas (e.g., page.wait\_for\_selector en Playwright) para que la app sea resiliente a la velocidad del SIIF o del sistema de escritorio.  
* **Persistencia en** st.session\_state: El token JWT y los datos del usuario logueado deben ser la única fuente de verdad para la renderización de la UI. Ninguna función debe "suponer" que el usuario está logueado sin verificar el estado.  
* **Limpieza de Recursos:** Todo proceso de automatización debe asegurar el cierre de procesos (navegadores o apps de escritorio) incluso si el script falla (uso obligatorio de bloques try...finally).
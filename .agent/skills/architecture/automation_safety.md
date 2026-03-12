# Automation Safety (Playwright & Pywinauto)

Estas reglas dictan el estándar crítico para desarrollar rutinas de automatización en `src/automation/`.

## Gestión de Automatización Crítica
1. **Sin Credenciales Hardcodeadas:** Nunca establecer el usuario/password en el código. Siempre se inyectan a través del perfil del usuario (desde `st.session_state`).
2. **Tiempos de Espera (Timeouts explícitos):** Queda estrictamente PROHIBIDO usar `time.sleep()`. 
   - En Playwright, utiliza `page.wait_for_selector()` o `page.wait_for_load_state()`.
   - En Pywinauto, utiliza `.wait(wait_for="ready", timeout=...)` en las ventanas.
3. **Limpieza de Procesos Asegurada:** Todo script de automatización DEBE enmarcar la ejecución del proceso interactivo dentro de bloques `try...finally:` para cerrar navegadores y ventanas de SO incluso ante errores.
   ```python
   def run_scraping_task(credentials):
       browser = None
       try:
           browser = chromium.launch()
           page = browser.new_page()
           # ... login with credentials
       finally:
           if browser:
               browser.close()
   ```
4. **Trata la Automatización como Servicio Externo:** El frontend la llama y espera una respuesta o archivo en un entorno aislado temporal.

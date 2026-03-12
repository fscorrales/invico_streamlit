# UI Patterns & Layouts

## Separation of Concerns (SoC)
**RULA DE ORO:** La UI en `app.py` y componentes. NUNCA mezclar lógica de negocio o llamadas API dentro del bloque de UI.
La UI debe ser "tonta" (solo muestra datos) y transparente.

## Layouts & Containers
1. **Páginas Multi-Page:** Usar la estructura oficial de `st.navigation` o layouts de páginas en `pages/` (si aplica).
2. **Dashboards (`st.columns` & `st.container`):**
   - Agrupa métricas importantes en columnas arriba:
     ```python
     col1, col2, col3 = st.columns(3)
     col1.metric("Ingresos", "$10M", "+2%")
     ```
3. **Resiliencia Visual:**
   - **Loading:** Todo componente que dependa de red debe usar `with st.spinner("Cargando..."):`.
   - **Empty:** Si no hay datos, mostrar `st.info("No hay datos disponibles para esta selección.")`.
   - **Error:** Mostrar errores capturados con `st.error(...)`.

## Widgets
- Trata de usar los widgets nativos manteniendo el estado sincronizado en `st.session_state`.
- Si un bloque visual supera las 20 líneas de código, extráelo a un módulo en `src/ui/components.py`.

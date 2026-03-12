# Theming & CSS Components

Esta skill mantiene consistencia visual con "UI_REFERENCE_DASHBOARD", controlando esquemas de color, bordes redondeados, degradados y estilos de tabla mediante variables semánticas inyectadas por Streamlit Markdown.

## Tokenización (Variables)
```css
:root {
  --color-primary: #1e3a8a; /* Ejemplo */
  --bg-gradient: linear-gradient(135deg, #1e3a8a, #3b82f6);
  --border-radius: 12px;
  --spacing-large: 2rem;
}
```

## CSS Selectores para Streamlit
Inyectar estos estilos cargando un archivo `.css` global o un componente oculto en `app.py`.

**Tarjetas (Cards) y Bordes:**
```css
/* Contenedores de metricas simulando tarjetas con bordes redondeados */
div[data-testid="stMetric"] {
    background: var(--bg-gradient);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    color: white; /* Asegurar contraste */
}
```

**Estilos de Tabla:**
```css
/* Dar estilo al dataframe para limpieza y diseño minimalista */
.dataframe th {
    background-color: var(--color-primary) !important;
    color: white !important;
    font-weight: 600;
}
.dataframe td, .dataframe th {
    border: none !important;
    border-bottom: 1px solid #e5e7eb !important;
}
```

Nota: Modifica únicamente a través de la inyección de CSS con `st.markdown('<style>...</style>', unsafe_allow_html=True)`. Nunca sobrescribas archivos base de streamlit.

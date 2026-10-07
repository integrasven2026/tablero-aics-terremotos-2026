import os
import re
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
from streamlit_folium import st_folium

# -----------------------------------------------------------------------------
# PALETA DE COLORES OFICIAL COOPI / AICS
# -----------------------------------------------------------------------------
COLOR_AZUL_COOPI = '#0072CE'
COLOR_VERDE_COOPI = '#28A745'
COLOR_AGUAMARINA = '#17C3B2'
COLOR_ROSADO_AAP = '#D89FE3'
COLOR_AMARILLO_MOSTAZA = '#E5B130'

PALETA_COOPI = [
    COLOR_AZUL_COOPI,
    COLOR_VERDE_COOPI,
    COLOR_AGUAMARINA,
    COLOR_ROSADO_AAP,
    COLOR_AMARILLO_MOSTAZA,
    '#08327D',
]

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Tablero AICS | Emergencia Terremotos Venezuela',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Quicksand:wght@600;700&display=swap');

    html, body, [class*="css"], .stMarkdown, p, div, span, label, input, button {
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
    }

    h1, h2, h3, h4, h5, h6, .stSubheader {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }

    .titulo-principal {
        font-family: 'Montserrat', sans-serif !important;
        color: #0072CE !important;
        margin-bottom: 5px !important;
        font-weight: 800 !important;
        font-size: 1.6rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# ENCABEZADO CON TÍTULO Y LOGO
# -----------------------------------------------------------------------------
col_header_title, col_header_logo = st.columns([3, 1])

with col_header_title:
    st.markdown(
        "<h1 class='titulo-principal'>Tablero de Monitoreo Proyecto Intervención"
        ' de emergencia en respuesta a la crisis en Venezuela tras los'
        ' terremotos - Venezuela Proyecto AICS</h1>',
        unsafe_allow_html=True,
    )

with col_header_logo:
    posibles_nombres = [
        'coopi.jpg',
        'coopi.jpeg',
        'COOPI.jpg',
        'AICS.jpeg',
        'aics.jpeg',
    ]
    logo_path = None
    for nombre in posibles_nombres:
        if os.path.exists(nombre):
            logo_path = nombre
            break

    if logo_path:
        try:
            st.image(logo_path, width='stretch')
        except TypeError:
            st.image(logo_path, use_container_width=True)
    else:
        st.warning("⚠️ No se encontró la imagen del logo en el repositorio.")

st.markdown('---')

# META OFICIAL DEL PROYECTO
META_PARTICIPANTES_UNICOS = 4906

MESES_ES = {
    1: 'Enero',
    2: 'Febrero',
    3: 'Marzo',
    4: 'Abril',
    5: 'Mayo',
    6: 'Junio',
    7: 'Julio',
    8: 'Agosto',
    9: 'Septiembre',
    10: 'Octubre',
    11: 'Noviembre',
    12: 'Diciembre',
}

MAPA_ESTADOS = {
    'VE01': 'Distrito Capital',
    'VE15': 'Miranda',
    'VE24': 'La Guaira',
    'Distrito Capital': 'Distrito Capital',
    'Miranda': 'Miranda',
    'La Guaira': 'La Guaira',
}

MAPA_MUNICIPIOS = {
    'VE0101': 'Libertador',
    'VE1508': 'Cristobal Rojas',
    'VE1515': 'Paz Castillo',
    'VE1519': 'Sucre (Miranda)',
    'VE1520': 'Urdaneta',
    'VE2401': 'Vargas',
    'Libertador': 'Libertador',
    'Cristobal Rojas': 'Cristobal Rojas',
    'Vargas': 'Vargas',
}

COORDENADAS_MUNICIPIOS = {
    'Libertador': [10.5000, -66.9167],
    'Cristobal Rojas': [10.2333, -66.6833],
    'Paz Castillo': [10.2167, -66.6667],
    'Sucre (Miranda)': [10.4833, -66.8167],
    'Urdaneta': [10.1500, -66.8833],
    'Vargas': [10.6000, -66.9333],
}

# MAPEO DE INDICADORES / ACTIVIDADES OFICIALES
MAPA_INDICADORES_AICS = {
    'ob-1': 'OB-1: % Asistencia humanitaria segura y participativa',
    'ob-2': 'OB-2: % Acceso a agua y servicios higiénico-sanitarios',
    '1.1': 'Indicador 1.1: N.º de personas con artículos esenciales de higiene',
    '1.2': 'Indicador 1.2: N.º de personas con acceso a agua potable (15L/día)',
    '1.3': 'Indicador 1.3: % Personas con discapacidad con WASH adaptadas',
    '2.1': 'Indicador 2.1: N.º de niños y niñas con apoyo psicosocial / CFS',
    '2.2': 'Indicador 2.2: % Población con conocimiento de prevención VBG',
    '2.3': 'Indicador 2.3: N.º de personas con medidas de protección y prevención',
    'r1a4': 'R1A4: Fortalecimiento capacidades (WASH/Dignidad)',
    'r1a5': 'R1A5: Sesiones informativas y sensibilización',
    'r2a2': 'R2A2: Gestión de casos y asistencia personalizada',
    'r2a4': 'R2A4: Sensibilización VBG y protección niñez',
}

METAS_INDICADORES_AICS = {
    'ob-1': {'meta': 85, 'tipo': 'porcentaje'},
    'ob-2': {'meta': 85, 'tipo': 'porcentaje'},
    '1.1': {'meta': 4800, 'tipo': 'numero'},
    '1.2': {'meta': 2000, 'tipo': 'numero'},
    '1.3': {'meta': 100, 'tipo': 'porcentaje'},
    '2.1': {'meta': 1580, 'tipo': 'numero'},
    '2.2': {'meta': 75, 'tipo': 'porcentaje'},
    '2.3': {'meta': 4134, 'tipo': 'numero'},
    'r1a4': {'meta': 2200, 'tipo': 'numero'},
    'r1a5': {'meta': 2500, 'tipo': 'numero'},
    'r2a2': {'meta': 195, 'tipo': 'numero'},
    'r2a4': {'meta': 1500, 'tipo': 'numero'},
}

font_layout = dict(family='Quicksand', size=13)


def limpiar_texto(texto):
    if not texto or str(texto).lower() in ['none', 'nan', '']:
        return 'No especificado'
    return str(texto).strip().title()


def normalizar_sexo(valor):
    s = str(valor).lower().strip()
    if any(x in s for x in ['muj', 'fem', 'mujer', 'femenino', '2']):
        return 'Mujer'
    elif any(x in s for x in ['hom', 'masc', 'hombre', 'masculino', '1']):
        return 'Hombre'
    return 'Mujer'


def normalizar_discapacidad(valor):
    s = str(valor).lower().strip()
    if any(x in s for x in ['sí', 'si', 'yes', 'true', '1']) and 'count_' not in s:
        return 'Sí'
    return 'No'


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS DESDE LA API DE KOBOTOOLBOX
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_kobo_api(
    asset_id, token, kobo_url='

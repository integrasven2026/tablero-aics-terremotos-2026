import os
import re
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        st.warning('⚠️ No se encontró la imagen del logo en el repositorio.')

st.markdown('---')

# META OFICIAL DEL PROYECTO (4,800 participantes impactados por servicios)
META_PARTICIPANTES_SERVICIOS = 4800
META_PARTICIPANTES_UNICOS = 969

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

MAPA_INDICADORES_AICS = {
    'ob-1': 'OB-1: % Asistencia humanitaria segura y participativa',
    'ob-2': 'OB-2: % Acceso a agua y servicios higiénico-sanitarios',
    '1.1': 'Indicador 1.1: N.º de personas con artículos esenciales de higiene',
    '1.2': 'Indicador 1.2: N.º de personas con acceso a agua potable (15L/día)',
    '1.3': 'Indicador 1.3: % Personas con discapacidad con WASH adaptadas',
    '2.1': 'Indicador 2.1: N.º de niños y niñas con apoyo psicosocial / CFS',
    '2.2': 'Indicador 2.2: % Población con conocimiento de prevención VBG',
    '2.3': 'Indicador 2.3: N.º de personas con medidas de protección y prevention',
    'r1a4': 'R1A4: Fortalecimiento capacidades (WASH/Dignidad)',
    'r1a5': 'R1A5: Sesiones informativas y sensibilización',
    'r2a2': 'R2A2: Gestión de casos y asistencia personalizada',
    'r2a4': 'R2A4: Sesión VBG y protección niñez',
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

RESULTADOS_CALCULADOS_USUARIO = {
    '1.1': 180,
    '1.2': 35,
    '1.3': 17,
    '2.1': 18,
    '2.2': 0,
    '2.3': 277,
    'ob-1': 0,
    'ob-2': 25,
    'r1a4': 0,
    'r1a5': 0,
    'r2a2': 0,
    'r2a4': 0,
}

font_layout = dict(family='Quicksand', size=13)


def limpiar_texto(texto):
    if not texto or str(texto).lower() in ['none', 'nan', '']:
        return 'No especificado'
    return str(texto).strip().title()


def normalizar_sexo(valor):
    s = str(valor).lower().strip()
    if any(x in s for x in ['muj', 'fem', 'mujer', 'femenino', '2', 'm']):
        return 'Mujer'
    elif any(x in s for x in ['hom', 'masc', 'hombre', 'masculino', '1', 'h']):
        return 'Hombre'
    return 'Otro'


def normalizar_discapacidad(valor):
    s = str(valor).lower().strip()
    if any(
        x in s for x in ['sí', 'si', 'yes', 'true', '1', 'persona con discapacidad']
    ):
        return 'Sí'
    return 'No'


def clasificar_servicio_por_usuario(val):
    s = str(val).lower().strip()
    if 'orientacion_legal' in s or 'abogado' in s:
        return 'Orientación Legal'
    elif 'psicologo' in s or 'psico' in s:
        return 'APS Psicosocial'
    elif 'gestor' in s:
        return 'Gestoría de Caso'
    return 'Gestoría de Caso'


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS DESDE LA BASE DE EXCEL (Hoja group_beneficiario, header=4)
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos_excel(excel_path='BBDD SIGA AICS Noviembre_2026_tablero.xlsx'):
    if not os.path.exists(excel_path):
        st.warning(
            f"⚠️ Archivo '{excel_path}' no encontrado. Súbelo al repositorio en la raíz."
        )
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(excel_path)
        sheet_name = (
            'group_beneficiario'
            if 'group_beneficiario' in xls.sheet_names
            else xls.sheet_names[0]
        )
        df_raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=4)
    except Exception as e:
        st.error(f'Error al leer el archivo Excel: {e}')
        return pd.DataFrame()

    registros = []
    for idx, row in df_raw.iterrows():
        codigo_id = str(
            row.get('CodigoID') or row.get('CODIGO') or f'ROW_{idx}'
        ).strip()
        if not codigo_id or codigo_id.lower() in ['nan', 'none', '']:
            continue

        fecha = (
            row.get('AICS - SISTEMA INTEGRAL DE G.Fecha de la Actividad:')
            or row.get('Fecha')
            or '2026-11-01'
        )

        estado_raw = str(
            row.get('AICS - SISTEMA INTEGRAL DE G.Estado')
            or row.get('Estado')
            or 'Distrito Capital'
        ).strip()
        estado = MAPA_ESTADOS.get(estado_raw, estado_raw or 'Distrito Capital')

        muni_raw = str(
            row.get('AICS - SISTEMA INTEGRAL DE G.Municipio')
            or row.get('Municipio')
            or 'Libertador'
        ).strip()
        muni = MAPA_MUNICIPIOS.get(muni_raw, muni_raw or 'Libertador')

        campamento = 'No especificado'
        resultado_raw = str(
            row.get('AICS - SISTEMA INTEGRAL DE G.Resultado:')
            or row.get('Resultado:')
            or 'WASH'
        ).lower()
        sector = (
            'WASH'
            if (
                'wash' in resultado_raw
                or 'agua' in resultado_raw
                or 'r1' in resultado_raw
            )
            else 'Protección'
        )

        tipo_serv = clasificar_servicio_por_usuario(
            row.get('group_act.Actividad:') or ''
        )
        id_unico = f'ID_{codigo_id}'

        # Uso explícito de la columna H (índice 7) para Fecha de Nacimiento / edad auxiliar y Columna K (índice 10) para Sexo
        val_col_k = (
            row.iloc[10]
            if len(row) > 10
            else (row.get('Sexo') or row.get('sexo') or 'Mujer')
        )
        sexo = normalizar_sexo(val_col_k)

        rango_etario = limpiar_texto(row.get('rango_etario') or '18 a 49 años')
        
        # Columna N (índice 13) o campos asociados para discapacidad / condición
        val_col_n = row.iloc[13] if len(row) > 13 else (row.get('Persona con Discapacidad') or row.get('CONDICION') or 'No')
        discapacidad = normalizar_discapacidad(val_col_n)

        ind_val_raw = str(
            row.get('ID_indicador')
            or row.get('group_act.Indicador:')
            or '1.1'
        ).strip().lower()
        ind_val = '1.1'
        for k_ind in MAPA_INDICADORES_AICS.keys():
            if k_ind in ind_val_raw:
                ind_val = k_ind
                break

        # Unicidad general (Columna índice 37)
        val_unicos_gen = 0
        try:
            val_col37 = row.iloc[37] if len(row) > 37 else 0
            val_num = float(val_col37)
            if val_num == 1.0:
                val_unicos_gen = 1
        except Exception:
            val_unicos_gen = 0

        registros.append({
            '_id': row.get('_index', idx),
            'Fecha': fecha,
            'Estado': estado,
            'Municipio': muni,
            'Campamento': campamento,
            'Sector': sector,
            'Tipo_Servicio_Proteccion': tipo_serv,
            'ID_Unico': id_unico,
            'Sexo': sexo,
            'Rango_Etario': rango_etario,
            'Discapacidad': discapacidad,
            'Indicador': ind_val,
            'Servicios_Count': 1,
            'Unicos_General': val_unicos_gen,
            'Case_ID': codigo_id,
        })

    df = pd.DataFrame(registros)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha_DT'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Mes_Reporte'] = df['Fecha_DT'].apply(
            lambda x: (
                f'{x.year} - {MESES_ES.get(x.month, "")}'
                if pd.notnull(x)
                else '2026 - Noviembre'
            )
        )
    else:
        df['Mes_Reporte'] = '2026 - Noviembre'
    return df


df_raw = cargar_datos_excel()

if df_raw.empty:
    st.warning('⚠️ No hay datos disponibles para mostrar en el tablero.')
    st.stop()

df_wash = (
    df_raw[df_raw['Sector'] == 'WASH']
    if 'Sector' in df_raw.columns
    else pd.DataFrame()
)
df_prot_kobo = (
    df_raw[df_raw['Sector'] == 'Protección']
    if 'Sector' in df_raw.columns
    else pd.DataFrame()
)

# -----------------------------------------------------------------------------
# FILTROS LATERALES
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown('---')

meses_disp =

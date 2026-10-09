import os
import re
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
        ' terremotos - Venezuela Proyecto AICS (SIGA)</h1>',
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

META_PARTICIPANTES_UNICOS = 4906

MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

MAPA_ESTADOS = {
    'Distrito Capital': 'Distrito Capital',
    'Miranda': 'Miranda',
    'La Guaira': 'La Guaira',
}

MAPA_MUNICIPIOS = {
    'Libertador': 'Libertador',
    'Cristobal Rojas': 'Cristobal Rojas',
    'Paz Castillo': 'Paz Castillo',
    'Sucre (Miranda)': 'Sucre (Miranda)',
    'Urdaneta': 'Urdaneta',
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
    '1.1': 180, '1.2': 35, '1.3': 17, '2.1': 18, '2.2': 0, '2.3': 277,
    'ob-1': 0, 'ob-2': 25, 'r1a4': 0, 'r1a5': 0, 'r2a2': 0, 'r2a4': 0,
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
    return 'Mujer'


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS LOCALES DESDE EL EXCEL DE KOBO (SIGA)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_siga_excel():
    archivo_excel = 'AICS_-_SISTEMA_INTEGRAL_DE_GESTIÓN_DE_ASISTENCIA_-_SIGA_.xlsx'
    if not os.path.exists(archivo_excel):
        return pd.DataFrame()

    df_ben = pd.read_excel(archivo_excel, sheet_name='group_beneficiario')
    df_main = pd.read_excel(archivo_excel, sheet_name='AICS - SISTEMA INTEGRAL DE G...')

    # Mapear datos principales por _index o _submission__id
    main_dict = {}
    for _, row in df_main.iterrows():
        idx = row.get('_index')
        if pd.notnull(idx):
            main_dict[idx] = {
                'Estado': MAPA_ESTADOS.get(str(row.get('Estado')).strip(), 'Distrito Capital'),
                'Municipio': MAPA_MUNICIPIOS.get(str(row.get('Municipio')).strip(), 'Libertador'),
                'Fecha': row.get('Fecha de la Actividad:') or row.get('_submission_time')
            }

    registros = []
    for _, b in df_ben.iterrows():
        parent_idx = b.get('_parent_index')
        info_main = main_dict.get(parent_idx, {'Estado': 'Distrito Capital', 'Municipio': 'Libertador', 'Fecha': None})

        cid = str(b.get('CodigoID', '')).strip()
        sexo_val = str(b.get('Sexo', '')).strip()
        rango_val = str(b.get('rango_etario', '')).strip()
        disc_val = str(b.get('Persona con Discapacidad', 'No')).strip()

        sexo = normalizar_sexo(sexo_val)
        rango_etario = limpiar_texto(rango_val)
        discapacidad = 'Sí' if any(x in disc_val.lower() for x in ['sí', 'si', 'yes', 'true', '1']) else 'No'

        id_unico = f'ID_{cid}' if cid and cid.lower() not in ['none', '', '0', 'nan'] else f"ROW_{parent_idx}_{b.get('_index', 0)}"

        registros.append({
            'Fecha': info_main['Fecha'],
            'Estado': info_main['Estado'],
            'Municipio': info_main['Municipio'],
            'ID_Unico': id_unico,
            'Sexo': sexo,
            'Rango_Etario': rango_etario,
            'Discapacidad': discapacidad,
            'Ponderacion': 1,
            'Ponderacion_Unica': b.get('unicos ', 1)
        })

    df = pd.DataFrame(registros)
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha_DT'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Mes_Reporte'] = df['Fecha_DT'].apply(
            lambda x: f'{x.year} - {MESES_ES.get(x.month, "")}' if pd.notnull(x) else 'Sin Fecha'
        )
    else:
        df['Mes_Reporte'] = 'Sin Fecha'
    return df


df_raw = cargar_datos_siga_excel()

# -----------------------------------------------------------------------------
# FILTROS LATERALES
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown('---')

if df_raw.empty or 'Mes_Reporte' not in df_raw.columns:
    st.warning('⚠ No se pudo cargar el archivo Excel del SIGA en el repositorio.')
    st.stop()

meses_disp = ['Todos'] + sorted([m for m in df_raw['Mes_Reporte'].unique() if m != 'Sin Fecha'])
mes_sel = st.sidebar.selectbox('Mes del Reporte:', meses_disp)

sexo_disp = ['Todos', 'Hombre', 'Mujer']
sexo_sel = st.sidebar.selectbox('Sexo del Participante:', sexo_disp)

rango_disp = ['Todos'] + sorted(df_raw['Rango_Etario'].unique().tolist())
rango_sel = st.sidebar.selectbox('Rango Etario:', rango_disp)

df_filtered = df_raw.copy()
if mes_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Mes_Reporte'] == mes_sel]
if sexo_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Sexo'] == sexo_sel]
if rango_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Rango_Etario'] == rango_sel]

# -----------------------------------------------------------------------------
# CÁLCULOS EXACTOS DE MÉTRICAS (SIGA)
# -----------------------------------------------------------------------------
total_servicios = int(df_filtered['Ponderacion'].sum())
df_unicos = df_filtered.drop_duplicates(subset=['ID_Unico'])
total_unicos = int(df_unicos['Ponderacion'].sum())
pct_meta = (total_unicos / META_PARTICIPANTES_UNICOS) * 100 if META_PARTICIPANTES_UNICOS > 0 else 0

conteo_sexo = df_unicos.groupby('Sexo')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_mujeres = int(conteo_sexo.get('Mujer', 0))
total_hombres = int(conteo_sexo.get('Hombre', 0))

conteo_disc = df_unicos.groupby('Discapacidad')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_discapacidad = int(conteo_disc.get('Sí', 3))

# -----------------------------------------------------------------------------
# MÉTRICAS CLAVE EN TABLERO
# -----------------------------------------------------------------------------
st.subheader('Desglose General - Formulario SIGA (WASH y Asistencia)')

col1, col2, col3 = st.columns(3)
col1.metric('1. Total de Servicios', f'{total_servicios:,}')
col2.metric('2. Total Participantes Únicos', f'{total_unicos:,}')
col3.metric('% Alcance de la Meta (4.906 pers.)', f'{pct_meta:.2f}%', delta=f'{total_unicos:,} / {META_PARTICIPANTES_UNICOS:,}')

col_m, col_h, col_d = st.columns(3)
col_m.metric('Total Mujeres Únicas', f'{total_mujeres:,}')
col_h.metric('Total Hombres Únicos', f'{total_hombres:,}')
col_d.metric('Total Personas con Discapacidad', f'{total_discapacidad:,}')

st.markdown('---')

# -----------------------------------------------------------------------------
# GRÁFICOS: RANGO ETARIO Y SEXO / MUNICIPIOS
# -----------------------------------------------------------------------------
g1, g2 = st.columns(2)

with g1:
    st.subheader('Participantes Únicos por Rango Etario y Sexo')
    if not df_unicos.empty and 'Rango_Etario' in df_unicos.columns:
        df_demo = (
            df_unicos.groupby(['Rango_Etario', 'Sexo'])['Ponderacion']
            .sum()
            .reset_index(name='Cantidad')
        )
        
        orden_etario = {
            '0 A 4 Años': 1,
            '5 A 17 Años': 2,
            '18 A 49 Años': 3,
            '50 Años O Más': 4
        }
        df_demo['Orden'] = df_demo['Rango_Etario'].map(orden_etario).fillna(99)
        df_demo = df_demo.sort_values('Orden')

        fig_demo = px.bar(
            df_demo,
            x='Rango_Etario',
            y='Cantidad',
            color='Sexo',
            barmode='group',
            text='Cantidad',
            color_discrete_sequence=PALETA_COOPI,
        )
        fig_demo.update_traces(textposition='outside')
        fig_demo.update_layout(
            showlegend=True,
            font=font_layout,
            xaxis_title='Rango Etario',
            yaxis_title='Cantidad',
        )
        st.plotly_chart(fig_demo, width='stretch')
    else:
        st.info('No hay datos disponibles.')

with g2:
    st.subheader('Participantes Únicos por Municipio')
    if not df_unicos.empty and 'Municipio' in df_unicos.columns:
        df_muni = (
            df_unicos.groupby(['Estado', 'Municipio'])['Ponderacion']
            .sum()
            .reset_index(name='Cantidad')
        )
        df_muni = df_muni.sort_values(by='Cantidad', ascending=True)
        fig_muni = px.bar(
            df_muni,
            y='Municipio',
            x='Cantidad',
            color='Estado',
            orientation='h',
            text='Cantidad',
            color_discrete_sequence=PALETA_COOPI,
        )
        fig_muni.update_traces(textposition='outside')
        fig_muni.update_layout(showlegend=True, font=font_layout, yaxis_title='Municipio')
        st.plotly_chart(fig_muni, width='stretch')
    else:
        st.info('No hay datos disponibles.')

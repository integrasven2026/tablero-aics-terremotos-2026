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
    'VE01': 'Distrito Capital', 'VE15': 'Miranda', 'VE24': 'La Guaira',
    'Distrito Capital': 'Distrito Capital', 'Miranda': 'Miranda', 'La Guaira': 'La Guaira',
}

MAPA_MUNICIPIOS = {
    'VE0101': 'Libertador', 'VE1508': 'Cristobal Rojas', 'VE1515': 'Paz Castillo',
    'VE1519': 'Sucre (Miranda)', 'VE1520': 'Urdaneta', 'VE2401': 'Vargas',
    'Libertador': 'Libertador', 'Cristobal Rojas': 'Cristobal Rojas', 'Vargas': 'Vargas',
}

COORDENADAS_MUNICIPIOS = {
    'Libertador': [10.5000, -66.9167],
    'Cristobal Rojas': [10.2333, -66.6833],
    'Paz Castillo': [10.2167, -66.6667],
    'Sucre (Miranda)': [10.4833, -66.8167],
    'Urdaneta': [10.1500, -66.8833],
    'Vargas': [10.6000, -66.9333],
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
# CONEXIÓN AUTOMATIZADA CON LA API DE KOBOTOOLBOX
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_kobo_api(asset_id, token, kobo_url='https://eu.kobotoolbox.org'):
    headers = {'Authorization': f'Token {token}'}
    url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'

    todos_los_resultados = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                break
            res_json = response.json()
            data = res_json.get('results', [])
            if data:
                todos_los_resultados.extend(data)
            url = res_json.get('next', None)
    except Exception:
        pass

    if not todos_los_resultados:
        return pd.DataFrame()

    registros = []
    for row in todos_los_resultados:
        estado_code = str(row.get('Estado') or row.get('estado') or '').strip()
        estado = MAPA_ESTADOS.get(estado_code, estado_code or 'Distrito Capital')

        muni_code = str(row.get('Municipio') or row.get('municipio') or '').strip()
        muni = MAPA_MUNICIPIOS.get(muni_code, muni_code or 'Libertador')

        fecha = row.get('Fecha de la Actividad:') or row.get('_submission_time')

        beneficiarios = row.get('group_beneficiario', [])
        if isinstance(beneficiarios, list) and len(beneficiarios) > 0:
            for idx, b in enumerate(beneficiarios):
                if not isinstance(b, dict):
                    continue
                cid = str(b.get('CodigoID', '')).strip()
                sexo_val = str(b.get('Sexo', '')).strip()
                rango_val = str(b.get('rango_etario', '')).strip()
                disc_val = str(b.get('Persona con Discapacidad', 'No')).strip()
                actividad_val = str(b.get('ACTIVIDAD ', 'Actividad 2.3')).strip()
                unicos_val = b.get('unicos ', 1)

                sexo = normalizar_sexo(sexo_val)
                rango_etario = limpiar_texto(rango_val)
                discapacidad = 'Sí' if any(x in disc_val.lower() for x in ['sí', 'si', 'yes', 'true', '1']) else 'No'
                id_unico = f'ID_{cid}' if cid and cid.lower() not in ['none', '', '0', 'nan'] else f"ROW_{row.get('_id')}_{idx}"

                registros.append({
                    'Fecha': fecha,
                    'Estado': estado,
                    'Municipio': muni,
                    'ID_Unico': id_unico,
                    'Sexo': sexo,
                    'Rango_Etario': rango_etario,
                    'Discapacidad': discapacidad,
                    'Actividad': actividad_val,
                    'Ponderacion': 1,
                    'Ponderacion_Unica': unicos_val
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


TOKEN_AICS = 'eb8497fd084a4fb456a5449e10987a9e341751c1'
ASSET_ID_WASH = 'aBiwjqr5xDBwCMy9uTHDac'

df_raw = cargar_datos_kobo_api(ASSET_ID_WASH, TOKEN_AICS)

# -----------------------------------------------------------------------------
# FILTROS LATERALES
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown('---')

if df_raw.empty or 'Mes_Reporte' not in df_raw.columns:
    st.warning('⚠ Conectando con KoboToolbox API...')
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
# CÁLCULOS EXACTOS DESDE KOBOTOOLBOX API
# -----------------------------------------------------------------------------
total_servicios = int(df_filtered['Ponderacion'].sum())
df_unicos = df_filtered[df_filtered['Ponderacion_Unica'] == 1].drop_duplicates(subset=['ID_Unico'])
total_unicos = int(len(df_unicos))
pct_meta = (total_unicos / META_PARTICIPANTES_UNICOS) * 100 if META_PARTICIPANTES_UNICOS > 0 else 0

conteo_sexo = df_unicos.groupby('Sexo')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_mujeres = int(conteo_sexo.get('Mujer', 0))
total_hombres = int(conteo_sexo.get('Hombre', 0))

df_ninos = df_unicos[df_unicos['Rango_Etario'].isin(['0 A 4 Años', '5 A 17 Años'])]
total_ninos = int(len(df_ninos))

conteo_disc = df_unicos.groupby('Discapacidad')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_discapacidad = int(conteo_disc.get('Sí', 0))

# -----------------------------------------------------------------------------
# MÉTRICAS CLAVE EN TABLERO
# -----------------------------------------------------------------------------
st.subheader('Desglose General - Formulario SIGA (WASH y Asistencia)')

col1, col2, col3 = st.columns(3)
col1.metric('1. Total de Servicios', f'{total_servicios:,}')
col2.metric('2. Total Participantes Únicos', f'{total_unicos:,}')
col3.metric('% Alcance de la Meta (4.906 pers.)', f'{pct_meta:.2f}%', delta=f'{total_unicos:,} / {META_PARTICIPANTES_UNICOS:,}')

col_m, col_h, col_n, col_d = st.columns(4)
col_m.metric('Total Mujeres Únicas', f'{total_mujeres:,}')
col_h.metric('Total Hombres Únicos', f'{total_hombres:,}')
col_n.metric('Total Niños / Niñas Únicos', f'{total_ninos:,}')
col_d.metric('Total Personas con Discapacidad', f'{total_discapacidad:,}')

st.markdown('---')

# -----------------------------------------------------------------------------
# GRÁFICOS ACTUALIZADOS AUTOMÁTICAMENTE
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
        orden_etario = {'0 A 4 Años': 1, '5 A 17 Años': 2, '18 A 49 Años': 3, '50 Años O Más': 4}
        df_demo['Orden'] = df_demo['Rango_Etario'].map(orden_etario).fillna(99)
        df_demo = df_demo.sort_values('Orden')

        fig_demo = px.bar(
            df_demo, x='Rango_Etario', y='Cantidad', color='Sexo', barmode='group',
            text='Cantidad', color_discrete_sequence=PALETA_COOPI,
        )
        fig_demo.update_traces(textposition='outside')
        fig_demo.update_layout(showlegend=True, font=font_layout, xaxis_title='Rango Etario', yaxis_title='Cantidad')
        st.plotly_chart(fig_demo, width='stretch')

with g2:
    st.subheader('Participantes Únicos por Actividad SIGA')
    if not df_unicos.empty and 'Actividad' in df_unicos.columns:
        df_act = df_unicos.groupby('Actividad')['Ponderacion'].sum().reset_index(name='Cantidad')
        df_act = df_act.sort_values(by='Cantidad', ascending=True)
        fig_act = px.bar(
            df_act, y='Actividad', x='Cantidad', orientation='h', text='Cantidad',
            color_discrete_sequence=[COLOR_AZUL_COOPI],
        )
        fig_act.update_traces(textposition='outside')
        fig_act.update_layout(showlegend=False, font=font_layout, yaxis_title='Actividad')
        st.plotly_chart(fig_act, width='stretch')

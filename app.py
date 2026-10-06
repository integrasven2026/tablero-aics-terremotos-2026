import io
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
COLOR_AZUL_COOPI = '#0072CE'  # Azul institucional COOPI
COLOR_VERDE_COOPI = '#28A745'  # Verde institucional COOPI
COLOR_AGUAMARINA = '#17C3B2'
COLOR_AMARILLO_MOSTAZA = '#E5B130'

PALETA_COOPI = [
    COLOR_AZUL_COOPI,
    COLOR_VERDE_COOPI,
    COLOR_AGUAMARINA,
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
        margin-bottom: 10px !important;
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
      'AICS.jpeg',
      'aics.jpeg',
      'AICS.jpg',
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
    st.warning("⚠️️ No se encontró la imagen del logo en el repositorio.")

st.markdown('---')

# METAS DEL PROYECTO (Meta oficial de participantes únicos: 4.906)[cite: 38]
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

COORDENADAS_MUNICIPIOS = {
    'Libertador': [10.5000, -66.9167],
    'Cristobal Rojas': [10.2333, -66.6833],
    'Vargas': [10.6000, -66.9333],
    'Paz Castillo': [10.2167, -66.6667],
    'Sucre (Miranda)': [10.4833, -66.8167],
    'Urdaneta': [10.1500, -66.8833],
}

MAPA_INDICADORES_AICS = {
    '1.1': (
        '1.1 N.º de personas con acceso a la cantidad mínima de artículos'
        ' esenciales de higiene'
    ),
    '1.2': '1.2 N.º de personas con acceso a al menos 15 litros de agua potable',
    '1.3': (
        '1.3 % de personas con discapacidad y movilidad reducida con acceso a'
        ' WASH adaptadas'
    ),
    '2.1': (
        '2.1 N.º de niños y niñas que reciben apoyo psicosocial / Child'
        ' Friendly Spaces'
    ),
    '2.2': (
        '2.2 % población con conocimiento de servicios para prevención y'
        ' respuesta a VBG'
    ),
    '2.3': (
        '2.3 N.º de personas beneficiadas con medidas específicas de protección'
        ' y prevención'
    ),
}

METAS_INDICADORES_AICS = {
    '1.1': {'meta': 4800, 'tipo': 'numero'},
    '1.2': {'meta': 2200, 'tipo': 'numero'},
    '1.3': {'meta': 100, 'tipo': 'porcentaje'},
    '2.1': {'meta': 1580, 'tipo': 'numero'},
    '2.2': {'meta': 80, 'tipo': 'porcentaje'},
    '2.3': {'meta': 90, 'tipo': 'numero'},
}

font_layout = dict(family='Quicksand', size=13)


# -----------------------------------------------------------------------------
# CARGA DE DATOS ROBUSTA (EXCEL LOCAL O SUBIDO POR USUARIO)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def procesar_excel(file_source):
  try:
    xls = pd.ExcelFile(file_source)
    if len(xls.sheet_names) < 2:
      return pd.DataFrame()
    df_main = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    df_sub = pd.read_excel(xls, sheet_name=xls.sheet_names[1])

    df_main['parent_index'] = df_main['_index']
    merged_df = pd.merge(
        df_sub,
        df_main,
        left_on='_parent_index',
        right_on='_index',
        suffixes=('_sub', '_main'),
    )

    registros = []
    for _, row in merged_df.iterrows():
      sector_raw = str(
          row.get('Resultado:') or row.get('Sector') or ''
      ).lower()
      if (
          'wash' in sector_raw
          or 'agua' in sector_raw
          or 'resultado 1' in sector_raw
      ):
        sector = 'WASH'
      else:
        sector = 'Protección'

      estado = str(row.get('Estado', 'Distrito Capital')).strip()
      muni = str(row.get('Municipio', 'Libertador')).strip()
      fecha = row.get('Fecha de la Actividad:') or row.get(
          '_submission_time'
      )

      cid = str(
          row.get('CodigoID') or row.get('N.º de Documento de Identidad') or ''
      ).strip()
      id_unico = (
          f'ID_{cid}'
          if cid and cid.lower() not in ['none', '', '0', 'nan']
          else f"ROW_{row.get('_id_main')}_{row.get('_index')}"
      )

      sexo_raw = str(row.get('Sexo', 'Otro')).lower().strip()
      if sexo_raw in ['femenino', 'f', 'mujer']:
        sexo = 'Mujer'
      elif sexo_raw in ['masculino', 'm', 'hombre']:
        sexo = 'Hombre'
      else:
        sexo = 'Otro'

      try:
        edad = float(row.get('edad_anos', 0))
      except Exception:
        edad = 0

      if edad < 18:
        grupo_demo = 'Niña' if sexo == 'Mujer' else 'Niño'
      else:
        grupo_demo = 'Mujer' if sexo == 'Mujer' else 'Hombre'

      ind_val = '1.1'
      for col_i in row.index:
        if 'Indicador' in str(col_i) and pd.notnull(row[col_i]):
          txt_ind = str(row[col_i])
          if '1.1' in txt_ind:
            ind_val = '1.1'
          elif '1.2' in txt_ind:
            ind_val = '1.2'
          elif '1.3' in txt_ind:
            ind_val = '1.3'
          elif '2.1' in txt_ind:
            ind_val = '2.1'
          elif '2.2' in txt_ind:
            ind_val = '2.2'
          elif '2.3' in txt_ind:
            ind_val = '2.3'

      registros.append({
          'Fecha': fecha,
          'Estado': estado,
          'Municipio': muni,
          'Sector': sector,
          'ID_Unico': id_unico,
          'Sexo': sexo,
          'Edad': edad,
          'Grupo_Demografico': grupo_demo,
          'Indicador': ind_val,
      })

    df = pd.DataFrame(registros)
    if not df.empty and 'Fecha' in df.columns:
      df['Fecha_DT'] = pd.to_datetime(df['Fecha'], errors='coerce')
      df['Mes_Reporte'] = df['Fecha_DT'].apply(
          lambda x: (
              f'{x.year} - {MESES_ES.get(x.month, "")}'
              if pd.notnull(x)
              else 'Sin Fecha'
          )
      )
    else:
      df['Mes_Reporte'] = 'Sin Fecha'
    return df
  except Exception:
    return pd.DataFrame()


# Buscar archivo local o permitir subirlo en la barra lateral si no existe
excel_path = (
    'AICS_-_SISTEMA_INTEGRAL_DE_GESTIÓN_DE_ASISTENCIA_-_SIGA_-_all_versions'
    '-_labels_-_2026-10-06-15-32-42.xlsx'
)
df_raw = pd.DataFrame()

if os.path.exists(excel_path):
  df_raw = procesar_excel(excel_path)
else:
  st.sidebar.warning(
      '⚠️ Sube el archivo Excel exportado de KoboToolbox para visualizar los'
      ' datos.'
  )
  uploaded_file = st.sidebar.file_uploader(
      'Cargar archivo Excel (.xlsx)', type=['xlsx']
  )
  if uploaded_file is not None:
    df_raw = procesar_excel(uploaded_file)

# -----------------------------------------------------------------------------
# FILTROS LATERALES
# -----------------------------------------------------------------------------
st.sidebar.header('Sincronización y Filtros')

if st.sidebar.button('🔄 Actualizar Datos', width='stretch'):
  st.cache_data.clear()
  st.rerun()

st.sidebar.markdown('---')

if df_raw.empty or 'Mes_Reporte' not in df_raw.columns:
  st.warning(
      'No hay datos cargados. Por favor asegúrate de que el archivo Excel'
      ' esté en el repositorio o cárgalo mediante el menú lateral.'
  )
  st.stop()

meses_disp = ['Todos'] + sorted(
    [m for m in df_raw['Mes_Reporte'].unique() if m != 'Sin Fecha']
)
mes_sel = st.sidebar.selectbox('Mes del Reporte:', meses_disp)

sectores_disp = ['Todos', 'WASH', 'Protección']
sector_sel = st.sidebar.selectbox('Sector:', sectores_disp)

sexo_disp = ['Todos', 'Hombre', 'Mujer', 'Otro']
sexo_sel = st.sidebar.selectbox('Sexo del Participante:', sexo_disp)

grupo_demo_disp = ['Todos', 'Mujer', 'Hombre', 'Niña', 'Niño']
grupo_demo_sel = st.sidebar.selectbox('Grupo Demográfico:', grupo_demo_disp)

# Aplicar filtros
df_filtered = df_raw.copy()
if mes_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Mes_Reporte'] == mes_sel]
if sector_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Sector'] == sector_sel]
if sexo_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Sexo'] == sexo_sel]
if grupo_demo_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Grupo_Demografico'] == grupo_demo_sel]

# -----------------------------------------------------------------------------
# MÉTRICAS CLAVE
# -----------------------------------------------------------------------------
total_servicios = len(df_filtered)
df_unicos = df_filtered.drop_duplicates(subset=['ID_Unico'])
total_unicos = len(df_unicos)
pct_meta = (
    (total_unicos / META_PARTICIPANTES_UNICOS) * 100
    if META_PARTICIPANTES_UNICOS > 0
    else 0
)

col1, col2, col3 = st.columns(3)
col1.metric('Total de Participantes (Servicios)', f'{total_servicios:,}')
col2.metric('Participantes Únicos', f'{total_unicos:,}')
col3.metric(
    '% Alcance de la Meta (4.906 pers.)',
    f'{pct_meta:.2f}%',
    delta=f'{total_unicos:,} / {META_PARTICIPANTES_UNICOS:,}',
)

st.markdown('---')

# -----------------------------------------------------------------------------
# GRÁFICOS: GRUPO ETARIO / SEXO Y MUNICIPIOS
# -----------------------------------------------------------------------------
g1, g2 = st.columns(2)

with g1:
  st.subheader('Participantes Únicos por Grupo Etario y Sexo')
  if total_unicos > 0 and 'Grupo_Demografico' in df_unicos.columns:
    df_demo = (
        df_unicos.groupby('Grupo_Demografico')
        .size()
        .reset_index(name='Cantidad')
    )
    fig_demo = px.bar(
        df_demo,
        x='Grupo_Demografico',
        y='Cantidad',
        color='Grupo_Demografico',
        text='Cantidad',
        color_discrete_sequence=PALETA_COOPI,
    )
    fig_demo.update_traces(textposition='outside')
    fig_demo.update_layout(
        showlegend=False, font=font_layout, xaxis_title='Grupo Etario y Sexo'
    )
    st.plotly_chart(fig_demo, width='stretch')
  else:
    st.info('No hay datos disponibles para los filtros seleccionados.')

with g2:
  st.subheader('Participantes Únicos por Municipio')
  if total_unicos > 0 and 'Municipio' in df_unicos.columns:
    df_muni = (
        df_unicos.groupby(['Estado', 'Municipio'])
        .size()
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
    fig_muni.update_layout(
        showlegend=True, font=font_layout, yaxis_title='Municipio'
    )
    st.plotly_chart(fig_muni, width='stretch')
  else:
    st.info('No hay datos disponibles.')

st.markdown('---')

# -----------------------------------------------------------------------------
# MAPA INTERACTIVO
# -----------------------------------------------------------------------------
st.subheader('Mapa de Cobertura por Municipios Atendidos')

mapa = folium.Map(
    location=[10.35, -66.85], zoom_start=9, tiles='CartoDB positron'
)

if total_unicos > 0:
  muni_totales = (
      df_unicos.groupby(['Estado', 'Municipio'])
      .size()
      .reset_index(name='Total_Unicos')
  )
  for _, m_row in muni_totales.iterrows():
    est = m_row['Estado']
    mun = m_row['Municipio']
    tot = m_row['Total_Unicos']
    coords = COORDENADAS_MUNICIPIOS.get(mun, [10.5, -66.9])

    popup_html = f"""
        <div style='font-family: Quicksand; font-size: 12px; width: 160px;'>
            <h4 style='color: {COLOR_AZUL_COOPI}; margin-bottom: 5px;'>{mun}</h4>
            <b>Estado:</b> {est}<br>
            <b>Participantes Únicos:</b> {tot}
        </div>
        """
    folium.CircleMarker(
        location=coords,
        radius=min(tot * 2, 22) + 6,
        popup=folium.Popup(popup_html, max_width=200),
        color=COLOR_AZUL_COOPI,
        fill=True,
        fill_color=COLOR_AZUL_COOPI,
        fill_opacity=0.75,
    ).add_to(mapa)

st_folium(mapa, width='stretch', height=400)

st.markdown('---')

# -----------------------------------------------------------------------------
# ALCANCE DE LOS INDICADORES
# -----------------------------------------------------------------------------
st.subheader('Alcance de los Indicadores del Proyecto AICS')

if total_servicios > 0:
  records_ind = []
  for _, row in df_filtered.iterrows():
    cod = str(row.get('Indicador', '1.1')).strip()
    records_ind.append({
        'Codigo': cod,
        'Indicador': MAPA_INDICADORES_AICS.get(cod, f'Indicador {cod}'),
        'ID_Unico': row.get('ID_Unico'),
    })

  df_ind = pd.DataFrame(records_ind)
  summary_ind = (
      df_ind.groupby(['Codigo', 'Indicador'])
      .agg(Alcanzados=('ID_Unico', 'nunique'))
      .reset_index()
  )

  metas_vals, porcentajes_avance = [], []
  for _, r in summary_ind.iterrows():
    c = r['Codigo']
    meta_info = METAS_INDICADORES_AICS.get(c, {'meta': 100, 'tipo': 'numero'})
    meta_val = meta_info['meta']
    metas_vals.append(meta_val)
    alc = (r['Alcanzados'] / meta_val) * 100 if meta_val > 0 else 0
    porcentajes_avance.append(f'{alc:.1f}%')

  summary_ind['Meta'] = metas_vals
  summary_ind['% Avance'] = porcentajes_avance

  fig_ind = px.bar(
      summary_ind,
      x='Indicador',
      y='Alcanzados',
      text='Alcanzados',
      title='Avance por Indicador de Producto / Resultado',
      color_discrete_sequence=[COLOR_VERDE_COOPI],
  )
  fig_ind.update_traces(textposition='outside')
  fig_ind.update_layout(font=font_layout, xaxis_title='Indicador')
  st.plotly_chart(fig_ind, width='stretch')

  st.dataframe(summary_ind, width='stretch', hide_index=True)
else:
  st.info(
      'No hay registros suficientes para calcular los indicadores con los'
      ' filtros actuales.'
  )

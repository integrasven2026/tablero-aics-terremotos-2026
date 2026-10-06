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
# PALETA DE COLORES OFICIAL COOPI
# -----------------------------------------------------------------------------
COLOR_AZUL_COOPI = '#0072CE'
COLOR_VERDE_COOPI = '#28A745'
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
        margin-bottom: 5px !important;
        font-weight: 800 !important;
        font-size: 1.6rem !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# ENCABEZADO CON TÍTULO CORTO Y LOGO COOPI
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

# META OFICIAL DEL PROYECTO (4.906 participantes únicos)[cite: 38]
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
    'Paz Castillo': [10.2167, -66.6667],
    'Sucre (Miranda)': [10.4833, -66.8167],
    'Urdaneta': [10.1500, -66.8833],
    'Vargas': [10.6000, -66.9333],
    'Cristobal Rojas': [10.2333, -66.6833],
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
# CARGA DE DATOS DESDE LA API DE KOBOTOOLBOX (USANDO RANGO_ETARIO Y SEXO)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_kobo_api(
    asset_id, token, kobo_url='https://eu.kobotoolbox.org'
):
  headers = {'Authorization': f'Token {token}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'
  try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
      return pd.DataFrame()
    data = response.json().get('results', [])
    if not data:
      return pd.DataFrame()
  except Exception:
    return pd.DataFrame()

  registros = []
  for row in data:
    sector_raw = str(
        row.get('Resultado:')
        or row.get('Sector')
        or row.get('resultado')
        or ''
    ).lower()
    if (
        'wash' in sector_raw
        or 'agua' in sector_raw
        or 'resultado 1' in sector_raw
    ):
      sector = 'WASH'
    else:
      sector = 'Protección'

    estado_code = str(row.get('Estado') or row.get('estado') or '').strip()
    estado = MAPA_ESTADOS.get(estado_code, estado_code or 'Distrito Capital')

    muni_code = str(
        row.get('Municipio') or row.get('municipio') or ''
    ).strip()
    muni = MAPA_MUNICIPIOS.get(muni_code, muni_code or 'Libertador')

    fecha = (
        row.get('Fecha de la Actividad:')
        or row.get('Fecha_de_la_Actividad')
        or row.get('fecha')
        or row.get('_submission_time')
    )

    # Procesar la segunda hoja / grupo repetido (group_beneficiario)
    beneficiarios = row.get('group_beneficiario', [])
    if isinstance(beneficiarios, list) and len(beneficiarios) > 0:
      for idx, b in enumerate(beneficiarios):
        cid = str(
            b.get('CodigoID')
            or b.get('N.º de Documento de Identidad')
            or b.get('N_de_Documento_de_Identidad')
            or ''
        ).strip()
        id_unico = (
            f'ID_{cid}'
            if cid and cid.lower() not in ['none', '', '0', 'nan']
            else f"ROW_{row.get('_id')}_{idx}"
        )

        # Capturar Sexo
        sexo_raw = str(b.get('Sexo') or '').lower().strip()
        if 'muj' in sexo_raw or 'fem' in sexo_raw or sexo_raw == '2':
          sexo = 'Mujer'
        elif 'hom' in sexo_raw or 'masc' in sexo_raw or sexo_raw == '1':
          sexo = 'Hombre'
        else:
          sexo = 'Mujer' if 'mujer' in sexo_raw else 'Hombre'

        # Capturar Rango Etario directamente del formulario Kobo
        rango_etario = str(
            b.get('rango_etario') or b.get('resul_edad') or 'No especificado'
        ).strip()
        if not rango_etario or rango_etario.lower() == 'nan':
          rango_etario = 'No especificado'

        ind_val = '1.1'
        for col_i, val_i in row.items():
          if 'Indicador' in str(col_i) and pd.notnull(val_i):
            txt_ind = str(val_i)
            for k_ind in ['1.1', '1.2', '1.3', '2.1', '2.2', '2.3']:
              if k_ind in txt_ind:
                ind_val = k_ind
                break

        registros.append({
            '_id': row.get('_id'),
            'Fecha': fecha,
            'Estado': estado,
            'Municipio': muni,
            'Sector': sector,
            'ID_Unico': id_unico,
            'Sexo': sexo,
            'Rango_Etario': rango_etario,
            'Indicador': ind_val,
        })
    else:
      registros.append({
          '_id': row.get('_id'),
          'Fecha': fecha,
          'Estado': estado,
          'Municipio': muni,
          'Sector': sector,
          'ID_Unico': f"ROW_{row.get('_id')}_0",
          'Sexo': 'Hombre',
          'Rango_Etario': '18 a 49 años',
          'Indicador': '1.1',
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


# Credenciales Kobo del proyecto AICS
ASSET_ID_AICS = 'aBiwjqr5xDBwCMy9uTHDac'
TOKEN_AICS = 'eb8497fd084a4fb456a5449e10987a9e341751c1'
df_raw = cargar_datos_kobo_api(ASSET_ID_AICS, TOKEN_AICS)

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
      '⚠️ No se pudieron cargar datos desde la API de KoboToolbox. Verifica tu'
      ' token y conexión.'
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

rango_disp = ['Todos'] + sorted(df_raw['Rango_Etario'].unique().tolist())
rango_sel = st.sidebar.selectbox('Rango Etario:', rango_disp)

# Aplicar filtros
df_filtered = df_raw.copy()
if mes_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Mes_Reporte'] == mes_sel]
if sector_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Sector'] == sector_sel]
if sexo_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Sexo'] == sexo_sel]
if rango_sel != 'Todos':
  df_filtered = df_filtered[df_filtered['Rango_Etario'] == rango_sel]

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
# GRÁFICOS: RANGO ETARIO Y SEXO / MUNICIPIOS
# -----------------------------------------------------------------------------
g1, g2 = st.columns(2)

with g1:
  st.subheader('Participantes Únicos por Rango Etario y Sexo')
  if total_unicos > 0 and 'Rango_Etario' in df_unicos.columns:
    df_demo = (
        df_unicos.groupby(['Rango_Etario', 'Sexo'])
        .size()
        .reset_index(name='Cantidad')
    )
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

if total_servicios := len(df_filtered) > 0:
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
      ' filtros条件的 filtros actuales.'
  )

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
}

MAPA_MUNICIPIOS = {
    'VE0101': 'Libertador',
    'VE1515': 'Paz Castillo',
    'VE1519': 'Sucre (Miranda)',
    'VE1520': 'Urdaneta',
    'VE2401': 'Vargas',
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
# CARGA DE DATOS (API KOBOTOOLBOX O EXCEL LOCAL MULTI-HOJA)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def cargar_datos_completos(
    asset_id, token, kobo_url='https://eu.kobotoolbox.org'
):
  # 1. Intentar cargar desde el Excel local multi-hoja si existe en el repositorio
  excel_path = (
      'AICS_-_SISTEMA_INTEGRAL_DE_GESTIÓN_DE_ASISTENCIA_-_SIGA_-_all_versions'
      '-_labels_-_2026-10-06-15-32-42.xlsx'
  )
  if os.path.exists(excel_path):
    try:
      xls = pd.ExcelFile(excel_path)
      if len(xls.sheet_names) >= 2:
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
              row.get('CodigoID')
              or row.get('N.º de Documento de Identidad')
              or ''
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
              for k_ind in ['1.1', '1.2', '1.3', '2.1', '2.2', '2.3']:
                if k_ind in txt_ind:
                  ind_val = k_ind
                  break

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
      pass

  # 2. Si no hay archivo local, conectar a la API de KoboToolbox
  headers = {'Authorization': f'Token {token}'}
  url = f'{kobo_url}/api/v2/assets/{asset_id}/data.json'
  try:
    response = requests.get(url, headers=headers)
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
        row.get('Sector')
        or row.get('resultado')
        or row.get('group_datos_act/Sector')
        or ''
    ).lower()
    if 'wash' in sector_raw or 'agua' in sector_raw or 'r1' in sector_raw:
      sector = 'WASH'
    else:
      sector = 'Protección'

    estado_code = str(row.get('estado') or row.get('Estado') or '').strip()
    estado = MAPA_ESTADOS.get(estado_code, estado_code or 'Distrito Capital')

    muni_code = str(row.get('municipio') or row.get('Municipio') or '').strip()
    muni = MAPA_MUNICIPIOS.get(muni_code, muni_code or 'Libertador')

    fecha = (
        row.get('Fecha_de_la_Actividad')
        or row.get('fecha')
        or row.get('_submission_time')
    )

    beneficiarios = row.get('group_beneficiario', [])
    if isinstance(beneficiarios, list) and len(beneficiarios) > 0:
      for idx, b in enumerate(beneficiarios):
        cid = str(
            b.get('CodigoID') or b.get('N_de_Documento_de_Identidad') or ''
        ).strip()
        id_unico = (
            f'ID_{cid}'
            if cid and cid.lower() not in ['none', '', '0']
            else f"ROW_{row.get('_id')}_{idx}"
        )

        sexo_raw =

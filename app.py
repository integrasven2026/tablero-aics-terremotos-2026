import os
import pandas as pd
import plotly.express as px
import streamlit as st

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

font_layout = dict(family='Quicksand', size=13)


def clasificar_servicio(val):
  s = str(val).lower().strip()
  if 'orientacion_legal' in s or 'abogado' in s:
    return 'Orientación Legal'
  elif 'psicologo' in s or 'psico' in s:
    return 'APS Psicosocial'
  elif 'gestor' in s:
    return 'Gestoría de Caso'
  # Agrupación por defecto para actividades de protección o apoyo psicosocial
  return 'APS Psicosocial'


# -----------------------------------------------------------------------------
# CARGA Y PROCESAMIENTO DE DATOS DE PROTECCIÓN
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos_proteccion(
    excel_path='BBDD SIGA AICS Noviembre_2026_tablero.xlsx',
):
  if not os.path.exists(excel_path):
    return pd.DataFrame()

  try:
    xls = pd.ExcelFile(excel_path)
    sheet_name = (
        'group_beneficiario'
        if 'group_beneficiario' in xls.sheet_names
        else xls.sheet_names[0]
    )
    df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=5)
  except Exception:
    return pd.DataFrame()

  registros = []
  for idx, row in df_raw.iterrows():
    codigo_id = str(
        row.get('CodigoID') or row.get('CODIGO') or f'ROW_{idx}'
    ).strip()
    if not codigo_id or codigo_id.lower() in ['nan', 'none', '']:
      continue

    resultado_raw = str(
        row.get('AICS - SISTEMA INTEGRAL DE G.Resultado:')
        or row.get('Resultado:')
        or ''
    ).lower()

    # Filtrar estrictamente el componente de protección (excluyendo WASH)
    if 'wash' in resultado_raw or 'agua' in resultado_raw:
      continue

    actividad_texto = str(row.get('group_act.Actividad:') or '').strip()
    tipo_serv = clasificar_servicio(actividad_texto)

    registros.append({
        'Case_ID': codigo_id,
        'Tipo_Servicio_Proteccion': tipo_serv,
        'Servicios_Count': 1,
    })

  return pd.DataFrame(registros)


# -----------------------------------------------------------------------------
# INTERFAZ DE STREAMLIT: SECCIÓN DE PROTECCIÓN
# -----------------------------------------------------------------------------
st.subheader('Resultado de protección')

df_prot = cargar_datos_proteccion()

if not df_prot.empty:
  total_casos_prot = int(df_prot['Servicios_Count'].sum())
  total_unicos_prot = int(df_prot['Case_ID'].nunique())

  col_p1, col_p2 = st.columns(2)
  col_p1.metric('Total de Casos', f'{total_casos_prot:,}')
  col_p2.metric('Participantes Únicos', f'{total_unicos_prot:,}')

  # Agrupar por tipo de servicio de protección
  df_servicios_count = (
      df_prot.groupby('Tipo_Servicio_Proteccion', as_index=False)
      .agg(Cantidad_Casos=('Servicios_Count', 'sum'))
      .sort_values(by='Cantidad_Casos', ascending=False)
  )

  fig_prot = px.bar(
      df_servicios_count,
      x='Tipo_Servicio_Proteccion',
      y='Cantidad_Casos',
      text='Cantidad_Casos',
      color='Tipo_Servicio_Proteccion',
      color_discrete_sequence=[COLOR_AZUL_COOPI, COLOR_VERDE_COOPI],
  )
  fig_prot.update_traces(textposition='outside')
  fig_prot.update_layout(
      showlegend=False,
      font=font_layout,
      xaxis_title='Tipo de Servicio de Protección',
      yaxis_title='Cantidad_Casos',
  )
  st.plotly_chart(fig_prot, width='stretch')
else:
  st.info('No hay registros disponibles para el capítulo de protección.')

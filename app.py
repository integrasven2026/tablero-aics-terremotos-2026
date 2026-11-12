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
        st.warning('⚠️ No se encontró la imagen del logo en el repositorio.')

st.markdown('---')

# METAS OFICIALES DEL PROYECTO
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

MAPA_ACTIVIDADES_AICS = {
    '1.1': (
        'Actividad 1.1: Promoción de higiene y distribución de artículos'
        ' esenciales'
    ),
    '1.2': 'Actividad 1.2: Acceso a agua potable y mejora de sistemas WASH',
    '1.3': 'Actividad 1.3: Adaptación de instalaciones WASH para personas con discapacidad',
    '2.1': 'Actividad 2.1: Servicios de apoyo psicosocial y Espacios Amigables (CFS)',
    '2.2': 'Actividad 2.2: Talleres de prevención de violencia basada en género (VBG)',
    '2.3': 'Actividad 2.3: Medidas específicas de protección y prevención de casos',
    'r1a4': 'R1A4: Fortalecimiento de capacidades comunitarias (WASH/Dignidad)',
    'r1a5': 'R1A5: Sesiones informativas y de sensibilización comunitaria',
    'r2a2': 'R2A2: Gestión de casos y asistencia de protección personalizada',
    'r2a4': 'R2A4: Sesiones especializadas en VBG y protección de la niñez',
}

METAS_ACTIVIDADES_AICS = {
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


def clasificar_servicio(val):
    s = str(val).lower().strip()
    if 'orientacion_legal' in s or 'abogado' in s:
        return 'Orientación Legal'
    elif 'psicologo' in s or 'psico' in s:
        return 'APS Psicosocial'
    elif 'gestor' in s:
        return 'Gestoría de Caso'
    elif 'child friendly' in s or '2.3' in s:
        return 'Espacios Amigables (CFS)'
    return 'Gestoría de Caso'


# -----------------------------------------------------------------------------
# 2. CARGA DE DATOS DESDE EL EXCEL OFICIAL ACTUALIZADO
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_datos_excel(
    excel_path='BBDD SIGA AICS Noviembre_2026_tablero_.xlsx',
):
    if not os.path.exists(excel_path):
        st.warning(f'⚠️ No se encontró el archivo {excel_path} en la raíz.')
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(excel_path)
        sheet_name = (
            'group_beneficiario'
            if 'group_beneficiario' in xls.sheet_names
            else xls.sheet_names[0]
        )
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=5)
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

        # Clasificación estricta por id_resul oficial (R1 = WASH, R2 = Protección)
        id_resul_val = str(
            row.get('AICS - SISTEMA INTEGRAL DE G.id_resul') or ''
        ).strip().upper()
        resultado_raw = str(
            row.get('AICS - SISTEMA INTEGRAL DE G.Resultado:') or ''
        ).upper()

        if 'R1' in id_resul_val or 'WASH' in resultado_raw:
            sector = 'WASH'
        elif 'R2' in id_resul_val or 'PROTECCIÓN' in resultado_raw or 'PROTECCION' in resultado_raw:
            sector = 'Protección'
        else:
            sector = 'Protección' if 'PROTECCIÓN' in resultado_raw else 'WASH'

        actividad_texto = str(row.get('group_act.Actividad:') or '').strip()
        tipo_serv = clasificar_servicio(actividad_texto)
        id_unico = f'ID_{codigo_id}'

        val_sexo = str(row.get('Sexo') or 'Mujer').strip().title()
        if 'Hombre' in val_sexo or val_sexo == 'H':
            sexo = 'Hombre'
        elif 'Mujer' in val_sexo or val_sexo == 'M':
            sexo = 'Mujer'
        else:
            sexo = 'Otro'

        rango_etario = str(
            row.get('rango_etario') or '18 a 49 años'
        ).strip().title()

        val_disc = str(
            row.get('Persona con Discapacidad') or 'No'
        ).strip().lower()
        discapacidad = (
            'Sí'
            if any(
                x in val_disc for x in ['sí', 'si', 'yes', 'true', '1']
            )
            else 'No'
        )

        ind_val_raw = str(
            row.get('ID_indicador') or row.get('group_act.Indicador:') or '1.1'
        ).strip().lower()
        ind_val = '1.1'
        for k_ind in MAPA_ACTIVIDADES_AICS.keys():
            if k_ind in ind_val_raw:
                ind_val = k_ind
                break

        if '1.2' in actividad_texto or 'higiene' in actividad_texto.lower():
            ind_val = '1.1'
        elif '2.1' in actividad_texto and 'grupal' in actividad_texto.lower():
            ind_val = '2.3'
        elif '2.3' in actividad_texto or 'child friendly' in actividad_texto.lower():
            ind_val = '2.1'
        elif '2.5' in actividad_texto or 'legal' in actividad_texto.lower():
            ind_val = '2.3'

        try:
            val_u = row.get('BENEFICIARIOS UNICOS GENERAL') or 0
            val_unicos_gen = int(float(val_u))
            if val_unicos_gen != 1:
                val_unicos_gen = 0
        except Exception:
            val_unicos_gen = 0

        registros.append({
            '_id': row.get('_index', idx),
            'Fecha': fecha,
            'Estado': estado,
            'Municipio': muni,
            'Campamento': campamento,
            'Sector': sector,
            'Actividad_Texto': actividad_texto,
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
                else 'Todos'
            )
        )
    else:
        df['Mes_Reporte'] = 'Todos'
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

meses_unicos = sorted(
    [m for m in df_raw['Mes_Reporte'].unique() if m != 'Todos']
)
meses_disp = ['Todos'] + meses_unicos
mes_sel = st.sidebar.selectbox('Mes del Reporte:', meses_disp, index=0)

sexo_disp = ['Todos', 'Hombre', 'Mujer', 'Otro']
sexo_sel = st.sidebar.selectbox('Sexo del Participante:', sexo_disp, index=0)

rango_disp = ['Todos'] + sorted(df_raw['Rango_Etario'].unique().tolist())
rango_sel = st.sidebar.selectbox('Rango Etario:', rango_disp, index=0)

df_filtered = df_raw.copy()
if mes_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Mes_Reporte'] == mes_sel]
if sexo_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Sexo'] == sexo_sel]
if rango_sel != 'Todos':
    df_filtered = df_filtered[df_filtered['Rango_Etario'] == rango_sel]

# -----------------------------------------------------------------------------
# MÉTRICAS CLAVE
# -----------------------------------------------------------------------------
total_servicios = int(df_filtered['Servicios_Count'].sum())
total_unicos = int(df_filtered['Unicos_General'].sum())

pct_meta_servicios = (
    (total_servicios / META_PARTICIPANTES_SERVICIOS) * 100
    if META_PARTICIPANTES_SERVICIOS > 0
    else 0
)

df_unicos_rows = df_filtered[df_filtered['Unicos_General'] == 1]

conteo_sexo = (
    df_unicos_rows.groupby('Sexo')['Unicos_General'].sum()
    if not df_unicos_rows.empty
    else pd.Series()
)
total_mujeres = int(conteo_sexo.get('Mujer', 0))
total_hombres = int(conteo_sexo.get('Hombre', 0))
total_otro = int(conteo_sexo.get('Otro', 0))

conteo_disc = (
    df_unicos_rows.groupby('Discapacidad')['Unicos_General'].sum()
    if not df_unicos_rows.empty
    else pd.Series()
)
total_discapacidad = int(conteo_disc.get('Sí', 0))

# Métricas específicas validadas por Sector sobre los únicos
total_unicos_wash = int(
    df_unicos_rows[df_unicos_rows['Sector'] == 'WASH'][
        'Unicos_General'
    ].sum()
)
total_unicos_prot = int(
    df_unicos_rows[df_unicos_rows['Sector'] == 'Protección'][
        'Unicos_General'
    ].sum()
)

col1, col2, col3 = st.columns(3)
col1.metric('Total de Participantes (Servicios)', f'{total_servicios:,}')
col2.metric('Participantes Únicos Totales', f'{total_unicos:,}')
col3.metric(
    '% Alcance de la Meta (4.800 serv.)',
    f'{pct_meta_servicios:.2f}%',
    delta=f'{total_servicios:,} / {META_PARTICIPANTES_SERVICIOS:,}',
)

col_w, col_p = st.columns(2)
col_w.metric(
    'Participantes Únicos WASH (Resultado 1)', f'{total_unicos_wash:,}'
)
col_p.metric(
    'Participantes Únicos Protección (Resultado 2)', f'{total_unicos_prot:,}'
)

col_m, col_h, col_o, col_d = st.columns(4)
col_m.metric('Participantes Únicos: Mujeres', f'{total_mujeres:,}')
col_h.metric('Participantes Únicos: Hombres', f'{total_hombres:,}')
col_o.metric('Participantes Únicos: Otro', f'{total_otro:,}')
col_d.metric('Participantes con Discapacidad', f'{total_discapacidad:,}')

st.markdown('---')

# -----------------------------------------------------------------------------
# GRÁFICOS: RANGO ETARIO Y SEXO / MUNICIPIOS
# -----------------------------------------------------------------------------
g1, g2 = st.columns(2)

with g1:
    st.subheader('Participantes Únicos por Rango Etario y Sexo')
    if not df_unicos_rows.empty and 'Rango_Etario' in df_unicos_rows.columns:
        df_demo = (
            df_unicos_rows.groupby(['Rango_Etario', 'Sexo'])['Unicos_General']
            .sum()
            .reset_index(name='Cantidad')
        )

        orden_etario = {
            '0 A 4 Años': 1,
            '5 A 17 Años': 2,
            '18 A 49 Años': 3,
            '50 Años O Más': 4,
        }
        df_demo['Orden'] = (
            df_demo['Rango_Etario'].str.title().map(orden_etario).fillna(99)
        )
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
        st.info('No hay datos disponibles para los filtros seleccionados.')

with g2:
    st.subheader('Participantes Únicos por Municipio')
    if not df_unicos_rows.empty and 'Municipio' in df_unicos_rows.columns:
        df_muni = (
            df_unicos_rows.groupby(['Estado', 'Municipio'])['Unicos_General']
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
    location=[10.40, -66.90], zoom_start=10, tiles='OpenStreetMap'
)

if not df_unicos_rows.empty:
    muni_resumen = []
    for (est, mun), grupo in df_unicos_rows.groupby(['Estado', 'Municipio']):
        tot = int(grupo['Unicos_General'].sum())
        campamentos = sorted([
            c
            for c in grupo['Campamento'].dropna().unique()
            if c and c != 'No especificado'
        ])
        campamentos_str = '<br>'.join([f'- {c}' for c in campamentos])
        if not campamentos_str:
            campamentos_str = '- No especificado'

        muni_resumen.append({
            'Estado': est,
            'Municipio': mun,
            'Total_Unicos': tot,
            'Campamentos': campamentos_str,
        })

    df_mapa = pd.DataFrame(muni_resumen)

    for _, m_row in df_mapa.iterrows():
        est = m_row['Estado']
        mun = m_row['Municipio']
        tot = m_row['Total_Unicos']
        camps = m_row['Campamentos']
        coords = COORDENADAS_MUNICIPIOS.get(mun, [10.5, -66.9])

        popup_html = f"""
        <div style='font-family: Quicksand; font-size: 13px; width: 220px;'>
            <h4 style='color: {COLOR_AZUL_COOPI}; margin-bottom: 5px;'>{mun}</h4>
            <b>Estado:</b> {est}<br>
            <b>Participantes Únicos:</b> <b>{tot}</b><br>
            <hr style='margin: 5px 0;'>
            <b>Campamentos / Refugios:</b><br>
            {camps}
        </div>
        """
        folium.CircleMarker(
            location=coords,
            radius=min(tot * 1.5, 25) + 8,
            popup=folium.Popup(popup_html, max_width=250),
            color=COLOR_AZUL_COOPI,
            fill=True,
            fill_color=COLOR_AZUL_COOPI,
            fill_opacity=0.8,
        ).add_to(mapa)

st_folium(mapa, width='stretch', height=450)

st.markdown('---')

# -----------------------------------------------------------------------------
# CÁLCULO DINÁMICO EXCLUSIVO PARA ACTIVIDADES DEL PROYECTO
# -----------------------------------------------------------------------------
resultados_dinamicos = (
    df_raw.groupby('Indicador')['Unicos_General'].sum().to_dict()
)

todos_acts = []
for k, nombre_act in MAPA_ACTIVIDADES_AICS.items():
    res_val = int(resultados_dinamicos.get(k, 0))
    meta_val = METAS_ACTIVIDADES_AICS.get(k, {'meta': 100})['meta']
    tipo_meta = METAS_ACTIVIDADES_AICS.get(k, {'tipo': 'numero'})['tipo']

    if tipo_meta == 'porcentaje':
        alc = res_val if res_val <= meta_val else 100.0
    else:
        alc = (res_val / meta_val) * 100 if meta_val > 0 else 0

    todos_acts.append({
        'Codigo': k.upper(),
        'Actividad': nombre_act,
        'Resultado_Mes': res_val,
        'Meta': meta_val,
        '% Avance': f'{alc:.1f}%',
    })

summary_final = pd.DataFrame(todos_acts)
summary_final = summary_final.sort_values(by='Codigo', ascending=False)

# -----------------------------------------------------------------------------
# REPORTE Y COMPARATIVA: GRÁFICO DE BARRAS HORIZONTAL (ACTIVIDADES)
# -----------------------------------------------------------------------------
st.subheader('Alcance de Actividades del Proyecto (Resultado del Mes vs Meta)')

fig_ind = go.Figure()
fig_ind.add_trace(
    go.Bar(
        y=summary_final['Actividad'],
        x=summary_final['Resultado_Mes'],
        name='Resultado del Mes',
        orientation='h',
        text=summary_final['Resultado_Mes'],
        textposition='outside',
        marker_color=COLOR_VERDE_COOPI,
    )
)
fig_ind.add_trace(
    go.Bar(
        y=summary_final['Actividad'],
        x=summary_final['Meta'],
        name='Meta Oficial',
        orientation='h',
        text=summary_final['Meta'],
        textposition='outside',
        marker_color=COLOR_AZUL_COOPI,
    )
)

fig_ind.update_layout(
    barmode='group',
    title='Comparativa por Actividad: Resultado del Mes vs Meta',
    font=font_layout,
    xaxis_title='Cantidad / Porcentaje',
    yaxis_title='Actividad',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    height=650,
)

st.plotly_chart(fig_ind, width='stretch')

st.markdown('#### Detalle de Avance por Actividad')
st.dataframe(
    summary_final[['Codigo', 'Actividad', 'Resultado_Mes', 'Meta', '% Avance']],
    width='stretch',
    hide_index=True,
)

st.markdown('---')

# -----------------------------------------------------------------------------
# CAPÍTULO: RESULTADO DE PROTECCIÓN (Año 2026, Proyecto AICS)
# -----------------------------------------------------------------------------
st.subheader('Resultado de protección')

if not df_prot_kobo.empty:
    df_proteccion_2026 = (
        df_prot_kobo[df_prot_kobo['Fecha_DT'].dt.year == 2026].copy()
        if 'Fecha_DT' in df_prot_kobo.columns
        else df_prot_kobo.copy()
    )

    if not df_proteccion_2026.empty:
        total_casos_prot = len(df_proteccion_2026)
        total_unicos_prot = df_proteccion_2026['Case_ID'].nunique()

        col_p1, col_p2 = st.columns(2)
        col_p1.metric('Total de Casos', f'{total_casos_prot:,}')
        col_p2.metric('Participantes Únicos', f'{total_unicos_prot:,}')

        df_servicios_count = (
            df_proteccion_2026.groupby(
                'Tipo_Servicio_Proteccion', as_index=False
            )
            .agg(Cantidad_Casos=('Servicios_Count', 'sum'))
            .sort_values(by='Cantidad_Casos', ascending=False)
        )

        fig_prot = px.bar(
            df_servicios_count,
            x='Tipo_Servicio_Proteccion',
            y='Cantidad_Casos',
            text='Cantidad_Casos',
            color='Tipo_Servicio_Proteccion',
            color_discrete_sequence=PALETA_COOPI,
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
        st.info(
            'No hay registros de servicios de protección para el año 2026 bajo'
            ' el proyecto AICS.'
        )
else:
    st.info('No hay datos disponibles para el capítulo de protección.')

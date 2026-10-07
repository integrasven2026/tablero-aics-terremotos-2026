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
        # Extracción y conteo del grupo de metadatos Alfa (Participantes únicos y servicios)
        meta_alfa = row.get('group_metadatos_alfa', {})
        case_id_alfa = ''
        if isinstance(meta_alfa, dict):
            case_id_alfa = str(meta_alfa.get('case_id', '')).strip()
        elif isinstance(meta_alfa, list) and len(meta_alfa) > 0:
            case_id_alfa = str(meta_alfa[0].get('case_id', '')).strip()

        # Detección robusta de servicios de protección recorriendo todo el registro y texto completo
        tipo_servicio_proteccion = 'No especificado'
        row_str_completo = str(row).lower()

        # Buscar por coincidencias directas en claves o valores de los campos solicitados
        encontro_servicio = False
        for k, v in row.items():
            k_l = str(k).lower()
            v_l = str(v).lower()
            if any(term in k_l or term in v_l for term in ['gestor_coopi', 'gestor/a', 'abogado', 'oficial legal', 'orientacion_legal']):
                tipo_servicio_proteccion = '1. Protección General' if 'gestor' in k_l or 'gestor' in v_l else '2. Orientación Legal'
                encontro_servicio = True
                break
            elif any(term in k_l or term in v_l for term in ['psicologo_coopi', 'psicólogo', 'aps']):
                tipo_servicio_proteccion = '3. APS Psicosocial'
                encontro_servicio = True
                break

        if not encontro_servicio:
            if 'gestor' in row_str_completo or 'caso' in row_str_completo:
                tipo_servicio_proteccion = '1. Protección General'
            elif 'legal' in row_str_completo or 'abogado' in row_str_completo:
                tipo_servicio_proteccion = '2. Orientación Legal'
            elif 'psico' in row_str_completo:
                tipo_servicio_proteccion = '3. APS Psicosocial'

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

        estado_code = str(
            row.get('Estado')
            or row.get('estado')
            or row.get('group_datos_loc/Estado')
            or ''
        ).strip()
        estado = MAPA_ESTADOS.get(estado_code, estado_code or 'Distrito Capital')

        muni_code = str(
            row.get('Municipio')
            or row.get('municipio')
            or row.get('group_datos_loc/Municipio')
            or ''
        ).strip()
        muni = MAPA_MUNICIPIOS.get(muni_code, muni_code or 'Libertador')

        campamento = 'No especificado'
        for k, v in row.items():
            if not isinstance(v, (str, int, float, bool)) or v is None:
                continue
            k_l = str(k).lower()
            if 'comunidad' in k_l or 'refugio' in k_l or 'establecimiento' in k_l:
                val_str = str(v).strip()
                if val_str and val_str.lower() not in ['none', 'nan', '']:
                    campamento = val_str
                    break

        fecha = (
            row.get('Fecha de la Actividad:')
            or row.get('Fecha_de_la_Actividad')
            or row.get('fecha')
            or row.get('_submission_time')
        )

        cantidad_envio = 1
        for k, v in row.items():
            k_l = str(k).lower()
            if any(x in k_l for x in ['escriba el número', 'número de', 'numero de', 'num_personas', 'suma_total', 'cantidad', 'tot_pers']):
                try:
                    val_num = int(float(v))
                    if val_num > 0:
                        cantidad_envio = val_num
                        break
                except Exception:
                    pass

        ind_val = '1.1'
        encontrado = False
        for col_i, val_i in row.items():
            if not isinstance(val_i, (str, int, float, bool)) or val_i is None:
                continue
            col_str_l = str(col_i).lower()
            if 'indicador' in col_str_l or 'actividad' in col_str_l or 'resultado' in col_str_l:
                txt_ind = str(val_i).lower()
                for k_ind in MAPA_INDICADORES_AICS.keys():
                    if k_ind in txt_ind:
                        ind_val = k_ind.lower()
                        encontrado = True
                        break
                if encontrado:
                    break

        if not encontrado:
            for k, v in row.items():
                if isinstance(v, (str, int, float, bool)) and v is not None:
                    val_str = str(v).lower()
                    for k_ind in MAPA_INDICADORES_AICS.keys():
                        if k_ind in val_str:
                            ind_val = k_ind.lower()
                            encontrado = True
                            break
                    if encontrado:
                        break

        hombres_envio = 0
        mujeres_envio = 0
        for k, v in row.items():
            k_l = str(k).lower()
            if ('suma_h' in k_l or 'hombre' in k_l or 'masculino' in k_l) and 'count_' not in k_l:
                try:
                    hombres_envio += int(float(v))
                except Exception:
                    pass
            elif ('suma_n' in k_l or 'suma_m' in k_l or 'mujer' in k_l or 'femenino' in k_l) and 'count_' not in k_l:
                try:
                    mujeres_envio += int(float(v))
                except Exception:
                    pass

        beneficiarios = row.get('group_beneficiario', [])
        if isinstance(beneficiarios, list) and len(beneficiarios) > 0:
            for idx, b in enumerate(beneficiarios):
                if not isinstance(b, dict):
                    continue
                cid = ''
                sexo_val = ''
                rango_val = ''
                disc_val = 'No'

                for k, v in b.items():
                    if not isinstance(v, (str, int, float, bool)) or v is None:
                        continue
                    k_str = str(k)
                    k_lower = k_str.lower()
                    if 'codigoid' in k_lower or 'documento' in k_lower:
                        cid = str(v).strip()
                    elif k_lower == 'sexo' or k_lower.endswith('/sexo'):
                        sexo_val = str(v).strip()
                    elif k_lower == 'rango_etario' or k_lower.endswith('/rango_etario') or 'resul_edad' in k_lower:
                        rango_val = str(v).strip()
                    elif ('discapacidad' in k_lower or k_lower.endswith('persona_con_discapacidad')) and 'count_' not in k_lower:
                        disc_val = str(v).strip()

                if not sexo_val:
                    for k, v in b.items():
                        if isinstance(v, (str, int, float, bool)) and v is not None:
                            k_l = str(k).lower()
                            if 'sexo' in k_l and 'id_' not in k_l and 'count_' not in k_l:
                                sexo_val = str(v).strip()
                                break
                if not rango_val:
                    for k, v in b.items():
                        if isinstance(v, (str, int, float, bool)) and v is not None:
                            k_l = str(k).lower()
                            if ('rango_etario' in k_l or 'edad' in k_l) and 'count_' not in k_l:
                                rango_val = str(v).strip()
                                break

                lista_sexos = [s.strip() for s in sexo_val.split(',') if s.strip()]
                lista_rangos = [r.strip() for r in rango_val.split(',') if r.strip()]
                max_len = max(len(lista_sexos), len(lista_rangos), 1)

                for sub_i in range(max_len):
                    s_item = (
                        lista_sexos[sub_i]
                        if sub_i < len(lista_sexos)
                        else (lista_sexos[0] if lista_sexos else 'Mujer')
                    )
                    r_item = (
                        lista_rangos[sub_i]
                        if sub_i < len(lista_rangos)
                        else (lista_rangos[0] if lista_rangos else '18 A 49 Años')
                    )

                    id_unico = (
                        f'ID_{cid}_{sub_i}'
                        if cid and cid.lower() not in ['none', '', '0', 'nan']
                        else (f'ALFA_{case_id_alfa}_{sub_i}' if case_id_alfa else f"ROW_{row.get('_id')}_{idx}_{sub_i}")
                    )

                    sexo = normalizar_sexo(s_item)
                    rango_etario = limpiar_texto(r_item)
                    discapacidad = normalizar_discapacidad(disc_val)

                    registros.append({
                        '_id': row.get('_id'),
                        'Fecha': fecha,
                        'Estado': estado,
                        'Municipio': muni,
                        'Campamento': campamento,
                        'Sector': sector,
                        'Tipo_Servicio_Proteccion': tipo_servicio_proteccion,
                        'ID_Unico': id_unico,
                        'Sexo': sexo,
                        'Rango_Etario': rango_etario,
                        'Discapacidad': discapacidad,
                        'Indicador': ind_val,
                        'Ponderacion': 1,
                    })
        else:
            id_base = f'ALFA_{case_id_alfa}' if case_id_alfa else f"ROW_{row.get('_id')}"
            if hombres_envio > 0 or mujeres_envio > 0:
                if hombres_envio > 0:
                    registros.append({
                        '_id': row.get('_id'),
                        'Fecha': fecha,
                        'Estado': estado,
                        'Municipio': muni,
                        'Campamento': campamento,
                        'Sector': sector,
                        'Tipo_Servicio_Proteccion': tipo_servicio_proteccion,
                        'ID_Unico': f'{id_base}_H',
                        'Sexo': 'Hombre',
                        'Rango_Etario': '5 A 17 Años' if ind_val == '2.1' else '18 A 49 Años',
                        'Discapacidad': 'No',
                        'Indicador': ind_val,
                        'Ponderacion': hombres_envio,
                    })
                if mujeres_envio > 0:
                    registros.append({
                        '_id': row.get('_id'),
                        'Fecha': fecha,
                        'Estado': estado,
                        'Municipio': muni,
                        'Campamento': campamento,
                        'Sector': sector,
                        'Tipo_Servicio_Proteccion': tipo_servicio_proteccion,
                        'ID_Unico': f'{id_base}_M',
                        'Sexo': 'Mujer',
                        'Rango_Etario': '5 A 17 Años' if ind_val == '2.1' else '18 A 49 Años',
                        'Discapacidad': 'No',
                        'Indicador': ind_val,
                        'Ponderacion': mujeres_envio,
                    })
            else:
                registros.append({
                    '_id': row.get('_id'),
                    'Fecha': fecha,
                    'Estado': estado,
                    'Municipio': muni,
                    'Campamento': campamento,
                    'Sector': sector,
                    'Tipo_Servicio_Proteccion': tipo_servicio_proteccion,
                    'ID_Unico': f'{id_base}_0',
                    'Sexo': 'Mujer',
                    'Rango_Etario': '5 A 17 Años' if ind_val == '2.1' else '18 A 49 Años',
                    'Discapacidad': 'No',
                    'Indicador': ind_val,
                    'Ponderacion': cantidad_envio,
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
        '⚠ No se pudieron cargar datos desde la API de KoboToolbox. Verifica tu'
        ' token y conexión.'
    )
    st.stop()

meses_disp = ['Todos'] + sorted(
    [m for m in df_raw['Mes_Reporte'].unique() if m != 'Sin Fecha']
)
mes_sel = st.sidebar.selectbox('Mes del Reporte:', meses_disp)

sexo_disp = ['Todos', 'Hombre', 'Mujer', 'Otro']
sexo_sel = st.sidebar.selectbox('Sexo del Participante:', sexo_disp)

rango_disp = ['Todos'] + sorted(df_raw['Rango_Etario'].unique().tolist())
rango_sel = st.sidebar.selectbox('Rango Etario:', rango_disp)

# Aplicar filtros globales para métricas y gráficos demográficos
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
total_servicios = int(df_filtered['Ponderacion'].sum())
df_unicos = df_filtered.drop_duplicates(subset=['ID_Unico'])
total_unicos = int(df_unicos['Ponderacion'].sum())
pct_meta = (
    (total_unicos / META_PARTICIPANTES_UNICOS) * 100
    if META_PARTICIPANTES_UNICOS > 0
    else 0
)

conteo_sexo = df_unicos.groupby('Sexo')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_mujeres = int(conteo_sexo.get('Mujer', 0))
total_hombres = int(conteo_sexo.get('Hombre', 0))

conteo_disc = df_unicos.groupby('Discapacidad')['Ponderacion'].sum() if not df_unicos.empty else pd.Series()
total_discapacidad = int(conteo_disc.get('Sí', 0))

col1, col2, col3 = st.columns(3)
col1.metric('Total de Participantes (Servicios)', f'{total_servicios:,}')
col2.metric('Participantes Únicos', f'{total_unicos:,}')
col3.metric(
    '% Alcance de la Meta (4.906 pers.)',
    f'{pct_meta:.2f}%',
    delta=f'{total_unicos:,} / {META_PARTICIPANTES_UNICOS:,}',
)

col_m, col_h, col_d = st.columns(3)
col_m.metric('Participantes Únicos: Mujeres', f'{total_mujeres:,}')
col_h.metric('Participantes Únicos: Hombres', f'{total_hombres:,}')
col_d.metric('Participantes con Discapacidad', f'{total_discapacidad:,}')

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
            xaxis={'categoryorder': 'array', 'categoryarray': ['0 A 4 Años', '5 A 17 Años', '18 A 49 Años', '50 Años O Más']}
        )
        st.plotly_chart(fig_demo, width='stretch')
    else:
        st.info('No hay datos disponibles para los filtros seleccionados.')

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

if not df_unicos.empty:
    muni_resumen = []
    for (est, mun), grupo in df_unicos.groupby(['Estado', 'Municipio']):
        tot = int(grupo['Ponderacion'].sum())
        campamentos = sorted([c for c in grupo['Campamento'].dropna().unique() if c and c != 'No especificado'])
        campamentos_str = "<br>".join([f"- {c}" for c in campamentos])
        if not campamentos_str:
            campamentos_str = "- No especificado"
            
        muni_resumen.append({
            'Estado': est,
            'Municipio': mun,
            'Total_Unicos': tot,
            'Campamentos': campamentos_str
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
# REPORTE Y COMPARATIVA: GRÁFICO DE BARRAS HORIZONTAL (INDICADORES Y ACTIVIDADES)
# -----------------------------------------------------------------------------
st.subheader('Alcance de Indicadores y Actividades (Resultado del Mes vs Meta)')

df_ind_base = df_raw.copy()
if mes_sel != 'Todos':
    df_ind_base = df_ind_base[df_ind_base['Mes_Reporte'] == mes_sel]
if sexo_sel != 'Todos':
    df_ind_base = df_ind_base[df_ind_base['Sexo'] == sexo_sel]
if rango_sel != 'Todos':
    df_ind_base = df_ind_base[df_ind_base['Rango_Etario'] == rango_sel]

if len(df_ind_base) > 0:
    records_ind = []
    for _, row in df_ind_base.iterrows():
        cod = str(row.get('Indicador', '1.1')).strip().lower()
        records_ind.append({
            'Codigo': cod,
            'Indicador': MAPA_INDICADORES_AICS.get(cod, f'Indicador/Actividad {cod.upper()}'),
            'Ponderacion': row.get('Ponderacion', 1),
        })

    df_ind = pd.DataFrame(records_ind)
    summary_ind = (
        df_ind.groupby(['Codigo', 'Indicador'])['Ponderacion']
        .sum()
        .reset_index(name='Resultado_Mes')
    )

    todos_inds = []
    for k, nombre in MAPA_INDICADORES_AICS.items():
        match = summary_ind[summary_ind['Codigo'] == k]
        res_val = int(match['Resultado_Mes'].values[0]) if not match.empty else 0
        meta_val = METAS_INDICADORES_AICS.get(k, {'meta': 100})['meta']
        alc = (res_val / meta_val) * 100 if meta_val > 0 else 0
        todos_inds.append({
            'Codigo': k.upper(),
            'Indicador': nombre,
            'Resultado_Mes': res_val,
            'Meta': meta_val,
            '% Avance': f'{alc:.1f}%'
        })

    summary_final = pd.DataFrame(todos_inds)
    summary_final = summary_final.sort_values(by='Codigo', ascending=False)

    fig_ind = go.Figure()
    fig_ind.add_trace(go.Bar(
        y=summary_final['Indicador'],
        x=summary_final['Resultado_Mes'],
        name='Resultado del Mes',
        orientation='h',
        text=summary_final['Resultado_Mes'],
        textposition='outside',
        marker_color=COLOR_VERDE_COOPI
    ))
    fig_ind.add_trace(go.Bar(
        y=summary_final['Indicador'],
        x=summary_final['Meta'],
        name='Meta Oficial',
        orientation='h',
        text=summary_final['Meta'],
        textposition='outside',
        marker_color=COLOR_AZUL_COOPI
    ))

    fig_ind.update_layout(
        barmode='group',
        title='Comparativa por Indicador / Actividad: Resultado del Mes vs Meta',
        font=font_layout,
        xaxis_title='Cantidad / Porcentaje',
        yaxis_title='Indicador / Actividad',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=650
    )
    
    st.plotly_chart(fig_ind, width='stretch')

    st.markdown('#### Detalle de Avance por Indicador y Actividad')
    st.dataframe(summary_final[['Codigo', 'Indicador', 'Resultado_Mes', 'Meta', '% Avance']], width='stretch', hide_index=True)
else:
    st.info(
        'No hay registros suficientes para calcular los indicadores con los'
        ' filtros actuales.'
    )

st.markdown('---')

# -----------------------------------------------------------------------------
# CAPÍTULO: SERVICIOS DE PROTECCIÓN (UBICADO AL FINAL)
# -----------------------------------------------------------------------------
st.subheader('Capítulo de Servicios de Protección')

if not df_filtered.empty and 'Tipo_Servicio_Proteccion' in df_filtered.columns:
    df_proteccion = df_filtered[df_filtered['Tipo_Servicio_Proteccion'] != 'No especificado']
    
    total_casos_proteccion = int(df_proteccion['Ponderacion'].sum()) if not df_proteccion.empty else 0
    st.metric('Total de Casos de Protección Atendidos', f'{total_casos_proteccion:,}')

    if not df_proteccion.empty:
        df_servicios_count = (
            df_proteccion.groupby('Tipo_Servicio_Proteccion')['Ponderacion']
            .sum()
            .reset_index(name='Cantidad_Casos')
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
            yaxis_title='Cantidad de Casos',
        )
        st.plotly_chart(fig_prot, width='stretch')
    else:
        st.info('No hay registros de servicios de protección bajo los filtros actuales.')
else:
    st.info('No hay datos disponibles para el capítulo de protección.')

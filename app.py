# -----------------------------------------------------------------------------
# ACTIVIDADES OFICIALES SEGÚN LA BASE DE DATOS
# -----------------------------------------------------------------------------
MAPA_ACTIVIDADES_AICS = {
    'Actividad 1.2: Promoción de buenas prácticas de higiene y tutela de la dignidad': {
        'codigo': '1.2',
        'meta': 2000,
        'tipo': 'numero',
    },
    'Actividad 2.1: Servicios de apoyo psicosocial (grupal)': {
        'codigo': '2.1 (Grupal)',
        'meta': 1580,
        'tipo': 'numero',
    },
    'Actividad 2.1: Servicios de apoyo psicosocial (individual)': {
        'codigo': '2.1 (Ind.)',
        'meta': 300,
        'tipo': 'numero',
    },
    'Actividad 2.2: Identificación y gestión de casos y asistencia de protección personalizada para las personas más vulnerables alojadas en centros de acogida temporales seleccionados.': {
        'codigo': '2.2',
        'meta': 195,
        'tipo': 'numero',
    },
    'Actividad 2.3: Creación de espacios a medida de los niños (Child Friendly Spaces)': {
        'codigo': '2.3',
        'meta': 4134,
        'tipo': 'numero',
    },
    'Actividad 2.5: Asistencia legal para la obtención de documentos de identidad': {
        'codigo': '2.5',
        'meta': 500,
        'tipo': 'numero',
    },
}

# -----------------------------------------------------------------------------
# CÁLCULO DINÁMICO EXCLUSIVO PARA ACTIVIDADES DEL PROYECTO
# -----------------------------------------------------------------------------
# Agrupamos por la columna exacta de la base de datos 'Actividad_Texto' (que almacena group_act.Actividad:)
resultados_dinamicos = (
    df_filtered[df_filtered['Unicos_General'] == 1]
    .groupby('Actividad_Texto')['Unicos_General']
    .sum()
    .to_dict()
)

todos_acts = []
for nombre_act, config in MAPA_ACTIVIDADES_AICS.items():
  res_val = int(resultados_dinamicos.get(nombre_act, 0))
  meta_val = config['meta']
  tipo_meta = config['tipo']

  if tipo_meta == 'porcentaje':
    alc = res_val if res_val <= meta_val else 100.0
  else:
    alc = (res_val / meta_val) * 100 if meta_val > 0 else 0

  todos_acts.append({
      'Codigo': config['codigo'],
      'Actividad': nombre_act,
      'Resultado_Mes': res_val,
      'Meta': meta_val,
      '% Avance': f'{alc:.1f}%',
  })

summary_final = pd.DataFrame(todos_acts)

# -----------------------------------------------------------------------------
# REPORTE Y TABLA DE AVANCE POR ACTIVIDAD
# -----------------------------------------------------------------------------
st.subheader('Detalle de Avance por Actividad')
st.dataframe(
    summary_final[['Codigo', 'Actividad', 'Resultado_Mes', 'Meta', '% Avance']],
    width='stretch',
    hide_index=True,
)

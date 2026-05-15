import pandas as pd
import re

df = pd.read_csv('base de datos de alumnos de pregrado.csv', dtype=str)
df.columns = [re.sub(r'[^\x00-\x7F]+', 'o', c) for c in df.columns]

# Mapeo de meses
MES_MAP = {'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04', 'MAYO': '05', 'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08', 'SETIEMBRE': '09', 'SEPTIEMBRE': '09', 'OCTUBRE': '10', 'NOVIEMBRE': '11', 'DICIEMBRE': '12'}

def extract_period(row):
    p = str(row['Periodo_SAP']).strip().upper()
    parts = p.split('-')
    mes_str = parts[-1] if len(parts) > 1 else p
    mes_num = MES_MAP.get(mes_str, '00')
    anio_col = [c for c in df.columns if len(c) <= 3 and c.startswith('A')][0]
    return f"{row[anio_col]}-{mes_num}"

df['Periodo_Real'] = df.apply(extract_period, axis=1)

# Periodo Máximo Detectado
ULTIMO_PERIODO = df['Periodo_Real'].max()
print(f"Ultimo periodo detectado: {ULTIMO_PERIODO}")

# Filtrar solo matricula activa para el conteo de 'estudiando'
df_activo = df[df['Estado_curso'] == 'CURSADO'].copy()

resumen = df.groupby(['Codigo_Plan_SAP', 'Programa']).agg(
    Historico_Alumnos=('DNI', 'nunique')
).reset_index()

# Contar alumnos activos en el último periodo
activos_last = df_activo[df_activo['Periodo_Real'] == ULTIMO_PERIODO].groupby(['Codigo_Plan_SAP', 'Programa'])['DNI'].nunique().reset_index()
activos_last.columns = ['Codigo_Plan_SAP', 'Programa', 'Alumnos_Actuamente_Estudiando']

resumen = pd.merge(resumen, activos_last, on=['Codigo_Plan_SAP', 'Programa'], how='left').fillna(0)
resumen['Alumnos_Actuamente_Estudiando'] = resumen['Alumnos_Actuamente_Estudiando'].astype(int)

resumen['Estado_Plan'] = resumen['Alumnos_Actuamente_Estudiando'].apply(lambda x: 'Vigente' if x > 0 else 'Cerrado/Sin Matrícula')

# Ordenar por carrera y estado
resumen = resumen.sort_values(['Codigo_Plan_SAP', 'Alumnos_Actuamente_Estudiando'], ascending=[True, False])

resumen.to_csv('estado_actual_planes_sap.csv', index=False, encoding='utf-8-sig')
print("Reporte generado: estado_actual_planes_sap.csv")

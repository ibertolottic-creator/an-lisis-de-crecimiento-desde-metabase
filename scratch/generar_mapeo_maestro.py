import pandas as pd
import re

df = pd.read_csv('base de datos de alumnos de pregrado.csv', dtype=str)
df.columns = [re.sub(r'[^\x00-\x7F]+', 'o', c) for c in df.columns]

MES_MAP = {'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04', 'MAYO': '05', 'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08', 'SETIEMBRE': '09', 'SEPTIEMBRE': '09', 'OCTUBRE': '10', 'NOVIEMBRE': '11', 'DICIEMBRE': '12'}

def extract_period(row):
    p = str(row['Periodo_SAP']).strip().upper()
    parts = p.split('-')
    mes_str = parts[-1] if len(parts) > 1 else p
    mes_num = MES_MAP.get(mes_str, '00')
    anio_col = [c for c in df.columns if len(c) <= 3 and c.startswith('A')][0]
    return f"{row[anio_col]}-{mes_num}"

df['Periodo_Real'] = df.apply(extract_period, axis=1)

def detect_modalidad(name):
    name = str(name).upper()
    if 'A DISTANCIA' in name: return 'Distancia'
    if '70/30' in name: return 'Semipresencial'
    return 'Regular'

resumen = df.groupby(['Codigo_Plan_SAP', 'Programa']).agg(
    Cant_Alumnos=('DNI', 'nunique'),
    Primer_Mes=('Periodo_Real', 'min'),
    Ultimo_Mes=('Periodo_Real', 'max')
).reset_index()

resumen['Modalidad'] = resumen['Programa'].apply(detect_modalidad)
resumen = resumen.sort_values(['Codigo_Plan_SAP', 'Primer_Mes'])

resumen.to_csv('mapeo_maestro_programas.csv', index=False, encoding='utf-8-sig')

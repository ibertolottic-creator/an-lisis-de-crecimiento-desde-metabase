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

# Usamos Mayo 2026 como mes de corte (según indicación del usuario)
MES_CORTE = '2026-05'
print(f"Mes de corte para vigencia: {MES_CORTE}")

df_activo = df[df['Estado_curso'] == 'CURSADO'].copy()

resumen = df.groupby(['Codigo_Plan_SAP', 'Programa']).agg(
    Historico_Total_DNI=('DNI', 'nunique'),
    Primer_Registro=('Periodo_Real', 'min'),
    Ultimo_Registro=('Periodo_Real', 'max')
).reset_index()

activos_mayo = df_activo[df_activo['Periodo_Real'] == MES_CORTE].groupby(['Codigo_Plan_SAP', 'Programa'])['DNI'].nunique().reset_index()
activos_mayo.columns = ['Codigo_Plan_SAP', 'Programa', 'Alumnos_Activos_Mayo_2026']

resumen = pd.merge(resumen, activos_mayo, on=['Codigo_Plan_SAP', 'Programa'], how='left').fillna(0)
resumen['Alumnos_Activos_Mayo_2026'] = resumen['Alumnos_Activos_Mayo_2026'].astype(int)

resumen['Vigencia'] = resumen['Alumnos_Activos_Mayo_2026'].apply(lambda x: 'ACTIVO' if x > 0 else 'CERRADO / SIN MATRÍCULA')

resumen = resumen.sort_values(['Alumnos_Activos_Mayo_2026', 'Historico_Total_DNI'], ascending=False)

resumen.to_csv('reporte_vigencia_planes.csv', index=False, encoding='utf-8-sig')

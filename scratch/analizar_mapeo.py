import pandas as pd
import re
import os

print("Cargando base de datos...")
df = pd.read_csv('base de datos de alumnos de pregrado.csv', dtype=str)
df.columns = [re.sub(r'[^\x00-\x7F]+', 'o', c) for c in df.columns]

# Mapeo de meses
MES_MAP = {
    'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04',
    'MAYO': '05', 'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08',
    'SETIEMBRE': '09', 'SEPTIEMBRE': '09', 'OCTUBRE': '10', 
    'NOVIEMBRE': '11', 'DICIEMBRE': '12'
}

def extract_period(row):
    p = str(row['Periodo_SAP']).strip().upper()
    parts = p.split('-')
    mes_str = parts[-1] if len(parts) > 1 else p
    mes_num = MES_MAP.get(mes_str, '00')
    # Manejar el nombre de la columna Año que fue limpiado a 'Ao' o similar
    # Buscamos la columna que tenga 2 letras y empiece con A
    anio_col = [c for c in df.columns if len(c) <= 3 and c.startswith('A')][0]
    return f"{row[anio_col]}-{mes_num}"

print("Procesando periodos...")
df['Periodo_Real'] = df.apply(extract_period, axis=1)

print("Agrupando datos...")
resumen = df.groupby(['Codigo_Plan_SAP', 'Programa']).agg(
    Cant_Alumnos=('DNI', 'nunique'),
    Primer_Mes=('Periodo_Real', 'min'),
    Ultimo_Mes=('Periodo_Real', 'max')
).reset_index()

# Ordenar por Código y luego por historia
resumen = resumen.sort_values(['Codigo_Plan_SAP', 'Primer_Mes'])

# Guardar resultado
output_file = 'mapeo_historico_programas.csv'
resumen.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"Resultado guardado en {output_file}")

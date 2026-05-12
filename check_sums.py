import pandas as pd

df = pd.read_csv('Cuadro_Mando_Pregrado_Calculado.csv')
df_grouped = df.groupby('Periodo_Real').sum(numeric_only=True)

df_grouped['Suma_3_Grupos'] = df_grouped['Admitidos Matriculados'] + df_grouped['Recuperados'] + df_grouped['Retenidos (1m)']
df_grouped['Diferencia'] = df_grouped['Estudiantes matrí. TOTAL'] - df_grouped['Suma_3_Grupos']

print(df_grouped[['Estudiantes matrí. TOTAL', 'Suma_3_Grupos', 'Diferencia']].tail(10))

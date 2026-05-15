import pandas as pd
import os

df = pd.read_csv("Cuadro_Mando_Pregrado_Calculado.csv")
df_cursos = pd.read_csv("Asignaturas_Desaprobados_Historico.csv")

print("--- Programas en Cuadro_Mando_Pregrado_Calculado.csv (df) ---")
programas_df = sorted(df['Programa'].unique().tolist())
for p in programas_df:
    if "DERECHO" in p.upper():
        print(f"Match: {p}")

print("\n--- Programas en Asignaturas_Desaprobados_Historico.csv (df_cursos) ---")
programas_cursos = sorted(df_cursos['Programa_Base'].unique().tolist())
for p in programas_cursos:
    if "DERECHO" in p.upper():
        print(f"Match: {p}")

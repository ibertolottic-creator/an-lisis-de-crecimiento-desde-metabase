import pandas as pd
import numpy as np
import re

def clean_program_name(name):
    if not isinstance(name, str):
        return str(name)
    name = re.sub(r'\s*-\s*\(A DISTANCIA AP\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*\(70/30 AP\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*\(2DA ESPECIALIDAD\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(A DISTANCIA\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(PAT A DISTANCIA\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*HISTORICO', '', name, flags=re.IGNORECASE)
    return name.strip()

# Mapping for months to ensure chronological sort
MES_MAP = {
    'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04',
    'MAYO': '05', 'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08',
    'SETIEMBRE': '09', 'SEPTIEMBRE': '09', 'OCTUBRE': '10', 
    'NOVIEMBRE': '11', 'DICIEMBRE': '12'
}

def extract_period(row, year_col):
    year = str(row[year_col]).strip()
    period_sap = str(row['Periodo_SAP']).strip()
    if year == 'nan' or period_sap == 'nan':
        return None
    
    parts = period_sap.split('-')
    mes_str = parts[-1].upper() if len(parts) > 1 else period_sap.upper()
    mes_num = MES_MAP.get(mes_str, '00')
    return f"{year}-{mes_num}"

def extract_month_name(row):
    period_sap = str(row['Periodo_SAP']).strip()
    parts = period_sap.split('-')
    return parts[-1].capitalize() if len(parts) > 1 else period_sap.capitalize()

def process_data(input_csv, output_pregrado, output_posgrado):
    print(f"Leyendo datos desde {input_csv}...")
    df = pd.read_csv(input_csv, dtype={
        'Matricula': str, 
        'DNI': str, 
        'Periodio_Admision': str, 
        'Ultima_inscripcion': str
    })
    
    year_col = [c for c in df.columns if 'A' in c and 'o' in c and len(c)<=4][0]
    
    print("Limpiando y normalizando programas...")
    df['Programa_Base'] = df['Programa'].apply(clean_program_name)
    
    print("Filtrando matrícula activa (Estado_curso == 'CURSADO')...")
    df_activos = df[df['Estado_curso'] == 'CURSADO'].copy()
    
    # Generate Periodo_Real for chronological sorting
    df_activos['Periodo_Real'] = df_activos.apply(lambda row: extract_period(row, year_col), axis=1)
    df_activos['Mes_Nombre'] = df_activos.apply(extract_month_name, axis=1)
    df_activos['Año'] = df_activos[year_col]
    
    # Calculate grade metrics per course row
    df_activos['Nota_Num'] = pd.to_numeric(df_activos['Nota'], errors='coerce').fillna(0)
    df_activos['Desaprobado'] = (df_activos['Nota_Num'] < 11).astype(int)
    
    print("Agrupando datos a nivel de alumno y mes...")
    student_month = df_activos.groupby(['Periodo_Real', 'Año', 'Mes_Nombre', 'Programa_Base', 'DNI']).agg({
        'Periodio_Admision': 'first',
        'Modalidad_Asignatura': 'first', 
        'Ciclo_Estudiante': 'first',
        'Egresado': 'max',
        'Nota_Num': 'mean', 
        'Desaprobado': 'sum',
        'Estado_alumno_Original': 'first',
        'Convalidado': 'first'
    }).reset_index()

    meses_orden = sorted(student_month['Periodo_Real'].dropna().unique())
    student_month['Nivel'] = student_month['Programa_Base'].apply(
        lambda x: 'Posgrado' if 'MAESTR' in str(x).upper() else 'Pregrado'
    )
    
    # Extract courses metrics globally before loop
    print("Calculando asignaturas con mayor reprobación...")
    df_cursos = df_activos.groupby(['Año', 'Mes_Nombre', 'Programa_Base', 'Asignatura']).agg({
        'Desaprobado': 'sum',
        'DNI': 'nunique'
    }).reset_index()
    df_cursos.rename(columns={'DNI': 'Total_Alumnos'}, inplace=True)
    df_cursos['Tasa_Desaprobados'] = (df_cursos['Desaprobado'] / df_cursos['Total_Alumnos']).round(4)
    df_cursos.to_csv("Asignaturas_Desaprobados_Historico.csv", index=False, encoding='utf-8-sig')

    resultados = []
    programas = student_month['Programa_Base'].unique()
    print(f"Procesando {len(programas)} programas a través de {len(meses_orden)} periodos cronológicos...")
    
    for prog in programas:
        df_prog = student_month[student_month['Programa_Base'] == prog].copy()
        
        alumnos_historico = set()
        alumnos_mes_anterior = set()
        egresados_historicos = set()
        ausencias = {} 
        historial_sets = []
        
        for mes_idx, periodo_real in enumerate(meses_orden):
            df_mes = df_prog[df_prog['Periodo_Real'] == periodo_real]
            alumnos_mes_actual = set(df_mes['DNI'].unique())
            
            if len(alumnos_mes_actual) == 0 and len(alumnos_historico) == 0:
                historial_sets.append(set())
                continue
                
            historial_sets.append(alumnos_mes_actual)
                
            egresados_mes_actual = set(df_mes[df_mes['Egresado'] == 'SI']['DNI'].unique())
            egresados_historicos.update(egresados_mes_actual)
            
            nuevos = alumnos_mes_actual - alumnos_historico
            admitidos_matriculados = len(nuevos)
            
            recuperados_set = (alumnos_mes_actual & alumnos_historico) - alumnos_mes_anterior
            recuperados = len(recuperados_set)
            
            dnis_activos = alumnos_historico - egresados_historicos
            riesgo_1 = 0
            riesgo_2 = 0
            temprana = 0
            tardia = 0
            
            for dni in dnis_activos:
                if dni in alumnos_mes_actual:
                    ausencias[dni] = 0 
                else:
                    ausencias[dni] = ausencias.get(dni, 0) + 1
                    meses_fuera = ausencias[dni]
                    if meses_fuera == 1:
                        riesgo_1 += 1
                    elif meses_fuera == 2:
                        riesgo_2 += 1
                    elif meses_fuera >= 3 and meses_fuera <= 6:
                        temprana += 1
                    elif meses_fuera > 6:
                        tardia += 1
            
            # Retenidos Continuos (Intersecciones)
            retenidos_1m = retenidos_3m = retenidos_6m = retenidos_12m = 0
            if len(historial_sets) >= 2:
                retenidos_1m = len(alumnos_mes_actual.intersection(historial_sets[-2]))
            if len(historial_sets) >= 3:
                s3 = alumnos_mes_actual
                for s in historial_sets[-3:]:
                    s3 = s3.intersection(s)
                retenidos_3m = len(s3)
            if len(historial_sets) >= 6:
                s6 = alumnos_mes_actual
                for s in historial_sets[-6:]:
                    s6 = s6.intersection(s)
                retenidos_6m = len(s6)
            if len(historial_sets) >= 12:
                s12 = alumnos_mes_actual
                for s in historial_sets[-12:]:
                    s12 = s12.intersection(s)
                retenidos_12m = len(s12)
            
            # Calcular origen de los nuevos
            df_nuevos = df_mes[df_mes['DNI'].isin(nuevos)]
            nuevos_traslados = df_nuevos[df_nuevos['Estado_alumno_Original'].str.contains('TRASLADO', na=False, case=False)]['DNI'].nunique()
            nuevos_convalidados = df_nuevos[(df_nuevos['Estado_alumno_Original'].str.contains('CONVALIDA', na=False, case=False)) | (df_nuevos['Convalidado'] == 'SI')]['DNI'].nunique()
            
            año_actual = df_mes['Año'].iloc[0] if not df_mes.empty else periodo_real.split('-')[0]
            mes_nombre = df_mes['Mes_Nombre'].iloc[0] if not df_mes.empty else "N/A"
            
            mat_distancia = df_mes[df_mes['Modalidad_Asignatura'].str.contains('VIRTUAL|DISTANCIA', case=False, na=False)]['DNI'].nunique()
            mat_presencial = df_mes[df_mes['Modalidad_Asignatura'].str.contains('PRESENCIAL', case=False, na=False)]['DNI'].nunique()
            total_matriculados = len(alumnos_mes_actual)
            
            resultados.append({
                'Periodo_Real': periodo_real,
                'Año': año_actual,
                'Mes': mes_nombre,
                'Programa': prog,
                'Nivel': df_prog['Nivel'].iloc[0] if not df_prog.empty else "Desconocido",
                'Egresados': len(egresados_mes_actual),
                'Admitidos Matriculados': admitidos_matriculados,
                'Nuevos Traslados': nuevos_traslados,
                'Nuevos Convalidados': nuevos_convalidados,
                'Recuperados': recuperados,
                'Riesgo Deserción (1m)': riesgo_1,
                'Riesgo Deserción (2m)': riesgo_2,
                'Deserción Temprana (3-6m)': temprana,
                'Deserción Tardía (>6m)': tardia,
                'Retenidos (1m)': retenidos_1m,
                'Retenidos (3m)': retenidos_3m,
                'Retenidos (6m)': retenidos_6m,
                'Retenidos (12m)': retenidos_12m,
                'Matríc. regular a Distancia': mat_distancia,
                'Matríc. regular Presencial': mat_presencial,
                'Estudiantes matrí. TOTAL': total_matriculados
            })
            
            alumnos_historico.update(alumnos_mes_actual)
            alumnos_mes_anterior = alumnos_mes_actual
            
    df_res = pd.DataFrame(resultados)
    if len(df_res) == 0:
        print("No se generaron resultados.")
        return
        
    df_pregrado = df_res[df_res['Nivel'] == 'Pregrado'].drop(columns=['Nivel'])
    df_posgrado = df_res[df_res['Nivel'] == 'Posgrado'].drop(columns=['Nivel', 'Matríc. regular Presencial'], errors='ignore')
    
    print(f"Exportando {len(df_pregrado)} filas a {output_pregrado}...")
    df_pregrado.to_csv(output_pregrado, index=False, encoding='utf-8-sig')
    
    print(f"Exportando {len(df_posgrado)} filas a {output_posgrado}...")
    df_posgrado.to_csv(output_posgrado, index=False, encoding='utf-8-sig')
    
    output_ml = "Dataset_Longitudinal_ML.csv"
    print(f"Exportando {len(student_month)} filas longitudinales enriquecidas a {output_ml}...")
    student_month.to_csv(output_ml, index=False, encoding='utf-8-sig')
    
    print("Procesamiento completado exitosamente.")

if __name__ == '__main__':
    input_file = "base de datos de alumnos de pregrado.csv"
    process_data(input_file, "Cuadro_Mando_Pregrado_Calculado.csv", "Cuadro_Mando_Posgrado_Calculado.csv")

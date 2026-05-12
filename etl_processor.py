import pandas as pd
import numpy as np
import re
from config.settings import PERIODO_ACTUAL

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
    
    df.columns = [re.sub(r'[^\x00-\x7F]+', 'o', c) for c in df.columns]
    
    # Identificar columna Año (maneja Ao, Ao, etc)
    year_col = [c for c in df.columns if ('a' in c.lower() and 'o' in c.lower() and len(c)<=4) or 'ao' in c.lower()][0]
    
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
    student_month = df_activos.groupby(['Periodo_Real', 'Año', 'Mes_Nombre', 'Codigo_Plan_SAP', 'Programa', 'Programa_Base', 'DNI']).agg({
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
    
    # Filtro: No considerar meses futuros (evita falsas deserciones en el ETL)
    anio_hoy = PERIODO_ACTUAL // 100
    mes_hoy = PERIODO_ACTUAL % 100
    periodo_max = f"{anio_hoy}-{mes_hoy:02d}"
    meses_orden = [m for m in meses_orden if m <= periodo_max]
    
    def get_metadata(code, name):
        code = str(code).upper()
        name = str(name).upper()
        
        # Facultad
        fac = "Otros"
        if code.startswith('E02'): fac = "CC. Administrativas y RRHH"
        elif code.startswith('E06'): fac = "Derecho"
        elif code.startswith('E07'): fac = "Educación"
        elif code.startswith('E0501'): fac = "Contabilidad y Finanzas"
        elif code.startswith('E0502'): fac = "Economía"
        elif code.startswith('E10'): fac = "Medicina Humana"
        
        # Gestion
        ges = "Sin Partner (Propio)"
        if code.startswith('E05') or code.startswith('E07'): ges = "Con Partner (AP)"
        
        # Modalidad
        mod = "Presencial Regular"
        if '70/30' in name or '50/50' in name: mod = "Presencial (Híbrido)"
        elif 'DISTANCIA' in name or 'PAT' in name: mod = "Distancia"
        
        return fac, ges, mod

    student_month[['Facultad', 'Gestion', 'Modalidad_Agrupada']] = student_month.apply(
        lambda x: pd.Series(get_metadata(x['Codigo_Plan_SAP'], x['Programa'])), axis=1
    )
    
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
    programas = student_month['Codigo_Plan_SAP'].unique()
    print(f"Procesando {len(programas)} planes SAP a través de {len(meses_orden)} periodos cronológicos...")
    
    for prog in programas:
        df_prog = student_month[student_month['Codigo_Plan_SAP'] == prog].copy()
        
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
            muy_tardia = 0
            perm_siempre = 0    # Nunca faltó (ausencia previa = 0)
            perm_siempre = 0    
            perm_1mes = 0       
            perm_incontinuo = 0
            reincorporado = 0
            
            for dni in dnis_activos:
                if dni in alumnos_mes_actual:
                    prev_aus = ausencias.get(dni, 0)
                    if prev_aus == 0:
                        perm_siempre += 1       # Siempre matriculado, nunca faltó
                    elif prev_aus == 1:
                        perm_1mes += 1          # Regresa tras 1 mes exacto de ausencia
                    elif prev_aus <= 5:
                        perm_incontinuo += 1    # Regresa tras 2-5 meses
                    else:
                        reincorporado += 1      # Regresa tras 6+ meses
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
                    elif meses_fuera >= 7 and meses_fuera <= 12:
                        tardia += 1
                    elif meses_fuera > 12:
                        muy_tardia += 1
            
            # Intersecciones de retención (mantenidas para compatibilidad)
            retenidos_1m = perm_siempre + perm_1mes  # Alias directo (compatibilidad)
            
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
                'Codigo_Plan_SAP': prog,
                'Programa': df_prog['Programa'].mode()[0] if not df_prog.empty else prog,
                'Facultad': df_prog['Facultad'].iloc[0],
                'Gestion': df_prog['Gestion'].iloc[0],
                'Modalidad_Agrupada': df_prog['Modalidad_Agrupada'].iloc[0],
                'Nivel': df_prog['Nivel'].iloc[0] if not df_prog.empty else "Desconocido",
                'Egresados': len(egresados_mes_actual),
                'Admitidos Matriculados': admitidos_matriculados,
                'Nuevos Traslados': nuevos_traslados,
                'Nuevos Convalidados': nuevos_convalidados,
                # Nueva clasificación de permanencia
                'Permanentes Continuos': perm_siempre + perm_1mes,
                'Perm. Siempre (0m)': perm_siempre,
                'Perm. 1mes': perm_1mes,
                'Permanentes Incontinuos': perm_incontinuo,
                'Reincorporados': reincorporado,
                # Deserción escalonada
                'Riesgo Deserción (1m)': riesgo_1,
                'Riesgo Deserción (2m)': riesgo_2,
                'Deserción Temprana (3-6m)': temprana,
                'Deserción Tardía (7-12m)': tardia,
                'Deserción Muy Tardía (>12m)': muy_tardia,
                # Compatibilidad KPI (alias)
                'Retenidos (1m)': perm_siempre + perm_1mes,
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

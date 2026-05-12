# ============================================================
# analyzer.py — Motor de Análisis de Deserción y Crecimiento
# ============================================================

import pandas as pd
import numpy as np
from config.settings import (
    PERIODO_ACTUAL, UMBRAL_EN_RIESGO, UMBRAL_DESERTOR,
    NOTA_APROBATORIA, PROGRAMAS_CORTOS
)


def calcular_diferencia_meses(periodo_actual: int, periodo_anterior) -> int:
    """Calcula la diferencia en meses entre dos periodos YYYYMM."""
    if pd.isna(periodo_anterior) or periodo_anterior == "" or periodo_anterior == 0:
        return 999  # Sin dato = máxima antigüedad
    try:
        pa = int(periodo_actual)
        pb = int(periodo_anterior)
        anio_a, mes_a = pa // 100, pa % 100
        anio_b, mes_b = pb // 100, pb % 100
        return (anio_a - anio_b) * 12 + (mes_a - mes_b)
    except (ValueError, TypeError):
        return 999


def simplificar_programa(nombre: str) -> str:
    """Reduce el nombre largo del programa a una versión corta."""
    if pd.isna(nombre):
        return "Sin programa"
    nombre_upper = nombre.strip().upper()
    for clave, corto in PROGRAMAS_CORTOS.items():
        if clave.upper() in nombre_upper:
            return corto
    return nombre[:50]


def detectar_modalidad(nombre_programa: str) -> str:
    """Detecta la modalidad del programa desde su nombre."""
    if pd.isna(nombre_programa):
        return "Sin dato"
    nombre = nombre_programa.upper()
    if "A DISTANCIA" in nombre:
        return "A Distancia"
    elif "70/30" in nombre:
        return "Semipresencial (70/30)"
    elif "PAT" in nombre:
        return "PAT A Distancia"
    else:
        return "Presencial"


def cargar_y_preparar(filepath: str) -> pd.DataFrame:
    """Carga CSV y prepara columnas necesarias."""
    # Detectar encoding
    for enc in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(filepath, encoding=enc, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("No se pudo leer el archivo. Intente con otro encoding.")

    # Normalizar nombres de columnas (quitar acentos comunes)
    col_map = {}
    for c in df.columns:
        c_clean = c.strip()
        col_map[c] = c_clean
    df.rename(columns=col_map, inplace=True)

    # Detectar columna de año (puede ser 'Año' o 'A\xf1o')
    for c in df.columns:
        if "o" in c.lower() and "a" in c.lower() and len(c) <= 5:
            if c != "Año":
                df.rename(columns={c: "Año"}, inplace=True)
            break

    # Convertir tipos
    for col in ["Nota", "Creditos", "Ciclo_Asignatura", "Ciclo_Estudiante"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Limpiar Ultima_inscripcion
    if "Ultima_inscripcion" in df.columns:
        df["Ultima_inscripcion"] = pd.to_numeric(
            df["Ultima_inscripcion"], errors="coerce"
        )

    # Limpiar Periodio_Admision (viene con typo en el SQL)
    col_admision = None
    for c in df.columns:
        if "admision" in c.lower() or "admisión" in c.lower():
            col_admision = c
            break
    if col_admision and col_admision != "Periodo_Admision":
        df.rename(columns={col_admision: "Periodo_Admision"}, inplace=True)

    if "Periodo_Admision" in df.columns:
        df["Periodo_Admision"] = pd.to_numeric(
            df["Periodo_Admision"], errors="coerce"
        )

    # Agregar columnas calculadas
    df["Programa_Corto"] = df["Programa"].apply(simplificar_programa)
    df["Modalidad"] = df["Programa"].apply(detectar_modalidad)

    return df


def construir_perfil_alumno(df: pd.DataFrame, periodo_ref: int = None) -> pd.DataFrame:
    """
    Construye un DataFrame con 1 fila por alumno (DNI único)
    con su estado actual y métricas académicas.
    """
    if periodo_ref is None:
        periodo_ref = PERIODO_ACTUAL

    # Agrupar por DNI
    perfiles = []
    for dni, grupo in df.groupby("DNI"):
        # Datos básicos (tomar del registro más reciente)
        ultimo = grupo.sort_values("Ultima_inscripcion", ascending=False).iloc[0]

        # Métricas académicas
        notas = grupo["Nota"]
        notas_validas = notas[notas > 0]

        ultima_insc = ultimo["Ultima_inscripcion"]
        meses_sin_actividad = calcular_diferencia_meses(periodo_ref, ultima_insc)

        # Clasificar estado
        es_egresado = (grupo["Egresado"] == "SI").any()

        if es_egresado:
            estado = "EGRESADO"
        elif meses_sin_actividad <= UMBRAL_EN_RIESGO:
            estado = "ACTIVO"
        elif meses_sin_actividad <= UMBRAL_DESERTOR:
            estado = "EN_RIESGO"
        elif meses_sin_actividad <= UMBRAL_DESERTOR:
            estado = "DESERTOR"
        else:
            # > 6 meses
            if meses_sin_actividad > UMBRAL_DESERTOR:
                estado = "BAJA"
            else:
                estado = "DESERTOR"

        # Corregir lógica: 3-6 meses = DESERTOR
        if not es_egresado:
            if meses_sin_actividad <= UMBRAL_EN_RIESGO:
                estado = "ACTIVO"
            elif meses_sin_actividad <= UMBRAL_DESERTOR:
                if meses_sin_actividad <= 3:
                    estado = "EN_RIESGO"
                else:
                    estado = "DESERTOR"
            else:
                estado = "BAJA"

        perfil = {
            "DNI": dni,
            "Nombre": ultimo.get("Apellidos_Nombres", ""),
            "Programa": ultimo.get("Programa", ""),
            "Programa_Corto": ultimo.get("Programa_Corto", ""),
            "Modalidad": ultimo.get("Modalidad", ""),
            "Periodo_Admision": ultimo.get("Periodo_Admision"),
            "Ultima_Inscripcion": ultima_insc,
            "Meses_Sin_Actividad": meses_sin_actividad,
            "Estado": estado,
            "Nota_Promedio": round(notas_validas.mean(), 1) if len(notas_validas) > 0 else 0,
            "Nota_Minima": int(notas_validas.min()) if len(notas_validas) > 0 else 0,
            "Cursos_Total": len(grupo),
            "Cursos_Desaprobados": int((notas_validas < NOTA_APROBATORIA).sum()),
            "Cursos_Aprobados": int((notas_validas >= NOTA_APROBATORIA).sum()),
            "Ciclo_Estudiante": int(ultimo.get("Ciclo_Estudiante", 0)),
            "Creditos_Acumulados": int(grupo["Creditos"].sum()),
            "Telefono": ultimo.get("Nro_Telefono", ""),
            "Correo_Personal": ultimo.get("Correo_Personal", ""),
            "Correo_Institucional": ultimo.get("Correo_Institucional", ""),
            "Convalidado": "SI" if (grupo.get("Convalidado", pd.Series(["NO"])) == "SI").any() else "NO",
            "Ultima_Asignatura": ultimo.get("Asignatura", ""),
            "Ultima_Nota": int(ultimo.get("Nota", 0)),
        }
        perfiles.append(perfil)

    df_perfiles = pd.DataFrame(perfiles)

    # Tasa de desaprobación por alumno
    df_perfiles["Tasa_Desaprobacion"] = np.where(
        df_perfiles["Cursos_Total"] > 0,
        round(df_perfiles["Cursos_Desaprobados"] / df_perfiles["Cursos_Total"] * 100, 1),
        0
    )

    return df_perfiles


def resumen_por_programa(df_perfiles: pd.DataFrame) -> pd.DataFrame:
    """Genera resumen de estados por programa."""
    resumen = df_perfiles.groupby("Programa_Corto").agg(
        Total=("DNI", "count"),
        Activos=("Estado", lambda x: (x == "ACTIVO").sum()),
        En_Riesgo=("Estado", lambda x: (x == "EN_RIESGO").sum()),
        Desertores=("Estado", lambda x: (x == "DESERTOR").sum()),
        Baja=("Estado", lambda x: (x == "BAJA").sum()),
        Egresados=("Estado", lambda x: (x == "EGRESADO").sum()),
        Nota_Promedio=("Nota_Promedio", "mean"),
        Tasa_Desaprobacion=("Tasa_Desaprobacion", "mean"),
    ).round(1).reset_index()

    resumen["Tasa_Desercion"] = round(
        (resumen["Desertores"] + resumen["Baja"]) / resumen["Total"] * 100, 1
    )

    return resumen.sort_values("Tasa_Desercion", ascending=False)


def analisis_correlaciones(df_perfiles: pd.DataFrame) -> dict:
    """
    Calcula correlaciones entre factores y deserción.
    Retorna un dict con las correlaciones y sus interpretaciones.
    """
    # Crear variable binaria: ¿desertó? (DESERTOR o BAJA = 1)
    df = df_perfiles.copy()
    df["Deserto"] = ((df["Estado"] == "DESERTOR") | (df["Estado"] == "BAJA")).astype(int)

    # Excluir egresados para el análisis
    df = df[df["Estado"] != "EGRESADO"]

    if len(df) < 10:
        return {"error": "Datos insuficientes para calcular correlaciones"}

    correlaciones = []

    # 1. Nota promedio vs Deserción
    if df["Nota_Promedio"].std() > 0:
        corr = df["Nota_Promedio"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "📉 Nota Promedio",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Nota más baja → mayor probabilidad de desertar" if corr < 0 else "Nota más alta → mayor probabilidad de desertar"
        })

    # 2. Cursos desaprobados vs Deserción
    if df["Cursos_Desaprobados"].std() > 0:
        corr = df["Cursos_Desaprobados"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "❌ Cursos Desaprobados",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Más cursos desaprobados → más deserción" if corr > 0 else "Sin relación clara"
        })

    # 3. Tasa de desaprobación vs Deserción
    if df["Tasa_Desaprobacion"].std() > 0:
        corr = df["Tasa_Desaprobacion"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "📊 Tasa de Desaprobación",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Mayor tasa de desaprobación → más deserción" if corr > 0 else "Sin relación clara"
        })

    # 4. Ciclo del estudiante vs Deserción
    if df["Ciclo_Estudiante"].std() > 0:
        corr = df["Ciclo_Estudiante"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "🎓 Ciclo del Estudiante",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Alumnos de ciclos tempranos desertan más" if corr < 0 else "Alumnos de ciclos avanzados desertan más"
        })

    # 5. Créditos acumulados vs Deserción
    if df["Creditos_Acumulados"].std() > 0:
        corr = df["Creditos_Acumulados"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "📚 Créditos Acumulados",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Menos créditos acumulados → más deserción" if corr < 0 else "Más créditos no protege de deserción"
        })

    # 6. Nota mínima vs Deserción
    if df["Nota_Minima"].std() > 0:
        corr = df["Nota_Minima"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "⬇️ Nota Mínima Obtenida",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Notas mínimas más bajas → más deserción" if corr < 0 else "Sin relación clara"
        })

    # 7. Última nota vs Deserción
    if df["Ultima_Nota"].std() > 0:
        corr = df["Ultima_Nota"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "📝 Última Nota Registrada",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Última nota baja → más deserción (señal de alerta temprana)" if corr < 0 else "Sin relación clara"
        })

    # 8. Total de cursos llevados vs Deserción
    if df["Cursos_Total"].std() > 0:
        corr = df["Cursos_Total"].corr(df["Deserto"])
        correlaciones.append({
            "Factor": "📋 Total de Cursos Llevados",
            "Correlación": round(corr, 3),
            "Fuerza": _fuerza_correlacion(corr),
            "Interpretación": "Menos cursos registrados → más deserción" if corr < 0 else "Más cursos no garantiza permanencia"
        })

    # Ordenar por fuerza absoluta
    correlaciones.sort(key=lambda x: abs(x["Correlación"]), reverse=True)

    # Estadísticas comparativas
    activos = df[df["Deserto"] == 0]
    desertores = df[df["Deserto"] == 1]

    comparativo = {}
    if len(activos) > 0 and len(desertores) > 0:
        comparativo = {
            "Nota Promedio": {
                "Activos": round(activos["Nota_Promedio"].mean(), 1),
                "Desertores": round(desertores["Nota_Promedio"].mean(), 1),
            },
            "Cursos Desaprobados (prom)": {
                "Activos": round(activos["Cursos_Desaprobados"].mean(), 1),
                "Desertores": round(desertores["Cursos_Desaprobados"].mean(), 1),
            },
            "Tasa Desaprobación (%)": {
                "Activos": round(activos["Tasa_Desaprobacion"].mean(), 1),
                "Desertores": round(desertores["Tasa_Desaprobacion"].mean(), 1),
            },
            "Ciclo Estudiante (prom)": {
                "Activos": round(activos["Ciclo_Estudiante"].mean(), 1),
                "Desertores": round(desertores["Ciclo_Estudiante"].mean(), 1),
            },
        }

    return {
        "correlaciones": correlaciones,
        "comparativo": comparativo,
        "n_activos": len(activos),
        "n_desertores": len(desertores),
    }


def materias_criticas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifica las asignaturas con mayor tasa de desaprobación
    y las correlaciona con deserción posterior.
    """
    # Filtrar solo cursos con nota registrada
    df_notas = df[df["Nota"] > 0].copy()
    df_notas["Desaprobado"] = (df_notas["Nota"] < NOTA_APROBATORIA).astype(int)

    resumen = df_notas.groupby("Asignatura").agg(
        Alumnos=("DNI", "nunique"),
        Nota_Promedio=("Nota", "mean"),
        Desaprobados=("Desaprobado", "sum"),
        Total_Registros=("Desaprobado", "count"),
    ).reset_index()

    resumen["Tasa_Desaprobacion"] = round(
        resumen["Desaprobados"] / resumen["Total_Registros"] * 100, 1
    )

    # Filtrar asignaturas con al menos 5 alumnos
    resumen = resumen[resumen["Alumnos"] >= 5]
    resumen["Nota_Promedio"] = resumen["Nota_Promedio"].round(1)

    return resumen.sort_values("Tasa_Desaprobacion", ascending=False).head(20)


def crecimiento_por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el crecimiento de matrícula por periodo SAP.
    """
    if "Periodo_SAP" not in df.columns:
        return pd.DataFrame()

    crecimiento = df.groupby("Periodo_SAP").agg(
        Alumnos_Unicos=("DNI", "nunique"),
        Registros=("DNI", "count"),
    ).reset_index()

    crecimiento = crecimiento.sort_values("Periodo_SAP")
    crecimiento["Variacion"] = crecimiento["Alumnos_Unicos"].diff()
    crecimiento["Variacion_Pct"] = round(
        crecimiento["Alumnos_Unicos"].pct_change() * 100, 1
    )

    return crecimiento


def cohorte_supervivencia(df_perfiles: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula tasa de supervivencia por cohorte (Periodo_Admision).
    """
    df = df_perfiles.copy()
    df = df[df["Periodo_Admision"].notna() & (df["Periodo_Admision"] > 0)]

    # Crear año de admisión para agrupar
    df["Anio_Admision"] = (df["Periodo_Admision"] // 100).astype(int)

    cohortes = df.groupby("Anio_Admision").agg(
        Total=("DNI", "count"),
        Activos=("Estado", lambda x: (x == "ACTIVO").sum()),
        En_Riesgo=("Estado", lambda x: (x == "EN_RIESGO").sum()),
        Desertores=("Estado", lambda x: ((x == "DESERTOR") | (x == "BAJA")).sum()),
        Egresados=("Estado", lambda x: (x == "EGRESADO").sum()),
    ).reset_index()

    cohortes["Tasa_Retencion"] = round(
        (cohortes["Activos"] + cohortes["Egresados"]) / cohortes["Total"] * 100, 1
    )
    cohortes["Tasa_Desercion"] = round(
        cohortes["Desertores"] / cohortes["Total"] * 100, 1
    )

    return cohortes.sort_values("Anio_Admision")


def _fuerza_correlacion(corr: float) -> str:
    """Clasifica la fuerza de una correlación."""
    abs_corr = abs(corr)
    if abs_corr >= 0.7:
        return "🔴 Fuerte"
    elif abs_corr >= 0.4:
        return "🟡 Moderada"
    elif abs_corr >= 0.2:
        return "🟢 Débil"
    else:
        return "⚪ Muy débil"

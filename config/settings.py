# ============================================================
# settings.py — Configuración del Sistema de Análisis
# ============================================================

from datetime import datetime

# Periodo actual (YYYYMM) — se calcula automáticamente
now = datetime.now()
PERIODO_ACTUAL = int(f"{now.year}{now.month:02d}")

# Umbrales de clasificación (en meses)
UMBRAL_EN_RIESGO = 2    # 1-2 meses sin matricularse
UMBRAL_DESERTOR = 6     # 3-6 meses sin matricularse
# > 6 meses = BAJA (dado de baja del programa)

# Nota mínima aprobatoria
NOTA_APROBATORIA = 11

# Nombres de columnas esperadas del CSV de Metabase
COLUMNAS_REQUERIDAS = [
    "Programa", "Matricula", "DNI", "Apellidos_Nombres",
    "Ultima_inscripcion", "Nota", "Egresado"
]

# Mapeo de nombres de programas simplificados
PROGRAMAS_CORTOS = {
    "CARRERA DE CONTABILIDAD Y FINANZAS": "Contabilidad",
    "CARRERA DE ECONOMIA": "Economía",
    "CARRERA DE DERECHO": "Derecho",
    "CARRERA PROFESIONAL DE EDUCACION CON MENCION EN INICIAL": "Educación - Inicial",
    "CARRERA PROFESIONAL DE EDUCACION CON MENCION EN PRIMARIA": "Educación - Primaria",
    "CARRERA PROFESIONAL DE EDUCACION CON MENCION EN MATEMÁTICA E INFORMÁTICA": "Educación - Matemática",
    "CARRERA PROFESIONAL DE EDUCACION CON MENCION EN CIENCIAS SOCIALES Y COMUNICACIÓN": "Educación - CC.SS.",
    "CARRERA PROFESIONAL DE ADMINISTRACION": "Administración",
    "CARRERA PROFESIONAL DE ADMINISTRACION Y NEGOCIOS INTERNACIONALES": "Adm. y Neg. Int.",
    "CARRERA PROFESIONAL DE GESTION DE RECURSOS HUMANOS": "Gestión RR.HH.",
    "CARRERA PROFESIONAL DE MARKETING": "Marketing",
}

# Colores del sistema
COLORES = {
    "ACTIVO": "#10b981",
    "EN_RIESGO": "#f59e0b",
    "DESERTOR": "#ef4444",
    "BAJA": "#6b7280",
    "EGRESADO": "#3b82f6",
}

COLORES_LISTA = ["#10b981", "#f59e0b", "#ef4444", "#6b7280", "#3b82f6"]

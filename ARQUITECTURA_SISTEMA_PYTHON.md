# Arquitectura del Sistema de Análisis de Crecimiento, Deserción y Machine Learning (USMP)

**Fecha de Actualización:** Mayo 2026
**Tecnologías:** Python 3 (Pandas, Numpy), Streamlit, Plotly, SQL.

Este documento técnico describe la arquitectura, el flujo de datos y las reglas estrictas de negocio del nuevo sistema de análisis de datos. Reemplaza al anterior sistema basado en Google Apps Script, sentando las bases tecnológicas necesarias para el despliegue futuro de modelos predictivos de Machine Learning.

---

## 1. Visión General y Flujo de Datos (Data Pipeline)

El sistema emplea un pipeline ETL (Extracción, Transformación y Carga) estructurado en 4 capas lógicas. Está diseñado para ser escalable y modular, permitiendo que otros equipos (Sistemas, Ciencia de Datos) o inteligencias artificiales puedan consumir los datos.

### Capa 1: Extracción (Data Source)
- **Origen:** Metabase / SAP.
- **Consulta Unificada:** Toda la extracción se realiza a través de un único query SQL denominado `"Datos para Análisis de Crecimiento y deserción v2026"`.
- **Granularidad:** Nivel transaccional profundo: *DNI Alumno -> Asignatura -> Estado_Curso -> Mes/Periodo SAP*.
- **Formato:** Extracción periódica en CSV (`base de datos de alumnos de pregrado.csv`).

### Capa 2: Procesamiento y Feature Engineering (Data Engineering / ETL)
- **Motor Principal:** Archivo `etl_processor.py`.
- **Lógica:** Implementa teoría de conjuntos (Set Theory) con Pandas para cruzar los DNIs mes a mes.
- **Propósito:** 
  1. Limpiar e imputar datos nulos.
  2. Aplicar las reglas de matrícula universitaria.
  3. Calcular métricas absolutas (Desertores, Nuevos, Egresados).
  4. Generar la matriz histórica que servirá como entrada (Features) para los futuros algoritmos de Machine Learning.

### Capa 3: Modelo Predictivo (Machine Learning - Próxima Fase)
- **Objetivo:** Calcular la probabilidad individual de deserción de un alumno para el siguiente mes `t+1`, basándose en su comportamiento histórico hasta el mes `t`.
- **Tecnología Proyectada:** `scikit-learn`, `XGBoost` o `LightGBM`.
- **Variables Potenciales (Features):** Frecuencia de cursos reprobados, cambios de plan (traslados internos), proporción de asignaturas convalidadas vs cursadas, antigüedad en el programa.

### Capa 4: Presentación y Visualización (Dashboard)
- **Motor Principal:** Archivo `app.py`.
- **Tecnología:** Streamlit (para web interactiva) y Plotly (para visualización de gráficos complejos como Waterfall y de evolución temporal).

---

## 2. Reglas de Negocio Estrictas

Para asegurar la coherencia de los indicadores gerenciales, el ETL aplica rigurosamente las siguientes reglas acordadas:

### 2.1. Matrícula Activa (`Estado_curso`)
No todos los registros en SAP significan que un alumno está estudiando en un mes específico.
- **Estudiante Activo:** Un DNI se contabiliza como matriculado en un mes **solo si** posee al menos una asignatura con `Estado_curso = 'CURSADO'`.
- **Filtro de Trámites:** Si el DNI en ese mes únicamente tiene asignaturas con `Estado_curso = 'CONVALIDADO'`, el sistema lo ignora como matrícula activa de ese mes (es solo un papeleo histórico o trámite).

### 2.2. Clasificación de Alumnos Nuevos (Admitidos Matriculados)
*Nota: Se omite formalmente el uso de la palabra "Cachimbo".*
- **Regla Estricta:** Un alumno se clasifica como "Admitido Matriculado" en un mes determinado **solo si** es la **primera vez en toda la historia** que su DNI registra una matrícula activa (`CURSADO`) dentro de ese programa.
- Si su primera aparición histórica es únicamente con cursos `'CONVALIDADO'`, no es un alumno nuevo, sino un traslado/convalidación externa.

### 2.3. Normalización de Programas y Traslados Internos
Un gran reto analítico es evitar registrar "Falsas Deserciones" cuando un alumno simplemente cambia de modalidad (ej. pasa de presencial a distancia) dentro de la misma carrera. Se aborda desde dos ópticas:

- **Opción A (Dashboard Gerencial Principal - `Programa_Base`):**
  El ETL limpia el nombre del programa, borrando sufijos como `"- (A DISTANCIA AP)"`, `"- (70/30 AP)"` o `"- (2DA ESPECIALIDAD)"`. 
  *Efecto:* Todas las modalidades de Contabilidad se vuelven una sola gran carrera. Si un alumno cambia de modalidad, para el Dashboard gerencial es transparente y el alumno figura con matrícula continua (sin deserción).

- **Opción B (Análisis Granular e Inteligencia Artificial - `Código_Plan_SAP`):**
  El ETL conserva intacto el `Código_Plan_SAP`. Puesto que el código es inmutable, incluso si el nombre legal de la carrera cambia con los años (ej. de "Educación Histórico" a "Primaria"), el código unifica a esa cohorte. Si un alumno cambia de `Código_Plan_SAP`, en el procesamiento a bajo nivel esto se registra como un **Traslado Saliente** (y no como una deserción neta), permitiendo a los algoritmos predictivos detectar inestabilidad académica sin distorsionar el macro-dashboard.

### 2.4. Cálculos Mensuales (Operaciones de Conjuntos)
Basado en el mes `t` y mes anterior `t-1`:
- **Egresados:** `DNI` con la marca `Egresado = 'SI'` en el mes `t`.
- **Desertores (No Matriculados):** `DNI` que estuvo matriculado activamente en `t-1`, NO está Egresado, y NO tiene matrícula activa en `t`.
- **Recuperados:** `DNI` que tiene historial de matrícula en el programa, estuvo ausente en `t-1`, pero reaparece activamente matriculado en `t`.

---

## 3. Próximos Pasos (Roadmap Técnico)
1. **Fase Actual:** Actualizar la sintaxis de `etl_processor.py` para cumplir cabalmente con las Reglas 2.1, 2.2 y 2.3.
2. **Validación:** Cruzar las salidas del CSV generado con los antiguos cuadros de mando `Cuadro_Mando_Pregrado_Actualizado.csv` para garantizar exactitud retroactiva.
3. **Despliegue Local:** Probar el Dashboard en local asegurando alta fluidez con más de 100,000 filas.
4. **Fase Predictiva:** Extraer el histórico del ETL para entrenar un Random Forest Classifier o XGBoost que asigne un "Score de Riesgo" mensual a cada DNI activo.

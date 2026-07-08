# Arquitectura del Sistema de Análisis de Crecimiento, Deserción y Machine Learning (USMP)

**Fecha de Última Actualización:** 8 de Julio de 2026  
**Tecnologías:** Python 3 (Pandas, Numpy), Streamlit, Plotly, SQL.

Este documento técnico describe la arquitectura, el flujo de datos y las reglas de negocio del sistema de análisis de datos de la USMP Virtual. El sistema procesa de forma integrada el pipeline analítico para **Pregrado** y **Posgrado**, sentando las bases tecnológicas necesarias para el consumo analítico y el entrenamiento de modelos predictivos de Machine Learning.

---

## 1. Visión General y Flujo de Datos (Data Pipeline)

El sistema emplea un pipeline ETL (Extracción, Transformación y Carga) y visualización estructurado en 4 capas lógicas.

### Capa 1: Extracción (Data Source)
- **Origen:** Metabase / SAP.
- **Granularidad:** Nivel transaccional profundo: *DNI Alumno -> Asignatura -> Estado_Curso -> Mes/Periodo SAP*.
- **Formatos de Entrada:** 
  - Pregrado: `Base de datos historial academico de alumnos de pregrado - Julio.csv`
  - Posgrado: `base de datos de historial académico de alumnos de posgrado.csv`

### Capa 2: Procesamiento y Feature Engineering (ETL)
- **Motor Principal:** Archivo `etl_processor.py`.
- **Lógica:** Implementa procesamiento conjunto en Pandas para ambas bases de datos. Etiqueta la dimensión `Nivel` dinámicamente según el archivo fuente y calcula de manera segura egresados unificados y retención de cohortes.
- **Salidas Generadas:**
  - `Cuadro_Mando_Pregrado_Calculado.csv`
  - `Cuadro_Mando_Posgrado_Calculado.csv`
  - `Dataset_Longitudinal_ML.csv` (Para modelos de IA)
  - `Asignaturas_Desaprobados_Historico.csv` (Cursos críticos)

### Capa 3: Visualización e Interfaz (Dashboard Streamlit)
- **Motor Principal:** Archivo `app.py`.
- **Características:**
  - Selector dinámico de nivel académico (**Pregrado** / **Posgrado**) incorporado en la barra lateral.
  - Filtros en caliente para aislar materias y datos predictivos por nivel.
  - Gráficos interactivos de dinámica de crecimiento y balance mensual.

### Capa 4: Modelo Predictivo (Machine Learning - En Desarrollo)
- **Propósito:** Calcular la probabilidad individual de retorno/deserción de un alumno basándose en su rendimiento académico, ausencias e inestabilidad (traslados).

---

## 2. Reglas de Negocio Estrictas

### 2.1. Matrícula Activa (`Estado_curso`)
Un DNI se contabiliza como matriculado en un mes **solo si** posee al menos una asignatura en ese periodo con `Estado_curso = 'CURSADO'`.

### 2.2. Clasificación de Alumnos Nuevos
Un alumno es "Admitido Matriculado" en un mes determinado **solo si** es la **primera vez en toda la historia** que su DNI registra una matrícula activa (`CURSADO`) en ese programa.

### 2.3. Normalización de Programas
- **Dashboard Gerencial (`Programa_Base`):** El ETL limpia sufijos como `(A DISTANCIA AP)` o `(70/30 AP)` para unificar las modalidades y evitar falsas deserciones al cambiar de modalidad dentro de una carrera.
- **Análisis de Machine Learning (`Código_Plan_SAP`):** Se mantiene el código SAP inmutable para dar trazabilidad a los traslados y cambios entre cohortes.

---

## 3. Roadmap Técnico

1. **Entrenamiento de Modelos Predictivos:** Utilizar el consolidado de `Dataset_Longitudinal_ML.csv` para entrenar el modelo de Random Forest incorporado en el dashboard.
2. **Publicación y Dockerización:** Preparar la imagen Docker para subir el sistema a producción en Google Cloud Run.
3. **Automatización Webhook:** Automatizar la llamada al ETL en la nube cuando se publiquen nuevas extracciones en el repositorio o la base de datos central.

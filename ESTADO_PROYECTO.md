# Estado del Proyecto: Sistema de Análisis de Deserción y Crecimiento (USMP)

**Fecha de Última Actualización:** 8 de Julio de 2026  
**Objetivo Principal:** Mantener un pipeline de datos robusto y un dashboard gerencial unificado para el análisis longitudinal de retención, crecimiento y riesgo académico de los alumnos de Pregrado y Posgrado de la USMP Virtual.

---

## 1. Hitos Alcanzados en la Sesión de Hoy (Julio 2026)

### 1.1. Actualización General a Julio 2026
* **Datos Actualizados:** Se procesaron e integraron de forma exitosa las bases de datos actualizadas al período de **Julio 2026**.
* **Límite Temporal Automático:** El pipeline de datos detecta el límite cronológico en base al mes actual y filtra de forma inteligente registros incompletos o adelantados.

### 1.2. Pipeline de Datos Concurrente (Pregrado + Posgrado)
* **Procesamiento Unificado:** Se actualizó `etl_processor.py` para leer y procesar simultáneamente las bases de datos de Pregrado (`Base de datos historial academico de alumnos de pregrado - Julio.csv`) y Posgrado (`base de datos de historial académico de alumnos de posgrado.csv`).
* **Seguridad en Nivel de Origen:** El campo `Nivel` se asigna directamente según el archivo origen (`Pregrado` o `Posgrado`), erradicando falsos positivos que dependían de la coincidencia del término `"MAESTR"` en el nombre del programa.

### 1.3. Dashboard Unificado y Selector en Filtros Principales (`app.py`)
* **Selector Sidebar:** Se integró un control de radio dinámico en los **Filtros Principales** de la barra lateral para alternar entre **Pregrado** y **Posgrado**.
* **Visualizaciones Homólogas:** Ambas opciones cargan exactamente la misma estructura de pestañas, KPIs, gráficos de balance y evolución de matrícula, adaptándose dinámicamente a los datos de cada nivel.
* **Filtrado en Caliente:** Los datasets de cursos reprobados (`Asignaturas_Desaprobados_Historico.csv`) y longitudinales de ML (`Dataset_Longitudinal_ML.csv`) se filtran en caliente según el nivel seleccionado para evitar contaminación de métricas en análisis globales.

### 1.4. Corrección en Matriz de Riesgo (Cruce de Programas)
* **Normalización de Nombres:** Se implementó `clean_program_name` al realizar el cruce de asignaturas desaprobadas con la tasa de deserción, incrementando los programas emparejados en la correlación de 7 a 11 en pregrado.

---

## 2. Componentes Técnicos Activos

* **`etl_processor.py`**: Pipeline principal en Pandas. Lee las bases en CSV, calcula métricas de cohorte y egresados deduplicados, clasifica las permanencias e incompresiones, y exporta datos consolidados.
* **`app.py`**: Interfaz de visualización interactiva basada en Streamlit y Plotly. Permite alternar de manera fluida entre Pregrado y Posgrado.
* **`config/settings.py`**: Configuración centralizada de umbrales, notas aprobatorias, mapeos de nombres de programas y paleta de colores corporativos.
* **Archivos Consolidados de Datos**:
  * `Cuadro_Mando_Pregrado_Calculado.csv` (Tablero de pregrado)
  * `Cuadro_Mando_Posgrado_Calculado.csv` (Tablero de posgrado)
  * `Dataset_Longitudinal_ML.csv` (Base de datos transaccional-longitudinal unificada para Machine Learning)
  * `Asignaturas_Desaprobados_Historico.csv` (Historial académico de cursos críticos)

---

## 3. Próximos Pasos

1. **Construcción y Despliegue de Modelos de Machine Learning**:
   - Entrenar modelos predictivos (Random Forest o XGBoost) utilizando la base enriquecida de `Dataset_Longitudinal_ML.csv` para predecir el score individual de deserción y el reingreso de alumnos.
2. **Dockerización del Sistema**:
   - Validar que el `Dockerfile` configure correctamente el entorno virtual local antes de realizar el despliegue del dashboard en Google Cloud Run.
3. **Automatización del Ingestion Pipeline**:
   - Vincular la carga mensual de datos a un proceso automatizado (ej. API de Metabase) para omitir la carga manual de archivos de texto CSV.

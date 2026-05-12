# Estado del Proyecto: Sistema de Análisis de Deserción y Crecimiento (Pregrado)

**Fecha de Actualización:** 12 de Mayo de 2026
**Objetivo Principal:** Optimizar el agrupamiento de estudiantes y refinar la taxonomía de retención y deserción, garantizando la trazabilidad longitudinal a través del Código SAP.

---

## 1. Hitos Alcanzados en la Última Sesión

### 1.1. Arquitectura de Agrupación por Código SAP
* **Cambio Estructural (ETL):** El ancla de procesamiento pasó del nombre textual (`Programa_Base`) al **Código Plan SAP** (`Codigo_Plan_SAP`).
* **Resolución de Conflictos:** Esto solucionó definitivamente el cruce de programas con nombres idénticos pero naturalezas distintas (ej. Derecho Regular vs. Derecho PAT a Distancia).
* **Escalabilidad:** El sistema ahora detecta 30 planes únicos (frente a los 17 anteriores), asegurando que ninguna cohorte de estudiantes quede invisibilizada o fusionada por error.

### 1.2. Jerarquía Académica Multidimensional
Se han implementado y estabilizado las siguientes dimensiones en el ETL, disponibles como filtros jerárquicos interactivos en `app.py`:
1. **Facultad:** Educación, Derecho, Economía, Contabilidad y Finanzas, CC. Administrativas y RRHH, Medicina Humana.
2. **Gestión Operativa:** Separación clara entre planes **Propios (Sin Partner)** y planes **Con Partner (AP)**.
3. **Modalidad Agrupada:** Distancia, Presencial (Híbrido) y Presencial Regular.

### 1.3. Nueva Taxonomía de Permanencia (Sustituye a "Retenidos / Recuperados")
Se ha diseñado una nueva categorización para entender el comportamiento de continuidad de la matrícula:
* 🟢 **Permanentes Continuos (0-1m):** Alumnos matriculados sin interrupción o que regresan tras máximo 1 mes de ausencia (Riesgo 1m recuperado).
* 🟡 **Permanentes Incontinuos (2-5m):** Alumnos que interrumpen sus estudios entre 2 y 5 meses y logran ser recuperados antes de considerarse desertores tardíos.
* 🟤 **Reincorporados (6m+):** Alumnos que regresan al sistema tras una larga ausencia superior a un semestre.

### 1.4. Rediseño Analítico del Dashboard (`app.py`)
* **Control de Caché Robusto:** Se integró la marca de tiempo de modificación del archivo (`mtime`) para garantizar que la interfaz siempre lea la última versión generada por el ETL.
* **Seguridad de Tipos:** Conversión forzada de variables a texto puro antes de procesos de ordenamiento (`sorted`), erradicando `TypeError` y previniendo caídas del panel.
* **Dinámica de Crecimiento (Gráfico 1):** Las *Entradas* calculan correctamente a los **Nuevos** y a todos los **Recuperados** (1m, Incontinuos y Reincorporados), balanceando el *Crecimiento Neto* contra las *Salidas* (Egresados y Riesgo 1m).
* **Balance de Matrícula (Gráfico 2):** Vista consolidada de pérdida vs. masa retenida. Para mantener la limpieza visual, los indicadores de *Deserción Temprana* y *Riesgo 2m* se ocultaron por defecto (visibles bajo demanda mediante la leyenda).

---

## 2. Componentes Técnicos Activos

* **`etl_processor.py`**: Corazón lógico. Toma la base sucia en CSV, aplica las reglas de agrupamiento `Codigo_Plan_SAP`, calcula las nuevas variables de retención interrumplida, y exporta tablas agregadas y un dataset plano.
* **`app.py`**: Interfaz de Streamlit. Carga las agregaciones y renderiza el árbol de filtros en la barra lateral con manejo seguro de excepciones y gráficos interactivos mediante `plotly.graph_objects`.
* **Archivos Intermedios**:
  * `Cuadro_Mando_Pregrado_Calculado.csv` (Tablero de mando)
  * `Dataset_Longitudinal_ML.csv` (Base lista para IA / Machine Learning)
  * `Asignaturas_Desaprobados_Historico.csv` (Métrica de calidad académica por curso)

---

## 3. Próximos Pasos Recomendados

1. **Dashboard de Posgrado:** Extender las mismas reglas de negocio (código SAP y jerarquía) para los programas de maestrías y especializaciones.
2. **Modelo Predictivo de Riesgo:** Aprovechar el `Dataset_Longitudinal_ML.csv` recién refinado para entrenar un modelo temprano de alerta utilizando el número de ausencias (`prev_aus`), la modalidad y el rendimiento en asignaturas filtro.
3. **Automatización de Ejecución:** Si el CSV base (`base de datos de alumnos de pregrado.csv`) se actualiza periódicamente, recomendar empaquetar el `etl_processor.py` en una tarea cronometrada o webhook conectada al sistema central de la universidad.

# 📘 Documentación Técnica Completa
## Sistema de Análisis de Crecimiento y Deserción — USMP Virtual 2026

---

## Tabla de Contenidos

1. [Proceso de Actualización Mensual (Flujo de Trabajo)](#1-proceso-de-actualización-mensual)
2. [Arquitectura Técnica del Sistema](#2-arquitectura-técnica-del-sistema)
3. [Diccionario Completo de Métricas y Fórmulas](#3-diccionario-completo-de-métricas-y-fórmulas)
4. [Catálogo de Visualizaciones y Análisis](#4-catálogo-de-visualizaciones-y-análisis)
5. [Estructura de Datos (Esquema de Columnas)](#5-estructura-de-datos)
6. [Guía de Despliegue](#6-guía-de-despliegue)

---

## 1. Proceso de Actualización Mensual

El sistema requiere un flujo de **dos fases** para actualizar los datos cada mes. Parte de este proceso aún es semiautomático y requiere intervención manual.

### Diagrama del Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FASE 1: PREPARACIÓN DE DATOS                    │
│                   (Asistido por IA — Semiautomático)                │
│                                                                     │
│  ┌──────────┐    ┌───────────────┐    ┌──────────────────────────┐  │
│  │ Documento│───▶│ Antigravity   │───▶│ CSV con métricas         │  │
│  │ Word     │    │ (IA asistente)│    │ calculadas               │  │
│  │ (.docx)  │    │ Extrae tablas │    │ (Pregrado + Posgrado)    │  │
│  │          │    │ y calcula     │    │                          │  │
│  └──────────┘    │ fórmulas      │    └──────────────────────────┘  │
│                  └───────────────┘                                   │
├─────────────────────────────────────────────────────────────────────┤
│                     FASE 2: CARGA Y VISUALIZACIÓN                   │
│                         (Manual + Automático)                       │
│                                                                     │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────────┐   │
│  │ CSV generado │───▶│ Google Sheets │───▶│ Dashboard          │   │
│  │ (pegar o     │    │ (Pestañas:    │    │ (index.html)       │   │
│  │  importar)   │    │  Pregrado /   │    │ Lee datos en vivo  │   │
│  │              │    │  Posgrado)    │    │ via Código.gs      │   │
│  └──────────────┘    └───────────────┘    └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### FASE 1 — Preparación de Datos (Conversión con IA)

**¿Por qué se necesita esta fase?**
Los datos originales llegan en formato **Word (.docx)** con tablas complejas (celdas fusionadas, filas de totales, datos agrupados por etapas). Este formato no es directamente consumible por el dashboard. Se requiere una transformación intermedia.

**Paso a paso:**

| Paso | Acción | Quién lo hace | Detalle |
|------|--------|---------------|---------|
| 1.1 | Obtener los documentos Word del mes | Usuario | Archivos tipo `Resultados Generales Carreras Profesionales MAYxxob.docx` y `Resultados Generales Maestrías MAYxxob.docx` |
| 1.2 | Enviar documentos al asistente IA (Antigravity) | Usuario | Se los pasa como archivos adjuntos en la conversación |
| 1.3 | Extracción de tablas del .docx | IA (Antigravity) | Script Python que usa `zipfile` + `xml.etree` para leer el XML interno del Word y extraer las filas de cada tabla |
| 1.4 | Limpieza y mapeo de datos | IA (Antigravity) | Filtra filas de "Totales", "Total AP", "Total sin AP". Mapea etapas numéricas (1,2,3,4,5) a nombres de mes (Enero, Febrero, etc.) |
| 1.5 | Cálculo automático de métricas | IA (Antigravity) | Aplica las 7-8 fórmulas del Diccionario de Métricas (ver Sección 3) |
| 1.6 | Generación de archivos CSV | IA (Antigravity) | Produce `Cuadro_Mando_Pregrado_Actualizado.csv` y `Cuadro_Mando_Posgrado_Actualizado.csv` |

**Datos nuevos detectados a partir de Mayo 2026:**
- **"Alumnos en Asignaturas de 2 Meses"**: Columna `2° Mes` en los documentos originales. Representa estudiantes que NO necesitan rematricularse este mes porque están cursando una asignatura de duración extendida (2 meses). Este dato es clave para explicar discrepancias entre el Crecimiento Neto calculado y la variación real del Total de Matriculados.

### FASE 2 — Carga Manual y Visualización Automática

| Paso | Acción | Quién lo hace | Detalle |
|------|--------|---------------|---------|
| 2.1 | Abrir Google Sheets vinculado | Usuario | ID: `1rOv812dEhB0uT4DGwNnVEqJLWfhFfTmpWohLYcaZB28` |
| 2.2 | Pegar/importar CSV en pestaña correspondiente | Usuario | Pestaña `Pregrado` para carreras, pestaña `Posgrado` para maestrías |
| 2.3 | Verificar encabezados | Usuario | La fila 1 debe tener los nombres exactos de las columnas (el sistema busca por coincidencia parcial, pero los nombres deben ser reconocibles) |
| 2.4 | Abrir el Dashboard | Automático | Al acceder a la webapp desplegada de Google Apps Script, `Código.gs` lee las hojas automáticamente y renderiza todo |

**Modo alternativo (Offline / sin Google Apps Script):**
- El usuario puede cargar archivos CSV directamente desde el navegador usando los botones "CSV Pregrado" / "CSV Posgrado" del dashboard
- También existe un botón "Usar Demo" que carga datos de ejemplo de Enero y Febrero

---

## 2. Arquitectura Técnica del Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    CAPA DE PRESENTACIÓN                  │
│                     (index.html)                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  5 Tarjetas  │  │ 15+ Gráficos │  │  2 Modales   │  │
│  │  KPI (cards) │  │  Chart.js    │  │  Educativos  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│  ┌──────▼─────────────────▼──────────────────▼───────┐  │
│  │              Motor de Cálculo (JavaScript)         │  │
│  │  procesarDatos() → aggregateData() → getTrendData()│  │
│  │  renderCharts() → renderTrendCharts()              │  │
│  │  renderMatrizChart() → renderComparativeTrendCharts│  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │                                │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │          Capa de Datos (Dual Source)                │  │
│  │                                                    │  │
│  │  ┌─────────────────┐    ┌───────────────────────┐ │  │
│  │  │ Google Sheets   │    │ Carga Local CSV       │ │  │
│  │  │ (via Código.gs) │    │ (PapaParse + Upload)  │ │  │
│  │  │ getDatos()      │    │ handleFileUpload()    │ │  │
│  │  └─────────────────┘    └───────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │           Integración IA (Gemini 2.5 Flash)        │  │
│  │  solicitarAnalisisIA() → analizarConGemini()       │  │
│  │  Diagnóstico ejecutivo en lenguaje natural         │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  CAPA DE BACKEND (GAS)                   │
│                    (Código.gs)                            │
│                                                          │
│  doGet()           → Sirve el HTML como webapp           │
│  getDatos()        → Lee Google Sheets (Pregrado +       │
│                      Posgrado) y retorna JSON            │
│  sheetToObjects()  → Mapeo inteligente de columnas       │
│                      con búsqueda fuzzy por nombre       │
│  analizarConGemini → Llama a la API de Gemini con        │
│                      los KPIs del contexto actual        │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Datos Interno

```
Google Sheets ──────────────────────────────────────────┐
  │                                                     │
  ▼                                                     │
sheetToObjects()                                        │
  │ Mapea encabezados → Objeto JS                       │
  │ {mes, programa, egresados, noMatri, admitidos,      │
  │  admitidosMatri, recuperados, matDistancia,          │
  │  matPresencial, total, dosMeses}                     │
  ▼                                                     │
procesarDatos()                                         │
  │ Calcula campos derivados:                           │
  │  → perdidaConv, desercionNeta, brechaReemplazo,     │
  │    crecimientoNeto, tasaEfComercial,                │
  │    balanceRetencion, tasaRenov, propCierre,          │
  │    tasaDesercion                                     │
  ▼                                                     │
db = { pregrado: [...], posgrado: [...] }               │
  │                                                     │
  ├── Filtros (Nivel, Mes, Programa) ──▶ actualizarDashboard()
  │                                      │
  │                      ┌───────────────┤
  │                      ▼               ▼
  │               KPIs + Diagnóstico   Gráficos (Chart.js)
  │                      │
  │                      ▼
  │               Gemini AI (opcional)
  │               Diagnóstico ejecutivo
  └─────────────────────────────────────────────────────┘
```

### Tecnologías y Dependencias

| Componente | Tecnología | Versión/CDN |
|---|---|---|
| Estructura | HTML5 | — |
| Lógica | JavaScript (Vanilla) | ES6+ |
| Estilos | TailwindCSS | CDN (última) |
| Gráficos | Chart.js | CDN (última) |
| Parsing CSV | PapaParse | 5.4.1 |
| Tipografía | Google Fonts (Inter) | 300–700 |
| Backend | Google Apps Script | V8 Runtime |
| Base de Datos | Google Sheets | — |
| IA | Gemini 2.5 Flash | REST API |

---

## 3. Diccionario Completo de Métricas y Fórmulas

### 3.1 Campos Base (Datos Operativos)

| Campo | Descripción | Origen |
|---|---|---|
| **Mes** | Periodo mensual (Enero–Diciembre) | Etapa 1–12 del documento Word |
| **Programa** | Nombre de la carrera o maestría | Fila individual del Word |
| **Egresados** | Alumnos que completaron su plan de estudios este mes | Dato directo |
| **No matriculados** | Alumnos activos que NO renovaron su matrícula este mes (deserción bruta) | Dato directo |
| **Admitidos** | Postulantes que aprobaron el proceso de admisión (leads calificados) | Dato directo |
| **Admitidos Matriculados** | Admitidos que efectivamente pagaron y se matricularon (ventas cerradas) | Dato directo |
| **Recuperados** | Alumnos previamente inactivos que volvieron a matricularse | Dato directo |
| **Matríc. regular a Distancia** | Alumnos inscritos en la modalidad virtual/online | Dato directo |
| **Matríc. regular Presencial** | Alumnos en planes de cierre 50/50 o 70/30 (solo Pregrado) | Dato directo |
| **Estudiantes matrí. TOTAL** | Total de alumnos activos con matrícula vigente | Dato directo |
| **Alumnos en Asignaturas de 2 Meses** | Estudiantes que no rematriculan porque cursan una asignatura de duración extendida | Columna "2° Mes" del Word |

### 3.2 Indicadores Estratégicos Absolutos (Cifras Enteras)

| Indicador | Fórmula | Interpretación |
|---|---|---|
| **Pérdida de Conversión Comercial** | `Admitidos − Admitidos Matriculados` | Cuántos prospectos viables se cayeron en el último paso. Mide la "fuga del embudo" comercial. |
| **Deserción Neta** | `No matriculados − Recuperados` | Saldo real del abandono. Si recuperas más de lo que pierdes, el resultado es negativo (bueno). |
| **Brecha de Reemplazo** | `Egresados − Admitidos Matriculados` | Si es positivo, el programa pierde masa crítica porque egresan más de los que entran como nuevos. |
| **Crecimiento Neto Estudiantil** | `(Adm.Mat. + Recuperados) − (No matriculados + Egresados)` | Balance final entre todo lo que entra y todo lo que sale. Pulso vital de crecimiento institucional. |
| **Balance de Retención** | `Recuperados − No matriculados` | Saldo neto de la gestión de fidelización en números absolutos. |

### 3.3 Indicadores Estratégicos Relativos (Tasas %)

| Indicador | Fórmula | Excepciones | Interpretación |
|---|---|---|---|
| **Tasa Efectividad Comercial** | `(Adm.Mat. / Admitidos) × 100` | — | % de cierre de ventas. ≥70% = bueno. |
| **Tasa Éxito Retención** | `(Recuperados / No matriculados) × 100` | Si No matriculados = 0 → `N/A*` | % de alumnos rescatados sobre el total de fugas. |
| **Tasa Renovación Genuina** | `(Adm.Mat. / Matríc. Distancia) × 100` | Si Matríc. Distancia = 0 → `N/A*` | % de inyección de nuevos sobre la base existente. |
| **Proporción de Matrícula en Cierre** | `(Presencial / TOTAL) × 100` | Solo aplica para Pregrado | % de la población que está en planes presenciales antiguos (cuenta regresiva). |
| **Tasa de Deserción Mensual** | `(No matriculados / Total) × 100` | — | Benchmark: ≤15% Pregrado, ≤5% Posgrado (estándar MINEDU). |

### 3.4 ¿Por qué el Crecimiento Neto no cuadra con la variación del Total?

> **Explicación clave**: Los "Alumnos en Asignaturas de 2 Meses" generan una discrepancia entre el Crecimiento Neto (fórmula de flujos) y la variación observada en el Total de Matriculados (dato transaccional).
>
> - **Crecimiento Neto** = flujo de personas (entradas − salidas)
> - **Total Matriculados** = transacciones de matrícula de ese mes
>
> Un alumno que cursa una asignatura de 2 meses **no aparece como "No matriculado"** (no es una salida), pero **tampoco suma en el Total** del mes actual (no hizo transacción). Temporalmente "desaparece" del conteo transaccional, creando el desfase.

---

## 4. Catálogo de Visualizaciones y Análisis

### 4.1 Tarjetas KPI Interactivas (5 tarjetas)

Cada tarjeta es clickeable y abre un modal educativo con: fórmula, interpretación general, análisis de la cifra actual, y recomendaciones.

| Tarjeta | Color | Métrica | Subtexto |
|---|---|---|---|
| Total Matriculados | 🔵 Azul | Población activa total | Distancia + Presencial |
| Crecimiento Neto | 🟢 Verde | Entradas vs Salidas | +/− alumnos netos |
| Efectividad Comercial | 🟣 Púrpura | % cierre de ventas | (N admitidos matriculados) |
| Balance de Retención | 🟡 Ámbar | Recuperados − Fugas | Rec: X | Fuga: Y |
| Tasa Deserción | 🔴 Rojo | % bajas / total activos | (N no matriculados) |

### 4.2 Gráficos del Mes Actual (5 gráficos)

| Gráfico | Tipo Chart.js | ¿Qué muestra? |
|---|---|---|
| **Embudo de Captación Comercial** | `bar` (horizontal) | Admitidos → Pagaron → Pérdida. Visualiza la fuga del embudo de ventas. |
| **Dinámica de Flujo: Entradas vs Salidas** | `bar` (stacked) | Barras verdes (Nuevos + Recuperados) contra rojas (Egresados + No matriculados). |
| **Composición de Matrícula** | `doughnut` | Distancia vs Presencial (solo Pregrado/Institucional). Muestra la cuenta regresiva de planes antiguos. |
| **Brecha de Reemplazo** | `bar` | Ingresos nuevos vs Egresados. ¿Las ventas nuevas superan a los graduados? |
| **Captación vs Deserción Bruta** | `bar` | Nuevos vs No matriculados. El "Síndrome de la Cubeta Agujereada" (Leaky Bucket). |

### 4.3 Evolución Histórica (5 gráficos temporales)

| Gráfico | Tipo | ¿Qué muestra? |
|---|---|---|
| **Total Matriculados Activos** | `line` (multicurva) | 4 líneas: Total, Nuevos Admitidos, Recuperados, Desertores. Vista panorámica completa. |
| **Evolución Crecimiento Neto** | `line` (fill) | Curva del crecimiento neto mes a mes. Identifica estacionalidades. |
| **Tendencia Efectividad Comercial** | `line` (fill) | Evolución del % de conversión. Escala fija 0–100%. |
| **Tasa Deserción vs Benchmark** | `bar` + plugin línea | Barras mensuales con línea punteada roja de límite máximo (5% Posgrado / 15% Pregrado). |
| **Histórico Captación vs Deserción** | `line` (doble) | Dos curvas superpuestas: verde (Captación) vs roja (Deserción). Cruces = "recesión técnica". |

### 4.4 Análisis Estratégico Avanzado (5 gráficos)

| Gráfico | Tipo | ¿Qué muestra? |
|---|---|---|
| **Matriz Estratégica BCG** | `bubble` + plugin cuadrantes | Eje X: Efectividad Comercial (%). Eje Y: Balance Retención (absoluto). Burbuja: tamaño del programa. Cuadrantes: Estrellas / Dormidos / Fugas / Críticos. |
| **Comparativa: Total Matriculados** | `line` (multicolor) | Pregrado vs Posgrado (vista Institucional) o todos los programas del nivel seleccionado. |
| **Comparativa: Crecimiento Neto** | `line` (multicolor) | Misma lógica comparativa para el crecimiento. |
| **Comparativa: Efectividad Comercial** | `line` (multicolor) | Evolución del % de conversión por programa o nivel. |
| **Comparativa: Balance Retención** | `line` (multicolor) | Evolución del balance de retención por programa o nivel. |

### 4.5 Panel de Diagnóstico + IA

| Componente | Descripción |
|---|---|
| **Diagnóstico automático (reglas)** | Texto generado por JavaScript según umbrales: crecimiento ±, balance retención ±, tasa deserción vs benchmark. Se actualiza instantáneamente con cada cambio de filtro. |
| **Análisis con Gemini AI** | Botón "✨ Analizar con IA" que envía los KPIs actuales a Gemini 2.5 Flash. Retorna diagnóstico ejecutivo (2 párrafos) + 3 recomendaciones accionables. Solo funciona dentro de Google Apps Script. |

### 4.6 Panel Comparativo vs Nivel Institucional

| Componente | Descripción |
|---|---|
| Efectividad Ventas vs Media | Compara el programa seleccionado contra el promedio de todos los programas del nivel. Badge: ▲ Sobre Media / ▼ Bajo Media. |
| Balance Retención vs Media | Misma comparación para el balance de retención. |
| Crecimiento Neto vs Media | Misma comparación para el crecimiento neto. |

### 4.7 Modales Educativos (13 modales)

Cada gráfico y KPI tiene un botón ℹ️ que abre un modal con 5 secciones:

1. **¿Cómo se calcula?** — Fórmula exacta
2. **¿Por qué es importante?** — Contexto estratégico
3. **¿Cómo se interpreta?** — Parámetros de evaluación y umbrales
4. **Análisis de tu cifra actual** — Interpretación personalizada con los datos del filtro activo
5. **Impacto Estratégico y Recomendaciones** — Acciones directas sugeridas

---

## 5. Estructura de Datos

### Esquema de la Hoja Google Sheets — Pestaña "Pregrado"

```
| Mes | Programa | Egresados | No matrí. | Admitidos | Admitidos Matriculados | Recuperados |
| Matríc. regular a Distancia | Matríc. regular Presencial | Estudiantes matrí. TOTAL |
| Alumnos en Asignaturas de 2 Meses |
| Pérdida de Conversión Comercial(...) | Deserción Neta(...) | Brecha de Reemplazo(...) |
| Crecimiento Neto Estudiantil(...) | Tasa Efectividad Comercial(...) |
| Tasa Éxito Retención(...) | Tasa Renovación Genuina(...) |
| Proporción de Matrícula en Cierre(...) |
```

### Esquema de la Hoja Google Sheets — Pestaña "Posgrado"

Igual que Pregrado pero **sin** las columnas: `Matríc. regular Presencial` y `Proporción de Matrícula en Cierre`.

### Reconocimiento Inteligente de Columnas

El backend (`Código.gs`) usa un sistema de búsqueda de columnas tolerante a errores:

```javascript
const getIdx = (possibleNames) => {
  // 1. Coincidencia exacta
  // 2. Coincidencia parcial (includes)
};
```

Esto significa que si el encabezado dice "No matrí." o "No matri" o "abandono", el sistema lo reconocerá automáticamente.

---

## 6. Guía de Despliegue

### Requisitos previos

1. Cuenta Google con acceso a Google Apps Script
2. Google Sheets con ID: `1rOv812dEhB0uT4DGwNnVEqJLWfhFfTmpWohLYcaZB28`
3. API Key de Gemini activa (ya incluida en `Código.gs`)

### Pasos para desplegar

1. Abrir [Google Apps Script](https://script.google.com)
2. Crear un proyecto nuevo vinculado al Google Sheets
3. Pegar el contenido de `Código.gs` en el archivo `Código.gs`
4. Crear un archivo HTML llamado `Index` y pegar el contenido de `index.html`
5. Desplegar como **Aplicación Web**:
   - Ejecutar como: Tu cuenta
   - Acceso: Cualquier persona con el enlace
6. Usar la URL generada para acceder al dashboard

### Para actualizar datos mensuales

1. Proporcionar los dos documentos Word del mes al asistente IA
2. La IA generará los CSV con las métricas calculadas
3. Pegar los CSV en las pestañas correspondientes de Google Sheets
4. El dashboard se actualiza automáticamente al recargar

---

*Documentación generada: Mayo 2026 — Ciclo Académico 2026-I*

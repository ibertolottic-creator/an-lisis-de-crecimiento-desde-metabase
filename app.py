import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from config.settings import PERIODO_ACTUAL

st.set_page_config(page_title="Dashboard Académico Avanzado", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Sistema de Análisis Estratégico y Deserción - USMP")
st.markdown("Dashboard interactivo para visualizar métricas clave y factores de riesgo para Machine Learning.")

@st.cache_data
def load_data(mtime):
    file_path = "Cuadro_Mando_Pregrado_Calculado.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        
        # Normalizar nombres de columnas (manejar codificación de tildes y caracteres especiales)
        new_cols = {}
        for col in df.columns:
            c = col.lower()
            # Identificar columna Año (maneja Ao, Ao, etc)
            if ("a" in c and "o" in c and len(c) <= 4) or "ao" in c:
                new_cols[col] = "Año"
            # Identificar columnas de Deserción
            elif "deser" in c:
                if "7-12" in c: new_cols[col] = "Deserción Tardía (7-12m)"
                elif ">12" in c or "1 a" in c or "muy" in c: new_cols[col] = "Deserción Muy Tardía (>12m)"
                elif "temprana" in c or "3-6" in c: new_cols[col] = "Deserción Temprana (3-6m)"
                elif "1m" in c: new_cols[col] = "Riesgo Deserción (1m)"
                elif "2m" in c: new_cols[col] = "Riesgo Deserción (2m)"
            elif "egresado" in c:
                new_cols[col] = "Egresados"
            elif "recuperado" in c:
                new_cols[col] = "Recuperados"
            elif "admitido" in c and "matri" in c:
                new_cols[col] = "Admitidos Matriculados"
            elif "matr" in c and "total" in c:
                new_cols[col] = "Estudiantes matrí. TOTAL"
        
        df.rename(columns=new_cols, inplace=True)
        
        # Fallback para Año si no se detectó
        if 'Año' not in df.columns and 'Periodo_Real' in df.columns:
            df['Año'] = df['Periodo_Real'].str.split('-').str[0]
        
        if 'Año' in df.columns:
            df['Año'] = df['Año'].astype(str)
        
        if 'Mes' in df.columns:
            df['Mes'] = df['Mes'].astype(str)
        
        if 'Periodo_Real' not in df.columns and 'Año' in df.columns and 'Mes' in df.columns:
            df['Periodo_Real'] = df['Año'] + "-" + df['Mes']
        
        # Filtro: No considerar meses futuros (evita falsas deserciones)
        # Convertimos PERIODO_ACTUAL (int YYYYMM) a string YYYY-MM
        anio_hoy = PERIODO_ACTUAL // 100
        mes_hoy = PERIODO_ACTUAL % 100
        periodo_max = f"{anio_hoy}-{mes_hoy:02d}"
        
        df = df[df['Periodo_Real'] <= periodo_max].copy()
        
        return df
    return pd.DataFrame()

def load_cursos_data(mtime):
    file_path = "Asignaturas_Desaprobados_Historico.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if 'Año' in df.columns:
            df['Año'] = df['Año'].astype(str)
        if 'Periodo_Real' in df.columns:
            df['Periodo_Real'] = df['Periodo_Real'].astype(str)
        return df
    return pd.DataFrame()

@st.cache_data
def load_longitudinal_data(mtime):
    file_path = "Dataset_Longitudinal_ML.csv"
    if os.path.exists(file_path):
        return pd.read_csv(file_path, low_memory=False)
    return pd.DataFrame()

file_path = "Cuadro_Mando_Pregrado_Calculado.csv"
mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
df = load_data(mtime)

file_path_cursos = "Asignaturas_Desaprobados_Historico.csv"
mtime_cursos = os.path.getmtime(file_path_cursos) if os.path.exists(file_path_cursos) else 0
df_cursos = load_cursos_data(mtime_cursos)

file_path_long = "Dataset_Longitudinal_ML.csv"
mtime_long = os.path.getmtime(file_path_long) if os.path.exists(file_path_long) else 0
df_long = load_longitudinal_data(mtime_long)

if df.empty:
    st.warning("No se encontraron datos. Ejecuta `python etl_processor.py` primero.")
else:
    st.sidebar.header("⚙️ Filtros Principales")
    
    años_disponibles = sorted(df['Año'].unique().tolist())
    años_seleccionados = st.sidebar.multiselect("Seleccionar Año(s)", años_disponibles, default=años_disponibles[-1:])
    
    if not años_seleccionados:
        st.warning("Por favor, selecciona al menos un año.")
        st.stop()
        
    df_filtrado_año = df[df['Año'].isin(años_seleccionados)]
    
    # --- FILTROS JERÁRQUICOS ---
    st.sidebar.markdown("---")
    
    # Asegurar que las nuevas columnas existan (evitar KeyError si el CSV es antiguo)
    for c in ['Gestion', 'Facultad', 'Modalidad_Agrupada']:
        if c not in df_filtrado_año.columns:
            df_filtrado_año[c] = "No clasificado"
            df[c] = "No clasificado"
    
    # 1. Filtro Gestión
    gestiones = ["Todos"] + sorted([str(x) for x in df_filtrado_año['Gestion'].unique() if pd.notnull(x)])
    gestion_sel = st.sidebar.selectbox("Gestión (Origen)", gestiones)
    df_f = df_filtrado_año.copy()
    if gestion_sel != "Todos":
        df_f = df_f[df_f['Gestion'] == gestion_sel]
        
    # 2. Filtro Facultad
    facultades = ["Todas"] + sorted([str(x) for x in df_f['Facultad'].unique() if pd.notnull(x)])
    facultad_sel = st.sidebar.selectbox("Facultad", facultades)
    if facultad_sel != "Todas":
        df_f = df_f[df_f['Facultad'] == facultad_sel]
        
    # 3. Filtro Modalidad
    modalidades = ["Todas"] + sorted([str(x) for x in df_f['Modalidad_Agrupada'].unique() if pd.notnull(x)])
    modalidad_sel = st.sidebar.selectbox("Modalidad Agrupada", modalidades)
    if modalidad_sel != "Todas":
        df_f = df_f[df_f['Modalidad_Agrupada'] == modalidad_sel]
        
    # 4. Filtro Programa (Dependiente de los anteriores)
    programas_disponibles = ["Todos (Filtrados)"] + sorted([str(x) for x in df_f['Programa'].unique() if pd.notnull(x)])
    programa_seleccionado = st.sidebar.selectbox("Seleccionar Programa Específico", programas_disponibles)
    
    st.sidebar.markdown("---")
    meses_disponibles = sorted([str(x) for x in df_filtrado_año['Mes'].unique() if pd.notnull(x)])
    mes_seleccionado = st.sidebar.selectbox("Seleccionar Mes para KPIs", meses_disponibles, index=len(meses_disponibles)-1 if meses_disponibles else 0)
    
    # -----------------------------------------------------
    # CÁLCULOS DE LÍNEA DE TIEMPO (Histórico, 6m, Actual)
    # -----------------------------------------------------
    # Usar df_f como base si se selecciona "Todos (Filtrados)"
    if programa_seleccionado == "Todos (Filtrados)":
        df_base = df_f.copy()
        # Para el histórico completo (df_full_prog), aplicamos los mismos filtros excepto el de año
        df_full_prog = df.copy()
        if gestion_sel != "Todos": df_full_prog = df_full_prog[df_full_prog['Gestion'] == gestion_sel]
        if facultad_sel != "Todas": df_full_prog = df_full_prog[df_full_prog['Facultad'] == facultad_sel]
        if modalidad_sel != "Todas": df_full_prog = df_full_prog[df_full_prog['Modalidad_Agrupada'] == modalidad_sel]
    else:
        df_base = df_f[df_f['Programa'] == programa_seleccionado]
        df_full_prog = df[df['Programa'] == programa_seleccionado]
        
    df_timeline_full = df_full_prog.groupby(['Periodo_Real', 'Año', 'Mes']).sum(numeric_only=True).reset_index()
    df_timeline_full = df_timeline_full.sort_values('Periodo_Real').reset_index(drop=True)
    
    año_anchor = max(años_seleccionados)
    anchor_idx = df_timeline_full.index[(df_timeline_full['Año'] == año_anchor) & (df_timeline_full['Mes'] == mes_seleccionado)].tolist()
    
    # Inicializar variables (Evitar NameError si anchor_idx es vacío)
    admitidos_mat_curr = admitidos_mat_3m = admitidos_mat_6m = admitidos_mat_12m = admitidos_mat_hist = 0
    recuperados_curr = recuperados_3m = recuperados_6m = recuperados_12m = recuperados_hist = 0
    crecimiento_curr = crecimiento_3m = crecimiento_6m = crecimiento_12m = crecimiento_hist = 0
    traslados_curr = convalidados_curr = regulares_curr = 0
    total_matriculados = 0
    riesgo_1 = riesgo_2 = temprana = tardia = muy_tardia = 0
    perm_0m = perm_1m = perm_incontinuo = reinc_6_12_curr = reinc_gt12_curr = 0
    retenidos_1m = 0
    
    if anchor_idx:
        idx = anchor_idx[0]
        df_current = df_timeline_full.iloc[[idx]]
        df_3m = df_timeline_full.iloc[max(0, idx - 2):idx+1]
        df_6m = df_timeline_full.iloc[max(0, idx - 5):idx+1]
        df_12m = df_timeline_full.iloc[max(0, idx - 11):idx+1]
        df_24m = df_timeline_full.iloc[max(0, idx - 23):idx+1]
        df_60m = df_timeline_full.iloc[max(0, idx - 59):idx+1]
        df_hist = df_timeline_full.iloc[:idx+1]
        
        # Métrica: Admitidos (Sumas rodantes)
        admitidos_mat_curr = df_current['Admitidos Matriculados'].sum()
        admitidos_mat_3m = df_3m['Admitidos Matriculados'].sum()
        admitidos_mat_6m = df_6m['Admitidos Matriculados'].sum()
        admitidos_mat_12m = df_12m['Admitidos Matriculados'].sum()
        admitidos_mat_24m = df_24m['Admitidos Matriculados'].sum()
        admitidos_mat_60m = df_60m['Admitidos Matriculados'].sum()
        admitidos_mat_hist = df_hist['Admitidos Matriculados'].sum()
        
        # Desglose Admitidos (Mes actual)
        traslados_curr = df_current.get('Nuevos Traslados', pd.Series([0])).sum()
        convalidados_curr = df_current.get('Nuevos Convalidados', pd.Series([0])).sum()
        regulares_curr = admitidos_mat_curr - traslados_curr - convalidados_curr
        
        # Métrica: Permanencia (nuevas categorías)
        perm_0m = df_current.get('Perm. Siempre (0m)', pd.Series([0])).sum()
        perm_1m = df_current.get('Perm. 1mes', pd.Series([0])).sum()
        perm_incontinuo = df_current.get('Permanentes Incontinuos', pd.Series([0])).sum()
        reinc_6_12_curr = df_current.get('Reincorporados (6-12m)', pd.Series([0])).sum()
        reinc_gt12_curr = df_current.get('Reincorporados (>12m)', pd.Series([0])).sum()
        
        # Métrica: Crecimiento Neto
        def calc_crecimiento(d):
            # Recuperados = quienes regresan tras ausencia (1m + 2-5m + 6-12m + >12m)
            recup = (d.get('Perm. 1mes', pd.Series([0])).sum() + 
                     d.get('Permanentes Incontinuos', pd.Series([0])).sum() + 
                     d.get('Reincorporados (6-12m)', pd.Series([0])).sum() + 
                     d.get('Reincorporados (>12m)', pd.Series([0])).sum())
            ent = d['Admitidos Matriculados'].sum() + recup
            sal = d.get('Riesgo Deserción (1m)', pd.Series([0])).sum() + d['Egresados'].sum()
            return ent - sal
            
        crecimiento_curr = calc_crecimiento(df_current)
        crecimiento_3m = calc_crecimiento(df_3m)
        crecimiento_6m = calc_crecimiento(df_6m)
        crecimiento_12m = calc_crecimiento(df_12m)
        crecimiento_24m = calc_crecimiento(df_24m)
        crecimiento_60m = calc_crecimiento(df_60m)
        crecimiento_hist = calc_crecimiento(df_hist)

        # Variables actuales
        total_matriculados = df_current['Estudiantes matrí. TOTAL'].sum()
        riesgo_1 = df_current.get('Riesgo Deserción (1m)', pd.Series([0])).sum()
        riesgo_2 = df_current.get('Riesgo Deserción (2m)', pd.Series([0])).sum()
        temprana = df_current.get('Deserción Temprana (3-6m)', pd.Series([0])).sum()
        tardia = df_current.get('Deserción Tardía (7-12m)', pd.Series([0])).sum()
        muy_tardia = df_current.get('Deserción Muy Tardía (>12m)', pd.Series([0])).sum()
        retenidos_1m = perm_0m + perm_1m
    
    desercion_total = riesgo_1 + riesgo_2 + temprana + tardia + muy_tardia
    
    st.subheader(f"Métricas Estratégicas: {mes_seleccionado} {año_anchor}")
    
    # ---------------------------------------------
    # NUEVO DISEÑO EN PESTAÑAS (TABS)
    # ---------------------------------------------
    st.metric("👥 Total Matriculados (Mes Activo)", int(total_matriculados))
    
    tab_crec, tab_adm, tab_perm = st.tabs(["📈 Crecimiento Neto", "🎯 Admitidos Matriculados", "🛡️ Permanentes y Reincorporados"])
    
    with tab_crec:
        st.info("💡 **Fórmula:** Ingresos (Nuevos + Recuperados) - Fugas del Mes (Riesgo 1m + Egresados). Mide si la universidad sumó o perdió alumnos reales.")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Este Mes", int(crecimiento_curr))
        c2.metric("Últ. 3 Meses", int(crecimiento_3m))
        c3.metric("Últ. 6 Meses", int(crecimiento_6m))
        c4.metric("Últ. Año", int(crecimiento_12m))
        c5.metric("Últ. 2 Años", int(crecimiento_24m))
        c6.metric("Últ. 5 Años", int(crecimiento_60m))
        c7.metric("Crecimiento Neto", int(crecimiento_hist))

        # --- NUEVA GRÁFICA DE DINÁMICA DE CRECIMIENTO ---
        st.markdown("### 📊 Dinámica de Crecimiento: Entradas vs Salidas")
        st.info("Este gráfico explica el Crecimiento Neto mostrando las **Entradas** (barras hacia arriba) y las **Salidas** (barras hacia abajo). La línea de puntos representa el saldo final de cada mes.")
        
        df_flow = df_timeline_full.copy()
        # Aseguramos que las salidas sean negativas para el gráfico
        df_flow['Fuga (Riesgo 1m)'] = -df_flow['Riesgo Deserción (1m)']
        df_flow['Egresados_Neg'] = -df_flow['Egresados']
        
        fig_flow = go.Figure()
        
        # Barras de Entradas (Positivas)
        fig_flow.add_trace(go.Bar(
            x=df_flow['Periodo_Real'], y=df_flow['Admitidos Matriculados'],
            name='Nuevos (Admitidos)', marker_color='#636EFA',
            hovertemplate='%{y} nuevos alumnos'
        ))
        # Recuperados = quienes regresan (1 mes + 2-5m + 6-12m + >12m)
        recuperados_flow = (
            df_flow.get('Perm. 1mes', 0) +
            df_flow.get('Permanentes Incontinuos', 0) +
            df_flow.get('Reincorporados (6-12m)', 0) +
            df_flow.get('Reincorporados (>12m)', 0)
        )
        fig_flow.add_trace(go.Bar(
            x=df_flow['Periodo_Real'], y=recuperados_flow,
            name='Recuperados', marker_color='#00CC96',
            hovertemplate='%{y} recuperados'
        ))
        
        # Barras de Salidas (Negativas)
        fig_flow.add_trace(go.Bar(
            x=df_flow['Periodo_Real'], y=df_flow['Fuga (Riesgo 1m)'],
            name='Desertores (Riesgo 1m)', marker_color='#EF553B',
            hovertemplate='%{y} desertores'
        ))
        fig_flow.add_trace(go.Bar(
            x=df_flow['Periodo_Real'], y=df_flow['Egresados_Neg'],
            name='Egresados', marker_color='#7F7F7F',
            hovertemplate='%{y} egresados'
        ))
        
        # Línea de Saldo (Crecimiento Neto)
        # Calculamos el saldo para la línea
        # Saldo Neto actualizado
        df_flow['Saldo_Neto'] = (df_flow['Admitidos Matriculados']
            + df_flow.get('Perm. 1mes', 0)
            + df_flow.get('Permanentes Incontinuos', 0)
            + df_flow.get('Reincorporados (6-12m)', 0)
            + df_flow.get('Reincorporados (>12m)', 0)
            + df_flow['Fuga (Riesgo 1m)']
            + df_flow['Egresados_Neg'])
        
        fig_flow.add_trace(go.Scatter(
            x=df_flow['Periodo_Real'], y=df_flow['Saldo_Neto'],
            name='Saldo Crecimiento Neto',
            line=dict(color='#FECB52', width=4, dash='dot'),
            mode='lines+markers'
        ))

        fig_flow.update_layout(
            barmode='relative',
            title="Explicación del Crecimiento Neto (Flujos Mensuales)",
            xaxis_title="Mes / Periodo",
            yaxis_title="Cantidad de Alumnos",
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig_flow, use_container_width=True)

    with tab_adm:
        st.info("💡 **Fórmula:** Cantidad de Alumnos que ingresaron por primera vez al programa.")
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("Este Mes", int(admitidos_mat_curr))
        c2.metric("Últ. 3 Meses", int(admitidos_mat_3m))
        c3.metric("Últ. 6 Meses", int(admitidos_mat_6m))
        c4.metric("Últ. Año", int(admitidos_mat_12m))
        c5.metric("Últ. 2 Años", int(admitidos_mat_24m))
        c6.metric("Últ. 5 Años", int(admitidos_mat_60m))
        c7.metric("Desde el inicio", int(admitidos_mat_hist))
        
        st.markdown("**Desglose de Admitidos (Este Mes):**")
        d1, d2, d3 = st.columns(3)
        d1.metric("Regulares", int(regulares_curr))
        d2.metric("Por Traslado", int(traslados_curr))
        d3.metric("Por Convalidación", int(convalidados_curr))

    with tab_perm:
        st.info("""💡 **Clasificación de Permanencia (Comportamiento de Matrícula):**
        - **Permanente Continuo (0m):** Siempre matriculado, nunca ha faltado.
        - **Permanente Continuo (1m):** Regresa tras solo 1 mes de ausencia.
        - **Permanente Incontinuo (2-5m):** Regresa tras una ausencia corta.
        - **Reincorporado (6-12m):** Regresa tras 6 meses a 1 año.
        - **Reincorporado (>1 año):** Regresa tras más de 12 meses.
        """)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🌲 Perm. (0 meses)", int(perm_0m))
        c2.metric("🌿 Perm. (1 mes)", int(perm_1m))
        c3.metric("🟡 Perm. Incontinuos", int(perm_incontinuo))
        c4.metric("🟤 Reinc. (6-12m)", int(reinc_6_12_curr))
        c5.metric("⚫ Reinc. (>1 año)", int(reinc_gt12_curr))
        
    st.markdown("### 📊 Evolución y Balance de la Matrícula")
    st.info("Este gráfico presenta el balance mensual de la universidad: sobre el eje cero se muestra la **Matrícula Activa** (Nuevos, Recuperados y Retenidos); bajo el eje cero se muestra la **Pérdida de Masa** (Desertores y Egresados).")
    
    # Preparar datos para el balance completo
    df_balance = df_timeline_full.copy()
    
    # Componentes Positivos (Parte superior)
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Perm. Siempre (0m)', 0),
        name='🌲 Perm. Continuo (0m)', marker_color='#006400',
        hovertemplate='%{y} perm. 0m'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Perm. 1mes', 0),
        name='🌿 Perm. Continuo (1m)', marker_color='#00CC96',
        hovertemplate='%{y} perm. 1m'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Permanentes Incontinuos', 0),
        name='🟡 Permanentes Incontinuos (2-5m)', marker_color='#FFA15A',
        hovertemplate='%{y} perm. incontinuos'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Reincorporados (6-12m)', 0),
        name='🟤 Reincorporados (6-12m)', marker_color='#FFEC45',
        hovertemplate='%{y} reinc. 6-12m'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Reincorporados (>12m)', 0),
        name='⚫ Reincorporados (>12m)', marker_color='#343a40',
        hovertemplate='%{y} reinc. >12m'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance['Admitidos Matriculados'],
        name='🔵 Nuevos (Ingresos)', marker_color='#636EFA',
        hovertemplate='%{y} nuevos'
    ))
    # Componentes Negativos (Parte inferior)
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=-df_balance['Riesgo Deserción (1m)'],
        name='🟠 Riesgo Deser. (1m)', marker_color='#FF7F0E',
        hovertemplate='%{y} riesgo 1m'
    ))
    # Riesgo 2m: desactivado por defecto (click en leyenda para activar)
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=-df_balance.get('Riesgo Deserción (2m)', 0),
        name='🟡 Riesgo Deser. (2m)', marker_color='#FFC107',
        hovertemplate='%{y} riesgo 2m',
        visible='legendonly'
    ))
    # Temprana: desactivada por defecto (click en leyenda para activar)
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=-df_balance.get('Deserción Temprana (3-6m)', 0),
        name='🔴 Deserción Temprana (3-6m)', marker_color='#D62728',
        hovertemplate='%{y} deser. temprana',
        visible='legendonly'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=-df_balance['Egresados'],
        name='⚪ Egresados (Salidas)', marker_color='#7F7F7F',
        hovertemplate='%{y} egresados'
    ))
    # Línea de Total Activo
    fig_bal.add_trace(go.Scatter(
        x=df_balance['Periodo_Real'], y=df_balance['Estudiantes matrí. TOTAL'],
        name='Población Total Activa',
        line=dict(color='#1f77b4', width=4),
        mode='lines+markers'
    ))

    fig_bal.update_layout(
        barmode='relative',
        title="Balance Mensual: Composición vs Pérdida de Matrícula",
        xaxis_title="Periodo / Mes",
        yaxis_title="Cantidad de Alumnos",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )
    
    st.plotly_chart(fig_bal, use_container_width=True)
    
    st.markdown("### ⚠️ Análisis de Deserción Escalonada (Mes Seleccionado)")
    col_d1, col_d2, col_d3, col_d4, col_d5, col_d6 = st.columns(6)
    col_d1.metric("🚨 Deserción Total", int(desercion_total))
    col_d2.metric("🟡 Riesgo (1m)", int(riesgo_1), delta_color="off")
    col_d3.metric("🟠 Riesgo (2m)", int(riesgo_2), delta_color="off")
    col_d4.metric("🔴 Temprana (3-6m)", int(temprana), delta_color="off")
    col_d5.metric("🟤 Tardía (7-12m)", int(tardia), delta_color="off")
    col_d6.metric("⚫ Crítica (>1 año)", int(muy_tardia), delta_color="off")
    
    st.markdown("---")
    st.subheader("Visualizaciones Temporales")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histograma de Deserciones en el tiempo
        cols_des = ['Riesgo Deserción (1m)', 'Riesgo Deserción (2m)', 'Deserción Temprana (3-6m)', 'Deserción Tardía (7-12m)', 'Deserción Muy Tardía (>12m)']
        df_trend = df_base.groupby('Periodo_Real')[cols_des].sum().reset_index()
            
        fig_des = px.bar(df_trend, x='Periodo_Real', y=cols_des,
                         title="Evolución de Deserción Escalonada",
                         labels={'value': 'Cantidad de Alumnos', 'variable': 'Tipo de Deserción'},
                         color_discrete_map={
                             'Riesgo Deserción (1m)': '#ffdf7e', 
                             'Riesgo Deserción (2m)': '#ffc107', 
                             'Deserción Temprana (3-6m)': '#fd7e14', 
                             'Deserción Tardía (7-12m)': '#a52a2a', 
                             'Deserción Muy Tardía (>12m)': '#343a40'
                         })
        fig_des.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig_des, use_container_width=True)
        
    with col2:
        df_mat = df_base.groupby('Periodo_Real')['Estudiantes matrí. TOTAL'].sum().reset_index()
        fig_trend = px.line(df_mat, x='Periodo_Real', y='Estudiantes matrí. TOTAL', title="Evolución Histórica de Matrícula", markers=True)
        fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=350)
        fig_trend.update_traces(line_color='#1f77b4', line_width=3)
        st.plotly_chart(fig_trend, use_container_width=True)
        
    st.markdown("---")
    st.subheader("🔍 Análisis Exploratorio (Causas de Deserción)")
    st.info("Utiliza estos análisis para profundizar en las razones académicas y estructurales de la deserción.")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Asignaturas Críticas", "🏛️ Programas con Mayor Riesgo", "⚖️ Matriz de Riesgo (Intervención)", "🤖 ML: Predicción de Retorno"])
    
    # Configuración de ventanas de tiempo
    windows = {
        "Mes Seleccionado": 1,
        "Últimos 2 Meses": 2,
        "Últimos 3 Meses": 3,
        "Últimos 6 Meses": 6,
        "Último Año": 12,
        "Últimos 2 Años": 24,
        "Últimos 3 Años": 36,
        "Últimos 5 Años": 60
    }
    
    with tab1:
        win_c = st.selectbox("Ventana de tiempo (Asignaturas):", list(windows.keys()), key="win_c")
        n_meses = windows[win_c]
        
        if win_c == "Mes Seleccionado":
            st.warning("⚠️ **Nota:** Si el mes seleccionado está en curso, es posible que aún no existan calificaciones finales (desaprobados) ni se haya confirmado la deserción para el mes siguiente.")
        
        # Filtrar df_cursos por ventana
        if not df_cursos.empty and anchor_idx:
            # Obtener periodos válidos
            periodo_anchor = df_timeline_full.iloc[anchor_idx[0]]['Periodo_Real']
            periodos_validos = df_timeline_full['Periodo_Real'].unique().tolist()
            idx_p = periodos_validos.index(periodo_anchor)
            periodos_ventana = periodos_validos[max(0, idx_p - n_meses + 1):idx_p+1]
            
            df_c_win = df_cursos[df_cursos['Periodo_Real'].isin(periodos_ventana)]
            if programa_seleccionado != "Todos (Filtrados)":
                df_c_win = df_c_win[df_c_win['Programa_Base'] == programa_seleccionado]
            
            if not df_c_win.empty:
                agg_dict = {'Desaprobado': 'sum', 'Desercion': 'sum', 'Total_Alumnos': 'sum'}
                
                top_cursos = df_c_win.groupby('Asignatura').agg(agg_dict).reset_index()
                top_cursos['Tasa_Reprobación'] = (top_cursos['Desaprobado'] / top_cursos['Total_Alumnos']) * 100
                top_cursos['Tasa_Deserción'] = (top_cursos['Desercion'] / top_cursos['Total_Alumnos']) * 100
                
                # Ordenar estrictamente por mayor cantidad absoluta de deserciones
                top_cursos = top_cursos.sort_values(by=['Desercion', 'Tasa_Deserción'], ascending=False).head(15)
                
                top_cursos['Asignatura_Label'] = top_cursos.apply(lambda r: f"{r['Asignatura']} ({r['Tasa_Deserción']:.1f}% deserción)", axis=1)
                
                fig_cursos = go.Figure()
                fig_cursos.add_trace(go.Bar(
                    y=top_cursos['Asignatura_Label'],
                    x=top_cursos['Total_Alumnos'],
                    name='Total Matriculados',
                    orientation='h', marker_color='#1f77b4',
                    hovertemplate='%{x} alumnos matriculados'
                ))
                fig_cursos.add_trace(go.Bar(
                    y=top_cursos['Asignatura_Label'],
                    x=top_cursos['Desaprobado'],
                    name='Desaprobados',
                    orientation='h', marker_color='#EF553B',
                    hovertemplate='%{x} desaprobados'
                ))
                fig_cursos.add_trace(go.Bar(
                    y=top_cursos['Asignatura_Label'],
                    x=top_cursos['Desercion'],
                    name='Deserciones',
                    orientation='h', marker_color='#FFA15A',
                    hovertemplate='%{x} desertores'
                ))
                
                fig_cursos.update_layout(
                    barmode='group', 
                    yaxis={'categoryorder':'total ascending'}, 
                    title=f"Asignaturas que más desertores generan ({win_c})",
                    plot_bgcolor="rgba(0,0,0,0)", 
                    height=650,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_cursos, use_container_width=True)
            else:
                st.info("No hay datos de asignaturas para este periodo.")

    with tab2:
        win_p = st.selectbox("Ventana de tiempo (Programas):", list(windows.keys()), key="win_p")
        n_meses_p = windows[win_p]
        # REGLA: Para ventanas menores a 12 meses, usamos un historial de 12 meses para no perder de vista los segmentos de deserción
        n_meses_calc = max(n_meses_p, 12)
        
        with st.expander("ℹ️ Metodología de Cálculo (Estado Actual)"):
            st.markdown(f"""
            Al seleccionar **{win_p}**, el gráfico muestra la **situación real al final del periodo**:
            *   **Población Total**: Alumnos únicos que pasaron por el programa en el tiempo de la ventana (para ventanas cortas se evalúa el estado de quienes estuvieron en el último año).
            *   **Barra de Deserción Acumulada**: Se construye sumando bloques de alumnos según su ausencia:
                *   🟠 **Hace 1 mes**: Recién salidos.
                *   🟠 **Hace 2 meses**: Riesgo crítico.
                *   🔴 **Hace 6 meses**: Deserción temprana (3-6m).
                *   🛑 **Hasta 1 año**: Deserción tardía (6m-1año).
            *   **Sin Duplicidad**: Cada alumno pertenece a un solo bloque según su último mes de actividad.
            """)
        
        if anchor_idx:
            periodo_anchor = df_timeline_full.iloc[anchor_idx[0]]['Periodo_Real']
            periodos_validos = df_timeline_full['Periodo_Real'].unique().tolist()
            idx_p = periodos_validos.index(periodo_anchor)
            periodos_ventana = periodos_validos[max(0, idx_p - n_meses_calc + 1):idx_p+1]
            
            # Usar df_f que ya tiene filtros de gestión/facultad
            df_p_win = df[df['Periodo_Real'].isin(periodos_ventana)]
            if gestion_sel != "Todos": df_p_win = df_p_win[df_p_win['Gestion'] == gestion_sel]
            if facultad_sel != "Todas": df_p_win = df_p_win[df_p_win['Facultad'] == facultad_sel]
            if modalidad_sel != "Todas": df_p_win = df_p_win[df_p_win['Modalidad_Agrupada'] == modalidad_sel]

            # --- CÁLCULO DINÁMICO DE ESTADO (SNAPSHOT) USANDO HISTORIAL ---
            ultimo_mes = periodos_ventana[-1]
            idx_anchor = periodos_validos.index(ultimo_mes)

            if not df_long.empty:
                # 1. POBLACIÓN ACTIVA (Sigue estrictamente la ventana del filtro)
                periodos_blue = periodos_validos[max(0, idx_p - n_meses_p + 1):idx_p+1]
                df_l_blue = df_long[df_long['Periodo_Real'].isin(periodos_blue)].copy()
                
                # 2. UNIVERSO PARA DESERCIÓN (Historial de al menos 12 meses para ver los segmentos)
                periodos_drop = periodos_validos[max(0, idx_p - n_meses_calc + 1):idx_p+1]
                df_l_drop = df_long[df_long['Periodo_Real'].isin(periodos_drop)].copy()
                
                # Exclusiones críticas
                exclusiones = ['EGRESADO', 'CONVALIDADO', 'TRASLADO INTERNO', 'TRASLADO EXTERNO']
                if 'Situación_Académica' in df_l_drop.columns:
                    df_l_drop = df_l_drop[~df_l_drop['Situación_Académica'].isin(exclusiones)]
                
                if gestion_sel != "Todos": 
                    df_l_blue = df_l_blue[df_l_blue['Gestion'] == gestion_sel]
                    df_l_drop = df_l_drop[df_l_drop['Gestion'] == gestion_sel]
                if facultad_sel != "Todas": 
                    df_l_blue = df_l_blue[df_l_blue['Facultad'] == facultad_sel]
                    df_l_drop = df_l_drop[df_l_drop['Facultad'] == facultad_sel]

                # --- CÁLCULO DE LA BARRA AZUL (Población en la Ventana Elegida) ---
                df_pop_p = df_l_blue.groupby('Programa')['DNI'].nunique().reset_index().rename(columns={'DNI': 'Total_Individuos_Ventana'})

                # --- CÁLCULO DE LA BARRA APILADA (Deserción en el Snapshot) ---
                df_last_act = df_l_drop.groupby(['Programa', 'DNI'])['Periodo_Real'].max().reset_index()
                df_last_act['Meses_Ausencia'] = df_last_act['Periodo_Real'].apply(lambda p: idx_anchor - periodos_validos.index(p) if p in periodos_validos else 999)
                
                def clasificar_d(m):
                    if m == 0: return 'Activo'
                    if m == 1: return 'D_1m'
                    if m == 2: return 'D_2m'
                    if 3 <= m <= 6: return 'D_6m'
                    if 7 <= m <= 12: return 'D_1año'
                    if 13 <= m <= 24: return 'D_2años'
                    if 25 <= m <= 36: return 'D_3años'
                    if 37 <= m <= 60: return 'D_5años'
                    return 'D_Mas'
                df_last_act['Estado'] = df_last_act['Meses_Ausencia'].apply(clasificar_d)
                
                df_p_states = df_last_act.groupby(['Programa', 'Estado']).size().unstack(fill_value=0).reset_index()
                for c in ['D_1m', 'D_2m', 'D_6m', 'D_1año', 'D_2años', 'D_3años', 'D_5años']:
                    if c not in df_p_states.columns: df_p_states[c] = 0
                
                # Unir ambos cálculos
                df_p_counts = pd.merge(df_pop_p, df_p_states, on='Programa', how='left').fillna(0)
                
                # Segmentos a mostrar según el filtro n_meses_p
                segmentos_visibles = ['D_1m', 'D_2m', 'D_6m', 'D_1año']
                if n_meses_p >= 24: segmentos_visibles.append('D_2años')
                if n_meses_p >= 36: segmentos_visibles.append('D_3años')
                if n_meses_p >= 60: segmentos_visibles.append('D_5años')
                
                # Calcular tasa de deserción acumulada (solo de los segmentos visibles)
                df_p_counts['Total_D'] = df_p_counts[segmentos_visibles].sum(axis=1)
                df_p_counts['Tasa_D'] = (df_p_counts['Total_D'] / df_p_counts['Total_Individuos_Ventana'].replace(0,1)) * 100
                df_p_counts['Programa_Label'] = df_p_counts.apply(lambda r: f"{r['Programa']} ({r['Tasa_D']:.1f}%)", axis=1)
                
                # Ordenar por población para el ranking
                top_prog = df_p_counts.sort_values(by='Total_Individuos_Ventana', ascending=False).head(15)
                
                fig_prog = go.Figure()
                
                # Barra A: Población Total (Universo de la ventana)
                fig_prog.add_trace(go.Bar(
                    y=top_prog['Programa_Label'], 
                    x=top_prog['Total_Individuos_Ventana'],
                    name='Población Total', 
                    orientation='h', 
                    marker_color='#1f77b4', 
                    offsetgroup=1,
                    text=top_prog['Total_Individuos_Ventana'].apply(lambda x: f"{x:,}"),
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>Población Total: %{x:,} alumnos únicos<extra></extra>'
                ))
                
                # Barra B (Stacked): Estado de esos alumnos
                colors = {'D_1m': '#FFA15A', 'D_2m': '#FF7F0E', 'D_6m': '#D62728', 'D_1año': '#8B0000', 
                          'D_2años': '#660000', 'D_3años': '#440000', 'D_5años': '#220000'}
                labels = {'D_1m': 'Hace 1 mes', 'D_2m': 'Hace 2 meses', 'D_6m': 'Hace 6 meses', 'D_1año': 'Hasta 1 año',
                          'D_2años': 'Hasta 2 años', 'D_3años': 'Hasta 3 años', 'D_5años': 'Hasta 5 años'}
                
                for seg in segmentos_visibles:
                    fig_prog.add_trace(go.Bar(
                        y=top_prog['Programa_Label'], 
                        x=top_prog[seg],
                        name=labels[seg], 
                        orientation='h', 
                        marker_color=colors[seg],
                        offsetgroup=2, 
                        hovertemplate='Segmento: ' + labels[seg] + '<br>Cantidad: %{x:,} alumnos<extra></extra>'
                    ))
                
                # Barra C: Etiqueta de TOTAL Deserción (Transparente para mostrar el texto al final)
                fig_prog.add_trace(go.Bar(
                    y=top_prog['Programa_Label'],
                    x=top_prog['Total_D'],
                    name='Total Deserción',
                    orientation='h',
                    marker_color='rgba(0,0,0,0)',
                    offsetgroup=2,
                    text=top_prog['Total_D'].apply(lambda x: f"Σ {x:,}"),
                    textposition='outside',
                    showlegend=False,
                    hoverinfo='skip'
                ))
                
                fig_prog.update_layout(
                    barmode='stack', 
                    yaxis={'categoryorder':'total ascending'}, 
                    title=f"Estado de Programas: Población vs Deserción Dinámica ({ultimo_mes})",
                    plot_bgcolor="rgba(0,0,0,0)", 
                    height=750,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis_title="Cantidad de Alumnos (Individuos únicos)"
                )
                st.plotly_chart(fig_prog, use_container_width=True)
            else:
                st.warning("Se requiere el Dataset Longitudinal para el análisis dinámico.")

            # --- Evolución Mensual del Riesgo (Fija a 1 año) ---
            st.markdown("#### 📈 Evolución Mensual de Nuevos Desertores (Top 5 Programas - Vista 1 Año)")
            top_5_names = top_prog['Programa'].head(5).tolist()
            
            # Forzar la ventana de tendencia a los últimos 12 meses
            periodos_12m = periodos_validos[max(0, idx_p - 11):idx_p+1]
            df_p_trend = df[df['Periodo_Real'].isin(periodos_12m) & df['Programa'].isin(top_5_names)].copy()
            df_p_trend = df_p_trend.sort_values(by='Periodo_Real')
            
            if not df_p_trend.empty:
                fig_p_trend = px.line(
                    df_p_trend, 
                    x='Periodo_Real', 
                    y='Riesgo Deserción (1m)', 
                    color='Programa',
                    title="Nuevos desertores detectados por mes (Último Año)",
                    markers=True,
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_p_trend.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", 
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                    xaxis_title="Periodo",
                    yaxis_title="Cantidad de Desertores"
                )
                st.plotly_chart(fig_p_trend, use_container_width=True)

    with tab3:
        st.markdown("### ⚖️ Correlación: Reprobación vs Deserción")
        st.info("Este gráfico identifica programas donde el bajo rendimiento académico podría estar impulsando la deserción.")
        
        if not df_cursos.empty and anchor_idx:
            # 1. Definir ventana de tiempo (6 meses) para estabilidad estadística
            periodo_anchor = df_timeline_full.iloc[anchor_idx[0]]['Periodo_Real']
            periodos_validos = df_timeline_full['Periodo_Real'].unique().tolist()
            idx_p = periodos_validos.index(periodo_anchor)
            periodos_mats = periodos_validos[max(0, idx_p - 5):idx_p+1]
            
            # 2. Filtrar df principal respetando los selectores de la barra lateral (excepto año)
            df_f_matrix = df.copy()
            if gestion_sel != "Todos":
                df_f_matrix = df_f_matrix[df_f_matrix['Gestion'] == gestion_sel]
            if facultad_sel != "Todas":
                df_f_matrix = df_f_matrix[df_f_matrix['Facultad'] == facultad_sel]
            if modalidad_sel != "Todas":
                df_f_matrix = df_f_matrix[df_f_matrix['Modalidad_Agrupada'] == modalidad_sel]

            # 3. Datos Académicos (Limpiar nombres para asegurar el merge)
            df_acad_base = df_cursos[df_cursos['Periodo_Real'].isin(periodos_mats)].copy()
            df_acad_base['Programa_Base'] = df_acad_base['Programa_Base'].str.strip()
            df_acad = df_acad_base.groupby('Programa_Base').agg({
                'Desaprobado': 'sum',
                'Total_Alumnos': 'sum'
            }).reset_index()
            df_acad['Tasa_Reprobacion'] = (df_acad['Desaprobado'] / df_acad['Total_Alumnos']) * 100
            
            # 4. Datos Deserción (Limpiar nombres para asegurar el merge)
            df_des_base = df_f_matrix[df_f_matrix['Periodo_Real'].isin(periodos_mats)].copy()
            df_des_base['Programa'] = df_des_base['Programa'].str.strip()
            df_des = df_des_base.groupby('Programa').agg({
                'Riesgo Deserción (1m)': 'sum',
                'Estudiantes matrí. TOTAL': 'mean'
            }).reset_index()
            df_des['Tasa_Deserción'] = (df_des['Riesgo Deserción (1m)'] / df_des['Estudiantes matrí. TOTAL']) * 100
            
            # 5. Merge por nombre limpio
            df_matrix = pd.merge(df_acad, df_des, left_on='Programa_Base', right_on='Programa')
            
            fig_matrix = px.scatter(df_matrix, x='Tasa_Reprobacion', y='Tasa_Deserción',
                                    size='Estudiantes matrí. TOTAL', color='Tasa_Deserción',
                                    text='Programa_Base', hover_name='Programa_Base',
                                    title="Matriz de Riesgo Académico (Ventana 6 meses)",
                                    labels={'Tasa_Reprobacion': '% Reprobación', 'Tasa_Deserción': '% Deserción (Riesgo 1m)'},
                                    color_continuous_scale='Viridis')
            
            fig_matrix.update_traces(textposition='top center')
            # Líneas de referencia (promedios)
            fig_matrix.add_hline(y=df_matrix['Tasa_Deserción'].mean(), line_dash="dot", annotation_text="Media Deserción")
            fig_matrix.add_vline(x=df_matrix['Tasa_Reprobacion'].mean(), line_dash="dot", annotation_text="Media Reprobación")
            
            fig_matrix.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=600)
            st.plotly_chart(fig_matrix, use_container_width=True)
            
            st.warning("⚠️ **Interpretación:** Los programas en el cuadrante superior derecho tienen alta reprobación y alta deserción. Requieren intervención académica urgente.")

    with tab4:
        st.markdown("### 🤖 Predicción de Retorno (Machine Learning)")
        st.info("Modelo Predictivo (Random Forest) que evalúa si un alumno que acaba de desertar (1 mes) volverá a matricularse. Basado en el historial completo del programa o grupo seleccionado.")
        
        if not df_long.empty:
            opciones_prog = ["Todos los Programas"] + sorted(df_long['Programa_Base'].dropna().unique().tolist())
            prog_ml = st.selectbox("Seleccione Programa (o Grupo) para entrenar el modelo:", opciones_prog, key="prog_ml")
            
            st.caption("ℹ️ **Nota sobre las Notas (Desaprobados):** El modelo utiliza la cantidad de cursos desaprobados que tuvo el alumno en su **último mes activo** (antes de desertar). No utiliza el mes actual porque aún está en curso y no tiene notas cerradas.")
            
            with st.spinner("Entrenando modelo predictivo Random Forest..."):
                # 1. Preparar datos y excluir egresados/convalidados/traslados
                if prog_ml == "Todos los Programas":
                    df_ml = df_long.copy()
                else:
                    df_ml = df_long[df_long['Programa_Base'] == prog_ml].copy()
                    
                exclusiones = ['EGRESADO', 'CONVALIDADO', 'TRASLADO INTERNO', 'TRASLADO EXTERNO']
                if 'Situación_Académica' in df_ml.columns:
                    df_ml = df_ml[~df_ml['Situación_Académica'].isin(exclusiones)]
                elif 'Estado_alumno_Original' in df_ml.columns:
                    df_ml = df_ml[~df_ml['Estado_alumno_Original'].isin(exclusiones)]
                
                periodos = sorted(df_ml['Periodo_Real'].unique())
                p_to_idx = {p: i for i, p in enumerate(periodos)}
                df_ml['Idx'] = df_ml['Periodo_Real'].map(p_to_idx)
                df_ml = df_ml.sort_values(['DNI', 'Idx'])
                
                # Ingeniería de Características (Nuevas Variables)
                df_ml['Meses_Estudiando'] = df_ml.groupby('DNI').cumcount() + 1
                df_ml['Primer_Idx'] = df_ml.groupby('DNI')['Idx'].transform('min')
                df_ml['Meses_Desde_Ingreso'] = df_ml['Idx'] - df_ml['Primer_Idx'] + 1
                df_ml['Tasa_Continuidad'] = (df_ml['Meses_Estudiando'] / df_ml['Meses_Desde_Ingreso']) * 100
                df_ml['Total_Desaprobados_Historico'] = df_ml.groupby('DNI')['Desaprobado'].cumsum()
                df_ml['Tasa_Reprobacion_Historica'] = df_ml['Total_Desaprobados_Historico'] / df_ml['Meses_Estudiando']
                
                if 'Cursos_Mes' in df_ml.columns:
                    df_ml['Cursos_Cursados_Historico'] = df_ml.groupby('DNI')['Cursos_Mes'].cumsum()
                    df_ml['Cursos_Aprobados_Historico'] = df_ml['Cursos_Cursados_Historico'] - df_ml['Total_Desaprobados_Historico']
                    df_ml['%_Aprobacion_Historico'] = (df_ml['Cursos_Aprobados_Historico'] / df_ml['Cursos_Cursados_Historico']) * 100
                
                # Nota histórica acumulada (Promedio de todas sus notas hasta ese momento)
                df_ml['Nota_Historica_Acumulada'] = df_ml.groupby('DNI')['Nota_Num'].expanding().mean().reset_index(0, drop=True)

                # Calcular Gaps (Ausencias)
                df_ml['Next_Idx'] = df_ml.groupby('DNI')['Idx'].shift(-1)
                df_ml['Gap'] = df_ml['Next_Idx'] - df_ml['Idx'] - 1
                
                # Identificar inicio de deserción (estudiantes que no se matricularon al mes siguiente)
                dropouts = df_ml[df_ml['Gap'] > 0].copy()
                dropouts['Returned_Next_Month'] = (dropouts['Gap'] == 1).astype(int)
                
                if len(dropouts) > 10:
                    try:
                        from sklearn.ensemble import RandomForestClassifier
                        
                        features = ['Desaprobado', 'Modalidad_Agrupada', 'Meses_Estudiando', 'Tasa_Continuidad', 'Total_Desaprobados_Historico', 'Tasa_Reprobacion_Historica']
                        if 'Nivel' in dropouts.columns: features.append('Nivel')
                        if 'Ciclo_Estudiante' in dropouts.columns: features.append('Ciclo_Estudiante')
                        if 'Nota_Historica_Acumulada' in dropouts.columns: features.append('Nota_Historica_Acumulada')
                        if 'Cursos_Cursados_Historico' in dropouts.columns: 
                            features.append('Cursos_Cursados_Historico')
                            features.append('%_Aprobacion_Historico')
                        
                        X = dropouts[features].fillna(0)
                        X = pd.get_dummies(X, drop_first=True)
                        y = dropouts['Returned_Next_Month']
                        
                        # Entrenar modelo
                        clf = RandomForestClassifier(max_depth=5, n_estimators=50, random_state=42)
                        clf.fit(X, y)
                        
                        col_m1, col_m2 = st.columns([1, 2])
                        with col_m1:
                            tasa_rec = y.mean() * 100
                            st.metric("Tasa Histórica de Recuperación", f"{tasa_rec:.1f}%", help="Porcentaje de alumnos que vuelven tras 1 mes de ausencia en este programa.")
                            
                            st.markdown("#### Importancia de Variables")
                            importances = pd.DataFrame({'Variable': X.columns, 'Importancia': clf.feature_importances_})
                            importances = importances.sort_values('Importancia', ascending=True)
                            # Limpiar nombres de columnas
                            importances['Variable'] = importances['Variable'].str.replace('Modalidad_Agrupada_', 'Mod: ')
                            fig_imp = px.bar(importances, x='Importancia', y='Variable', orientation='h', color='Importancia', color_continuous_scale='Blues')
                            fig_imp.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=300, showlegend=False)
                            st.plotly_chart(fig_imp, use_container_width=True)

                            # NUEVO: Desglose por Etapa Académica
                            st.markdown("#### Tasa de Recuperación por Etapa")
                            def segment_seniority(m):
                                if m <= 3: return "1. Inicios (1-3m)"
                                if m <= 12: return "2. Consolidación (4-12m)"
                                return "3. Avanzados (>12m)"
                            
                            dropouts['Etapa_Academica'] = dropouts['Meses_Estudiando'].apply(segment_seniority)
                            recovery_by_stage = dropouts.groupby('Etapa_Academica')['Returned_Next_Month'].mean().reset_index()
                            recovery_by_stage['Returned_Next_Month'] *= 100
                            
                            fig_stage = px.bar(recovery_by_stage, x='Etapa_Academica', y='Returned_Next_Month', 
                                               color='Etapa_Academica', title="Recuperación según Antigüedad",
                                               labels={'Returned_Next_Month': '% Recuperación'})
                            fig_stage.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=300, showlegend=False)
                            st.plotly_chart(fig_stage, use_container_width=True)

                            # NUEVO: Desglose por Ciclo Académico
                            if 'Ciclo_Estudiante' in dropouts.columns:
                                st.markdown("#### Tasa de Recuperación por Ciclo")
                                recovery_by_cycle = dropouts.groupby('Ciclo_Estudiante')['Returned_Next_Month'].mean().reset_index()
                                recovery_by_cycle['Returned_Next_Month'] *= 100
                                recovery_by_cycle = recovery_by_cycle.sort_values('Ciclo_Estudiante')
                                
                                fig_cycle = px.bar(recovery_by_cycle, x='Ciclo_Estudiante', y='Returned_Next_Month',
                                                  title="Recuperación según Ciclo del Estudiante",
                                                  labels={'Returned_Next_Month': '% Recuperación', 'Ciclo_Estudiante': 'Ciclo'},
                                                  color='Returned_Next_Month', color_continuous_scale='Greens')
                                fig_cycle.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=300)
                                st.plotly_chart(fig_cycle, use_container_width=True)
                            
                        with col_m2:
                            # Time-Series Evolution of Recovery
                            st.markdown("#### Evolución de Recuperación (Mes a Mes)")
                            st.caption("¿Están funcionando las estrategias recientes de retención? (Últimos 12 meses)")
                            trend = dropouts.groupby('Periodo_Real')['Returned_Next_Month'].mean().reset_index()
                            trend['Returned_Next_Month'] *= 100
                            trend = trend.tail(12)
                            
                            fig_trend = px.line(trend, x='Periodo_Real', y='Returned_Next_Month', markers=True)
                            fig_trend.update_traces(line_color='#2ca02c', line_width=3, marker=dict(size=8))
                            fig_trend.update_layout(yaxis_title="% Recuperación al mes sgte.", xaxis_title="Mes de inicio de ausencia", plot_bgcolor="rgba(0,0,0,0)", height=300)
                            st.plotly_chart(fig_trend, use_container_width=True)
                            
                        # Predicción para los desertores actuales
                        st.markdown("---")
                        st.markdown("#### 🎯 Predictor de Retorno: Alumnos en Riesgo Actual (1 mes de ausencia)")
                        
                        ultimo_idx = max(p_to_idx.values())
                        actuales = df_ml.groupby('DNI').last().reset_index()
                        
                        # Alumnos cuyo último registro fue hace 1 mes (están ausentes este mes actual)
                        en_riesgo = actuales[actuales['Idx'] == ultimo_idx - 1].copy()
                        
                        if not en_riesgo.empty:
                            X_actual = en_riesgo[features].fillna(0)
                            X_actual = pd.get_dummies(X_actual)
                            # Alinear columnas con el modelo entrenado
                            X_actual = X_actual.reindex(columns=X.columns, fill_value=0)
                            
                            probs = clf.predict_proba(X_actual)[:, 1]
                            en_riesgo['Probabilidad de Retorno'] = probs * 100
                            
                            res = en_riesgo[['DNI', 'Periodo_Real', 'Desaprobado'] + [c for c in features if c not in ['Desaprobado', 'Nivel']] + ['Probabilidad de Retorno']]
                            res = res.sort_values('Probabilidad de Retorno', ascending=False)
                            
                            # Renombrar columnas para mayor claridad
                            res = res.rename(columns={
                                'Desaprobado': 'Cursos Desaprobados (Mes Previo)',
                                'Periodo_Real': 'Último Mes Activo',
                                'Modalidad_Agrupada': 'Modalidad',
                                'Meses_Estudiando': 'Meses Totales Estudiando',
                                'Tasa_Continuidad': '% Continuidad (Histórico)',
                                'Total_Desaprobados_Historico': 'Total Cursos Jalados (Histórico)',
                                'Tasa_Reprobacion_Historica': 'Promedio Jalados por Mes',
                                'Ciclo_Estudiante': 'Ciclo Actual',
                                'Nota_Historica_Acumulada': 'Promedio Notas Histórico',
                                'Cursos_Cursados_Historico': 'Total Asignaturas Cursadas',
                                '%_Aprobacion_Historico': '% Éxito Académico'
                            })
                            
                            # Colorear columna de probabilidad
                            def color_prob(val):
                                color = '#d62728' if val < 30 else '#ff7f0e' if val < 60 else '#2ca02c'
                                return f'color: {color}; font-weight: bold'
                                
                            format_dict = {
                                'Probabilidad de Retorno': '{:.1f}%', 
                                'Cursos Desaprobados (Mes Previo)': '{:.0f}',
                                'Meses Totales Estudiando': '{:.0f}',
                                '% Continuidad (Histórico)': '{:.1f}%',
                                'Total Cursos Jalados (Histórico)': '{:.0f}',
                                'Promedio Jalados por Mes': '{:.2f}'
                            }
                            if 'Ciclo Actual' in res.columns: format_dict['Ciclo Actual'] = '{:.0f}'
                            if 'Promedio Notas Histórico' in res.columns: format_dict['Promedio Notas Histórico'] = '{:.1f}'
                            if 'Total Asignaturas Cursadas' in res.columns: format_dict['Total Asignaturas Cursadas'] = '{:.0f}'
                            if '% Éxito Académico' in res.columns: format_dict['% Éxito Académico'] = '{:.1f}%'
                            
                            st.dataframe(res.style.map(color_prob, subset=['Probabilidad de Retorno']).format(format_dict), use_container_width=True)
                        else:
                            st.success("¡Excelente! No hay alumnos de este programa con 1 mes exacto de ausencia en el último periodo analizado.")
                            
                    except ImportError:
                        st.error("La librería scikit-learn no está instalada. Ejecute: `pip install scikit-learn`")
                else:
                    st.info("No hay suficientes datos históricos de deserción para entrenar un modelo predictivo en este programa.")
            
            # --- NUEVA SECCIÓN: RESUMEN GENERAL PROGRAMAS ---
            st.markdown("---")
            st.markdown("#### 📊 Panorama General: Calificaciones vs Deserción por Programa")
            st.caption("Ubicación estratégica de cada programa según su desempeño académico y tasa de pérdida de alumnos.")
            
            # Preparar datos agregados para el scatter plot
            df_summary = df_long.groupby('Programa_Base').agg({
                'Nota_Num': 'mean',
                'Desercion': 'mean',
                'DNI': 'nunique'
            }).reset_index()
            df_summary['Desercion'] *= 100
            
            fig_sum = px.scatter(
                df_summary, x='Nota_Num', y='Desercion',
                size='DNI', color='Desercion',
                text='Programa_Base', hover_name='Programa_Base',
                labels={'Nota_Num': 'Promedio de Notas', 'Desercion': '% Tasa de Deserción'},
                color_continuous_scale='RdYlGn_r'
            )
            fig_sum.update_traces(textposition='top center')
            fig_sum.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=500)
            st.plotly_chart(fig_sum, use_container_width=True)
            
        else:
            st.warning("Se requiere el Dataset Longitudinal para ejecutar Machine Learning.")

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

@st.cache_data
def load_cursos_data():
    file_path = "Asignaturas_Desaprobados_Historico.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['Año'] = df['Año'].astype(str)
        return df
    return pd.DataFrame()

file_path = "Cuadro_Mando_Pregrado_Calculado.csv"
mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
df = load_data(mtime)
df_cursos = load_cursos_data()

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
    perm_continuo = perm_incontinuo = reincorporado_curr = 0
    retenidos_1m = 0
    antiguos_total = 0
    
    if anchor_idx:
        idx = anchor_idx[0]
        df_current = df_timeline_full.iloc[[idx]]
        df_3m = df_timeline_full.iloc[max(0, idx - 2):idx+1]
        df_6m = df_timeline_full.iloc[max(0, idx - 5):idx+1]
        df_12m = df_timeline_full.iloc[max(0, idx - 11):idx+1]
        df_hist = df_timeline_full.iloc[:idx+1]
        
        # Métrica: Admitidos (Sumas rodantes)
        admitidos_mat_curr = df_current['Admitidos Matriculados'].sum()
        admitidos_mat_3m = df_3m['Admitidos Matriculados'].sum()
        admitidos_mat_6m = df_6m['Admitidos Matriculados'].sum()
        admitidos_mat_12m = df_12m['Admitidos Matriculados'].sum()
        admitidos_mat_hist = df_hist['Admitidos Matriculados'].sum()
        
        # Desglose Admitidos (Mes actual)
        traslados_curr = df_current.get('Nuevos Traslados', pd.Series([0])).sum()
        convalidados_curr = df_current.get('Nuevos Convalidados', pd.Series([0])).sum()
        regulares_curr = admitidos_mat_curr - traslados_curr - convalidados_curr
        
        # Métrica: Permanencia (nuevas categorías)
        perm_continuo = df_current.get('Permanentes Continuos', pd.Series([0])).sum()
        perm_incontinuo = df_current.get('Permanentes Incontinuos', pd.Series([0])).sum()
        reincorporado_curr = df_current.get('Reincorporados', pd.Series([0])).sum()
        
        # Métrica: Crecimiento Neto
        def calc_crecimiento(d):
            ent = d['Admitidos Matriculados'].sum() + d.get('Perm. 1mes', pd.Series([0])).sum() + d.get('Permanentes Incontinuos', pd.Series([0])).sum() + d.get('Reincorporados', pd.Series([0])).sum()
            sal = d.get('Riesgo Deserción (1m)', pd.Series([0])).sum() + d['Egresados'].sum()
            return ent - sal
            
        crecimiento_curr = calc_crecimiento(df_current)
        crecimiento_3m = calc_crecimiento(df_3m)
        crecimiento_6m = calc_crecimiento(df_6m)
        crecimiento_12m = calc_crecimiento(df_12m)
        crecimiento_hist = calc_crecimiento(df_hist)

        # Variables actuales
        total_matriculados = df_current['Estudiantes matrí. TOTAL'].sum()
        riesgo_1 = df_current.get('Riesgo Deserción (1m)', pd.Series([0])).sum()
        riesgo_2 = df_current.get('Riesgo Deserción (2m)', pd.Series([0])).sum()
        temprana = df_current.get('Deserción Temprana (3-6m)', pd.Series([0])).sum()
        tardia = df_current.get('Deserción Tardía (7-12m)', pd.Series([0])).sum()
        muy_tardia = df_current.get('Deserción Muy Tardía (>12m)', pd.Series([0])).sum()
        retenidos_1m = perm_continuo
        antiguos_total = total_matriculados - admitidos_mat_curr
    
    desercion_total = riesgo_1 + riesgo_2 + temprana + tardia + muy_tardia
    
    st.subheader(f"Métricas Estratégicas: {mes_seleccionado} {año_anchor}")
    
    # ---------------------------------------------
    # NUEVO DISEÑO EN PESTAÑAS (TABS)
    # ---------------------------------------------
    st.metric("👥 Total Matriculados (Mes Activo)", int(total_matriculados))
    
    tab_crec, tab_adm, tab_perm = st.tabs(["📈 Crecimiento Neto", "🎯 Admitidos Matriculados", "🛡️ Permanentes"])
    
    with tab_crec:
        st.info("💡 **Fórmula:** Ingresos (Nuevos + Recuperados) - Fugas del Mes (Riesgo 1m + Egresados). Mide si la universidad sumó o perdió alumnos reales.")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Este Mes", int(crecimiento_curr))
        c2.metric("Últimos 3 Meses", int(crecimiento_3m))
        c3.metric("Últimos 6 Meses", int(crecimiento_6m))
        c4.metric("Último Año (12m)", int(crecimiento_12m))
        c5.metric("Crecimiento Neto", int(crecimiento_hist))

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
        # Recuperados = quienes regresan (1 mes + 2-5m + 6m+)
        recuperados_flow = (
            df_flow.get('Perm. 1mes', 0) +
            df_flow.get('Permanentes Incontinuos', 0) +
            df_flow.get('Reincorporados', 0)
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
            + df_flow.get('Reincorporados', 0)
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
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Este Mes", int(admitidos_mat_curr))
        c2.metric("Últimos 3 Meses", int(admitidos_mat_3m))
        c3.metric("Últimos 6 Meses", int(admitidos_mat_6m))
        c4.metric("Último Año (12m)", int(admitidos_mat_12m))
        c5.metric("Desde el inicio", int(admitidos_mat_hist))
        
        st.markdown("**Desglose de Admitidos (Este Mes):**")
        d1, d2, d3 = st.columns(3)
        d1.metric("Regulares", int(regulares_curr))
        d2.metric("Por Traslado", int(traslados_curr))
        d3.metric("Por Convalidación", int(convalidados_curr))

    with tab_perm:
        st.info("""💡 **Nueva Clasificación de Permanencia por Comportamiento de Matrícula:**
        - **Permanente Continuo:** Alumno siempre matriculado (máximo 1 mes de gap)
        - **Permanente Incontinuo:** Regresa tras 2-5 meses de ausencia
        - **Reincorporado:** Regresa tras 6+ meses de ausencia
        """)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 Perm. Continuos", int(perm_continuo))
        c2.metric("🟡 Perm. Incontinuos", int(perm_incontinuo))
        c3.metric("🟤 Reincorporados", int(reincorporado_curr))
        c4.metric("👥 Total Antiguos", int(antiguos_total))
        
    st.markdown("### 📊 Evolución y Balance de la Matrícula")
    st.info("Este gráfico presenta el balance mensual de la universidad: sobre el eje cero se muestra la **Matrícula Activa** (Nuevos, Recuperados y Retenidos); bajo el eje cero se muestra la **Pérdida de Masa** (Desertores y Egresados).")
    
    # Preparar datos para el balance completo
    df_balance = df_timeline_full.copy()
    
    # Componentes Positivos (Parte superior)
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Permanentes Continuos', df_balance.get('Retenidos (1m)', 0)),
        name='🟢 Permanentes Continuos (0-1m)', marker_color='#00CC96',
        hovertemplate='%{y} perm. continuos'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Permanentes Incontinuos', 0),
        name='🟡 Permanentes Incontinuos (2-5m)', marker_color='#FFA15A',
        hovertemplate='%{y} perm. incontinuos'
    ))
    fig_bal.add_trace(go.Bar(
        x=df_balance['Periodo_Real'],
        y=df_balance.get('Reincorporados', 0),
        name='🟤 Reincorporados (6m+)', marker_color='#FFEC45',
        hovertemplate='%{y} reincorporados'
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
    
    tab1, tab2 = st.tabs(["📚 Asignaturas Críticas (Desaprobados)", "🏛️ Programas con Mayor Riesgo"])
    
    with tab1:
        st.markdown("Top 10 Asignaturas con mayor volumen de desaprobados en el mes seleccionado.")
        if not df_cursos.empty:
            df_c_mes = df_cursos[(df_cursos['Año'].isin(años_seleccionados)) & (df_cursos['Mes_Nombre'] == mes_seleccionado)]
            if programa_seleccionado != "Todos (Institucional)":
                df_c_mes = df_c_mes[df_c_mes['Programa_Base'] == programa_seleccionado]
            
            if not df_c_mes.empty:
                top_cursos = df_c_mes.groupby('Asignatura').agg({'Desaprobado': 'sum', 'Total_Alumnos': 'sum'}).reset_index()
                top_cursos['Tasa_Reprobación'] = (top_cursos['Desaprobado'] / top_cursos['Total_Alumnos']) * 100
                top_cursos = top_cursos.sort_values(by='Desaprobado', ascending=False).head(10)
                
                fig_cursos = px.bar(top_cursos, x='Desaprobado', y='Asignatura', orientation='h',
                                    hover_data=['Total_Alumnos', 'Tasa_Reprobación'],
                                    title="Top 10 Asignaturas Críticas",
                                    color='Tasa_Reprobación', color_continuous_scale='Reds')
                fig_cursos.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)", height=400)
                st.plotly_chart(fig_cursos, use_container_width=True)
            else:
                st.info("No hay datos de asignaturas para los filtros seleccionados.")
                
    with tab2:
        st.markdown("Programas con mayor cantidad de desertores en el mes seleccionado.")
        df_p_mes = df_f[df_f['Mes'] == mes_seleccionado].copy()
        cols_sum = ['Riesgo Deserción (1m)', 'Riesgo Deserción (2m)', 'Deserción Temprana (3-6m)', 'Deserción Tardía (7-12m)', 'Deserción Muy Tardía (>12m)']
        df_p_mes['Deserción_Total'] = df_p_mes[cols_sum].sum(axis=1)
        
        top_prog = df_p_mes.sort_values(by='Deserción_Total', ascending=False).head(10)
        
        fig_prog = px.bar(top_prog, x='Deserción_Total', y='Programa', orientation='h',
                          title="Top Programas con Mayor Deserción Absoluta",
                          color='Deserción_Total', color_continuous_scale='Oranges')
        fig_prog.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)", height=400)
        st.plotly_chart(fig_prog, use_container_width=True)

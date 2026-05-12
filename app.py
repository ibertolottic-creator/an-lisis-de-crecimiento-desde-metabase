import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Dashboard Académico Avanzado", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Sistema de Análisis Estratégico y Deserción - USMP")
st.markdown("Dashboard interactivo para visualizar métricas clave y factores de riesgo para Machine Learning.")

@st.cache_data
def load_data():
    # Cache buster para forzar la recarga del CSV (v2)
    file_path = "Cuadro_Mando_Pregrado_Calculado.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['Año'] = df['Año'].astype(str)
        if 'Periodo_Real' not in df.columns:
            df['Periodo_Real'] = df['Año'] + "-" + df['Mes']
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

df = load_data()
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
    
    meses_disponibles = df_filtrado_año['Mes'].unique().tolist()
    mes_seleccionado = st.sidebar.selectbox("Seleccionar Mes Específico (para KPIs)", meses_disponibles, index=len(meses_disponibles)-1 if meses_disponibles else 0)
    
    programas_disponibles = ["Todos (Institucional)"] + df['Programa'].unique().tolist()
    programa_seleccionado = st.sidebar.selectbox("Seleccionar Programa", programas_disponibles)
    
    # -----------------------------------------------------
    # CÁLCULOS DE LÍNEA DE TIEMPO (Histórico, 6m, Actual)
    # -----------------------------------------------------
    if programa_seleccionado == "Todos (Institucional)":
        df_full_prog = df.copy()
        df_base = df_filtrado_año.copy()
    else:
        df_full_prog = df[df['Programa'] == programa_seleccionado]
        df_base = df_filtrado_año[df_filtrado_año['Programa'] == programa_seleccionado]
        
    df_timeline_full = df_full_prog.groupby(['Periodo_Real', 'Año', 'Mes']).sum(numeric_only=True).reset_index()
    df_timeline_full = df_timeline_full.sort_values('Periodo_Real').reset_index(drop=True)
    
    año_anchor = max(años_seleccionados)
    anchor_idx = df_timeline_full.index[(df_timeline_full['Año'] == año_anchor) & (df_timeline_full['Mes'] == mes_seleccionado)].tolist()
    
    # Inicializar variables
    admitidos_mat_curr = 0
    recuperados_curr = 0
    crecimiento_curr = 0
    traslados_curr = convalidados_curr = regulares_curr = 0
    total_matriculados = 0
    riesgo_1 = riesgo_2 = temprana = tardia = 0
    
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
        
        # Métrica: Recuperados (Sumas rodantes)
        recuperados_curr = df_current['Recuperados'].sum()
        recuperados_3m = df_3m['Recuperados'].sum()
        recuperados_6m = df_6m['Recuperados'].sum()
        recuperados_12m = df_12m['Recuperados'].sum()
        recuperados_hist = df_hist['Recuperados'].sum()
        
        # Métrica: Crecimiento Neto (CORRECCIÓN: Solo se resta la fuga del mes (Riesgo 1m) + Egresados)
        def calc_crecimiento(d):
            ent = d['Admitidos Matriculados'].sum() + d['Recuperados'].sum()
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
        tardia = df_current.get('Deserción Tardía (>6m)', pd.Series([0])).sum()
        
        # -------------------------------------------------------------
        # LECTURA: RETENIDOS CONTINUOS PRECALCULADOS
        # -------------------------------------------------------------
        retenidos_1m = df_current.get('Retenidos (1m)', pd.Series([0])).sum()
        retenidos_3m = df_current.get('Retenidos (3m)', pd.Series([0])).sum()
        retenidos_6m = df_current.get('Retenidos (6m)', pd.Series([0])).sum()
        retenidos_12m = df_current.get('Retenidos (12m)', pd.Series([0])).sum()
        
        antiguos_total = total_matriculados - admitidos_mat_curr
    
    desercion_total = riesgo_1 + riesgo_2 + temprana + tardia
    
    st.subheader(f"Métricas Estratégicas: {mes_seleccionado} {año_anchor}")
    
    # ---------------------------------------------
    # NUEVO DISEÑO EN PESTAÑAS (TABS)
    # ---------------------------------------------
    st.metric("👥 Total Matriculados (Mes Activo)", int(total_matriculados))
    
    tab_crec, tab_adm, tab_rec = st.tabs(["📈 Crecimiento Neto", "🎯 Admitidos Matriculados", "🛡️ Retenidos (Continuos)"])
    
    with tab_crec:
        st.info("💡 **Fórmula:** Ingresos (Nuevos + Recuperados) - Fugas del Mes (Riesgo 1m + Egresados). Mide si la universidad sumó o perdió alumnos reales.")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Este Mes", int(crecimiento_curr))
        c2.metric("Últimos 3 Meses", int(crecimiento_3m))
        c3.metric("Últimos 6 Meses", int(crecimiento_6m))
        c4.metric("Último Año (12m)", int(crecimiento_12m))
        c5.metric("Desde el inicio", int(crecimiento_hist))

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

    with tab_rec:
        st.info("💡 **Fórmula:** Alumnos antiguos que mantienen matrícula continua ininterrumpida durante los últimos X meses.")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("1 Mes (vs anterior)", int(retenidos_1m))
        c2.metric("Últimos 3 Meses", int(retenidos_3m))
        c3.metric("Últimos 6 Meses", int(retenidos_6m))
        c4.metric("Último Año (12m)", int(retenidos_12m))
        c5.metric("Total Antiguos", int(antiguos_total))
        
    st.markdown("---")
    st.markdown("### 📊 Evolución y Composición de la Matrícula")
    st.info("Esta gráfica de área apilada (líneas llenas) demuestra visualmente cómo se compone el **Total de Matriculados** cada mes. La suma exacta de las tres franjas da como resultado el 100% de los alumnos activos de ese mes.")
    
    # Preparar datos para el gráfico de composición
    df_composicion = df_timeline_full[['Periodo_Real', 'Admitidos Matriculados', 'Recuperados', 'Retenidos (1m)']].copy()
    
    # Renombrar para mayor claridad en la leyenda
    df_composicion = df_composicion.rename(columns={
        'Retenidos (1m)': '1. Retenidos (Continuos del mes anterior)',
        'Recuperados': '2. Recuperados (Regresaron este mes)',
        'Admitidos Matriculados': '3. Nuevos (Primera matrícula)'
    })
    
    # Derretir (melt) el dataframe para Plotly
    df_melt = df_composicion.melt(id_vars=['Periodo_Real'], 
                                  value_vars=['1. Retenidos (Continuos del mes anterior)', '2. Recuperados (Regresaron este mes)', '3. Nuevos (Primera matrícula)'],
                                  var_name='Tipo de Alumno', value_name='Cantidad')
                                  
    fig_comp = px.area(df_melt, x='Periodo_Real', y='Cantidad', color='Tipo de Alumno',
                       color_discrete_map={
                           '1. Retenidos (Continuos del mes anterior)': '#00CC96', # Verde
                           '3. Nuevos (Primera matrícula)': '#636EFA',             # Azul
                           '2. Recuperados (Regresaron este mes)': '#FFA15A'       # Naranja
                       })
                       
    fig_comp.update_layout(
        xaxis_title="Meses (Periodo)",
        yaxis_title="Cantidad de Alumnos",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_comp, use_container_width=True)
    
    st.markdown("### ⚠️ Análisis de Deserción Escalonada (Mes Seleccionado)")
    col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns(5)
    col_d1.metric("🚨 Deserción Total", int(desercion_total))
    col_d2.metric("🟡 Riesgo (1 mes)", int(riesgo_1), delta_color="off")
    col_d3.metric("🟠 Riesgo (2 meses)", int(riesgo_2), delta_color="off")
    col_d4.metric("🔴 Temprana (3-6 m)", int(temprana), delta_color="off")
    col_d5.metric("⚫ Tardía (>6 m)", int(tardia), delta_color="off")
    
    st.markdown("---")
    st.subheader("Visualizaciones Temporales")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histograma de Deserciones en el tiempo
        df_trend = df_base.groupby('Periodo_Real')[['Riesgo Deserción (1m)', 'Riesgo Deserción (2m)', 'Deserción Temprana (3-6m)', 'Deserción Tardía (>6m)']].sum().reset_index()
            
        fig_des = px.bar(df_trend, x='Periodo_Real', y=['Riesgo Deserción (1m)', 'Riesgo Deserción (2m)', 'Deserción Temprana (3-6m)', 'Deserción Tardía (>6m)'],
                         title="Evolución de Deserción Escalonada",
                         labels={'value': 'Cantidad de Alumnos', 'variable': 'Tipo de Deserción'},
                         color_discrete_map={
                             'Riesgo Deserción (1m)': '#ffdf7e', 
                             'Riesgo Deserción (2m)': '#ffc107', 
                             'Deserción Temprana (3-6m)': '#fd7e14', 
                             'Deserción Tardía (>6m)': '#dc3545'
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
        df_p_mes = df_filtrado_año[df_filtrado_año['Mes'] == mes_seleccionado].copy()
        df_p_mes['Deserción_Total'] = df_p_mes['Riesgo Deserción (1m)'] + df_p_mes['Riesgo Deserción (2m)'] + df_p_mes['Deserción Temprana (3-6m)'] + df_p_mes['Deserción Tardía (>6m)']
        
        top_prog = df_p_mes.sort_values(by='Deserción_Total', ascending=False).head(10)
        
        fig_prog = px.bar(top_prog, x='Deserción_Total', y='Programa', orientation='h',
                          title="Top Programas con Mayor Deserción Absoluta",
                          color='Deserción_Total', color_continuous_scale='Oranges')
        fig_prog.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)", height=400)
        st.plotly_chart(fig_prog, use_container_width=True)

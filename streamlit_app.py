import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import plotly.express as px # Para gráficos más profesionales

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ---
conn = st.connection("supabase", type=SupabaseConnection)

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. VER DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR HISTORIAL"): ir_a('Carga')

# ==========================================
#        PANTALLA: 1. DASHBOARD (EL PLATO FUERTE)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📊 Análisis de Ventas Histórico")

    # 1. Carga de datos desde historial_ventas
    try:
        with st.spinner("Cargando 280,000 registros..."):
            res = conn.table("historial_ventas").select("fecha, cantidad_vendida, total_neto, productos(nombre, categoria)").execute()
            df = pd.DataFrame(res.data)
            
            # Limpieza y preparación
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['Año'] = df['fecha'].dt.year
            df['Mes'] = df['fecha'].dt.month
            df['Mes_Nombre'] = df['fecha'].dt.strftime('%b')
            df['Nombre'] = df['productos'].apply(lambda x: x['nombre'])
            df['Categoria'] = df['productos'].apply(lambda x: x['categoria'])

        # --- FILTROS ---
        st.sidebar.header("Filtros")
        años_selec = st.sidebar.multiselect("Seleccionar Años", options=sorted(df['Año'].unique()), default=df['Año'].unique())
        df_filtrado = df[df['Año'].isin(años_selec)]

        # --- MÉTRICAS TOP ---
        c1, c2, c3 = st.columns(3)
        total_v = df_filtrado['total_neto'].sum()
        total_u = df_filtrado['cantidad_vendida'].sum()
        c1.metric("Facturación Total", f"{total_v:,.2f} €")
        c2.metric("Unidades Vendidas", f"{total_u:,} uds")
        c3.metric("Ticket Medio Est.", f"{(total_v/len(df_filtrado)):,.2f} €")

        st.divider()

        # --- GRÁFICO 1: COMPARATIVA MENSUAL POR AÑO ---
        st.subheader("📈 Evolución de Facturación por Mes")
        df_mes = df_filtrado.groupby(['Año', 'Mes', 'Mes_Nombre'])['total_neto'].sum().reset_index()
        fig_evol = px.line(df_mes, x='Mes_Nombre', y='total_neto', color=df_mes['Año'].astype(str),
                          labels={'total_neto': 'Ventas (€)', 'Mes_Nombre': 'Mes'},
                          markers=True, category_orders={"Mes_Nombre": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]})
        st.plotly_chart(fig_evol, use_container_width=True)

        # --- GRÁFICO 2: TOP SABORES ---
        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("🏆 Top 10 Empanadas")
            df_empa = df_filtrado[df_filtrado['Categoria'] == 'Empanada']
            top_sabores = df_empa.groupby('Nombre')['cantidad_vendida'].sum().sort_values(ascending=False).head(10).reset_index()
            fig_top = px.bar(top_sabores, x='cantidad_vendida', y='Nombre', orientation='h', color='cantidad_vendida',
                            color_continuous_scale='Oranges')
            st.plotly_chart(fig_top, use_container_width=True)

        with col_right:
            st.subheader("🍕 Ventas por Categoría")
            df_cat = df_filtrado.groupby('Categoria')['total_neto'].sum().reset_index()
            fig_pie = px.pie(df_cat, values='total_neto', names='Categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as e:
        st.error(f"Error al generar el Dashboard: {e}")
        st.info("Asegúrate de que la tabla 'historial_ventas' tiene datos.")

# ==========================================
#        PANTALLA: 4. CARGA (POR SI SUBES MÁS)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.success("✅ ¡Ya tienes 282,245 filas cargadas! Puedes subir más archivos si lo necesitas.")
    # (Aquí sigue el código de carga que ya tenías...)

# [Se mantienen las pantallas de Productos y Operativa del código anterior]

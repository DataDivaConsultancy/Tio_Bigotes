import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets.")
    st.stop()

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p):
    st.session_state.pantalla = p

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
#        PANTALLA: 1. DASHBOARD
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📊 Análisis de Ventas")

    try:
        # Traer datos con relación a productos para tener los nombres
        res = conn.table("historial_ventas").select("fecha, cantidad_vendida, total_neto, productos(nombre, categoria)").execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['Año'] = df['fecha'].dt.year
            df['Mes_Num'] = df['fecha'].dt.month
            df['Mes'] = df['fecha'].dt.strftime('%b')
            df['Nombre'] = df['productos'].apply(lambda x: x['nombre'] if x else "Desconocido")
            df['Categoria'] = df['productos'].apply(lambda x: x['categoria'] if x else "Otros")

            # Metricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Neto", f"{df['total_neto'].sum():,.2f} €")
            c2.metric("Unidades", f"{df['cantidad_vendida'].sum():,}")
            c3.metric("Registros", f"{len(df):,}")

            # Gráfico de evolución
            df_evo = df.groupby(['Año', 'Mes_Num', 'Mes'])['total_neto'].sum().reset_index().sort_values('Mes_Num')
            fig = px.line(df_evo, x='Mes', y='total_neto', color=df_evo['Año'].astype(str), markers=True, title="Ventas por Mes y Año")
            st.plotly_chart(fig, use_container_width=True)
            
            # Top Sabores
            st.subheader("🏆 Top 10 Sabores (Unidades)")
            top = df.groupby('Nombre')['cantidad_vendida'].sum().sort_values(ascending=False).head(10).reset_index()
            fig_bar = px.bar(top, x='cantidad_vendida', y='Nombre', orientation='h', color='cantidad_vendida')
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("No hay datos en el historial.")
    except Exception as e:
        st.error(f"Error cargando Dashboard: {e}")

# ==========================================
#        PANTALLA: 4. CARGA (Simplificada)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Estado de la Base de Datos")
    st.info("Ya has cargado los datos históricos. Si necesitas subir más, usa el importador.")
    # (Aquí puedes dejar el código de carga anterior si quieres subir más archivos)

# Las pantallas de Productos y Operativa se pueden rellenar igual
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write("Gestionar productos...")

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write("Control diario...")

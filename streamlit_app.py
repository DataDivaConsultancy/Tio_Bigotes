import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import plotly.express as px
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN DIRECTA ---
# Usamos st.secrets directamente para que no haya pérdida de datos
try:
    if "connections" not in st.secrets:
        st.error("Faltan los Secrets en la configuración de Streamlit.")
        st.stop()
        
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error de conexión: {e}")
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
    st.title("🥐 Tío Bigotes - Panel Principal")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 VER DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 PRODUCTOS"): ir_a('Productos')
        if st.button("📥 CARGAR DATOS"): ir_a('Carga')

# ==========================================
#        PANTALLA: DASHBOARD (SEGURO)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Análisis de Ventas")
    
    try:
        # Limitamos la consulta inicial para evitar que se cuelgue
        res = conn.table("historial_ventas").select("fecha, total_neto").limit(10000).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            st.success(f"Analizando los últimos {len(df)} registros...")
            
            df['fecha'] = pd.to_datetime(df['fecha'])
            df_evo = df.groupby('fecha')['total_neto'].sum().reset_index()
            
            fig = px.line(df_evo, x='fecha', y='total_neto', title="Tendencia de Ventas")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos todavía. Ve a 'Cargar Datos'.")
    except Exception as e:
        st.error(f"Error al leer datos: {e}")

# [El resto de pantallas se mantienen simples para probar conexión]
else:
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write(f"Estás en la pantalla: {st.session_state.pantalla}")

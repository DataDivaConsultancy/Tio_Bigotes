import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import plotly.express as px
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ---
@st.cache_resource # Esto evita que la conexión se cree mil veces
def get_connection():
    return st.connection("supabase", type=SupabaseConnection)

try:
    conn = get_connection()
except:
    st.error("Error de conexión.")
    st.stop()

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Panel")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 VER DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 PRODUCTOS"): ir_a('Productos')
        if st.button("📥 CARGAR MÁS"): ir_a('Carga')

# ==========================================
#        PANTALLA: DASHBOARD (OPTIMIZADA)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📊 Análisis de Ventas")
    
    # Usamos st.cache_data para que no descargue 280k filas cada vez que tocas un botón
    @st.cache_data(ttl=600) # Guarda los datos 10 minutos
    def cargar_datos():
        # Pedimos solo lo necesario para que no se quede la pantalla en negro
        res = conn.table("historial_ventas").select("fecha, cantidad_vendida, total_neto, producto_id").limit(50000).execute()
        return pd.DataFrame(res.data)

    try:
        with st.spinner("Analizando datos..."):
            df = cargar_datos()
            if not df.empty:
                df['fecha'] = pd.to_datetime(df['fecha'])
                st.metric("Datos Analizados", f"{len(df):,} filas")
                
                # Gráfico rápido
                df_evo = df.groupby('fecha')['total_neto'].sum().reset_index()
                fig = px.area(df_evo, x='fecha', y='total_neto', title="Ventas en el tiempo (Muestra)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No hay datos cargados aún.")
    except Exception as e:
        st.error(f"Error de memoria: {e}. Prueba a reducir el archivo CSV.")

# [Mantén las otras pantallas vacías o con texto simple por ahora]

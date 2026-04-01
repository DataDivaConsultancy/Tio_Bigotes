import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Panel Tío Bigotes", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetConnection)

# --- ESTILOS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 80px; width: 100%; font-size: 18px; font-weight: bold;
        border-radius: 12px; background-color: #ff9800; color: white;
    }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(nueva_pantalla):
    st.session_state.pantalla = nueva_pantalla

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1])
    with col_logo_2:
        try: st.image('image.png', use_column_width=True)
        except: st.info("Cargando Panel Tío Bigotes...")
    
    st.subheader(f"Gestión de Tienda | {datetime.date.today().strftime('%d/%m/%Y')}")
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 1. DASHBOARD (HISTORIAL)"): ir_a('Dashboard')
        if st.button("👨‍🍳 2. CONTROL DIARIO & HORNEADO"): ir_a('Operativa')
    with c2:
        if st.button("🛒 3. PREVISIÓN DE COMPRAS"): ir_a('Compras')
        if st.button("📈 4. IA PROMEDIOS & LISTAS"): ir_a('IA')

# ==========================================
#        PANTALLA: 1. DASHBOARD (Historial)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ MENU", on_click=ir_a, args=('Home',))
    st.title("📊 Análisis de Ventas (Historial)")
    
    try:
        df_historial = conn.read(worksheet="Historial")
        # Mostrar métricas rápidas de la última fecha registrada
        st.write("Últimos datos registrados en Historial:")
        st.dataframe(df_historial.tail(10), use_container_width=True)
    except:
        st.error("No se pudo leer la pestaña 'Historial'. Revisa el nombre en tu Excel.")

# ==========================================
#   PANTALLA: 2. CONTROL DIARIO / HORNEADO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ MENU", on_click=ir_a, args=('Home',))
    st.title("🔥 Operativa Diaria")
    
    tab1, tab2 = st.tabs(["Previsión Sugerida", "Registro Control Diario"])
    
    with tab1:
        st.subheader("Sugerencia de Horneado")
        try:
            df_prev = conn.read(worksheet="Prevision Horneado")
            st.write("Basado en el promedio de hoy y eventos especiales:")
            st.table(df_prev.head(10)) 
        except:
            st.info("Pestaña 'Prevision Horneado' no encontrada o vacía.")

    with tab2:
        st.subheader("Anotar Stock / Horneado")
        with st.form("control_diario"):
            producto = st.selectbox("Producto", ["Carne Cuchillo", "Pollo", "J&Q", "Caprese", "Carne Picante", "Carne Suave"])
            tipo = st.radio("¿Qué registras?", ["Horneado", "Merma", "Resto (Cierre)"])
            cantidad = st.number_input("Cantidad", min_value=0, step=1)
            
            if st.form_submit_button("Guardar en Control Diario"):
                # Aquí iría la lógica para enviar a la pestaña "Control Diario"
                st.success(f"Registrado: {cantidad} de {producto} como {tipo}")
                st.balloons()

# ==========================================
#        PANTALLA: 3. PREVISIÓN COMPRAS
# ==========================================
elif st.session_state.pantalla == 'Compras':
    st.button("⬅️ MENU", on_click=ir_a, args=('Home',))
    st.title("🛒 Previsión de Compras")
    try:
        df_compras = conn.read(worksheet="Prevision compras")
        st.dataframe(df_compras, use_container_width=True)
    except:
        st.error("No se pudo cargar la pestaña 'Prevision compras'.")

# ==========================================
#        PANTALLA: 4. IA & LISTAS
# ==========================================
elif st.session_state.pantalla == 'IA':
    st.button("⬅️ MENU", on_click=ir_a, args=('Home',))
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("IA Promedios")
        try:
            df_prom = conn.read(worksheet="IA_Promedios")
            st.dataframe(df_prom)
        except: st.write("Error cargando promedios.")
    with col2:
        st.subheader("Listas")
        try:
            df_listas = conn.read(worksheet="Listas")
            st.dataframe(df_listas)
        except: st.write("Error cargando listas.")

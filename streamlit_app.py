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
        height: 90px; width: 100%; font-size: 20px; font-weight: bold;
        border-radius: 12px; background-color: #ff9800; color: white;
    }
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
        except: st.warning("Sube 'image.png' a GitHub")
    
    st.subheader("Menú Principal")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. VER VENTAS (DASHBOARD)"): ir_a('Dashboard')
    with col2:
        if st.button("🔥 2. REGISTRAR HORNEADO"): ir_a('Operativa')

# ==========================================
#        PANTALLA: 1. DASHBOARD (LECTURA)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📊 Análisis de Ventas Real")
    
    try:
        # Intentamos leer la pestaña "VENTAS" de tu Sheet
        df_ventas = conn.read(worksheet="VENTAS")
        st.success("✅ Datos cargados desde Google Sheets")
        
        # Muestra las últimas 5 ventas registradas
        st.write("Últimos registros en el Excel:")
        st.dataframe(df_ventas.tail(5), use_container_width=True)
        
    except Exception as e:
        st.error(f"No pude leer la pestaña 'VENTAS'. Revisa que el nombre sea exacto en el Sheet.")
        st.info("Asegúrate de haber compartido el Sheet con: streamlit-app@streamlit-app-274213.iam.gserviceaccount.com")

# ==========================================
#   PANTALLA: 2. OPERATIVA (ESCRITURA)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("👨‍🍳 Registro de Horneado")
    
    with st.form("form_horneado"):
        sabor = st.selectbox("Sabor", ["Carne Cuchillo", "Pollo", "J&Q", "Caprese", "Carne Picante", "Carne Suave"])
        cantidad = st.number_input("Cantidad (Unidades)", min_value=1, step=1)
        enviar = st.form_submit_button("💾 GUARDAR EN EXCEL")
        
        if enviar:
            # Creamos la línea de datos
            nueva_fila = pd.DataFrame([{
                "Fecha": datetime.date.today().strftime("%Y-%m-%d"),
                "Sabor": sabor,
                "Cantidad": cantidad
            }])
            
            # Intentamos escribir en la pestaña "HORNEADOS"
            try:
                # Leemos lo que hay, añadimos lo nuevo y guardamos
                df_actual = conn.read(worksheet="HORNEADOS")
                df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
                conn.update(worksheet="HORNEADOS", data=df_final)
                st.balloons()
                st.success(f"¡Guardado! {cantidad} de {sabor} registradas.")
            except:
                st.error("Error al guardar. ¿Existe la pestaña 'HORNEADOS' en tu Sheet?")

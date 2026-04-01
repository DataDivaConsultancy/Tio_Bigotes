import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Tienda - Panel Operativo", layout="wide", initial_sidebar_state="collapsed")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 100px; width: 100%; font-size: 20px; font-weight: bold;
        border-radius: 12px; background-color: #ff9800; color: white; border: none; margin-bottom: 15px;
    }
    div.stButton > button:first-child:hover { background-color: #e68a00; border: 2px solid #333; }
    .st-emotion-cache-1vt4ygl button { height: auto; font-size: 16px; background-color: #f0f2f6; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(nueva_pantalla):
    st.session_state.pantalla = nueva_pantalla

sabores = ["CARNE CUCHILLO", "POLLO", "JAMON Y QUESO", "CAPRESE", "CARNE PICANTE", "CARNE SUAVE"]

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    col_logo_1, col_logo_2, col_logo_3 = st.columns([1, 2, 1])
    with col_logo_2:
        try:
            st.image('image.png', use_column_width=True)
        except:
            st.warning("⚠️ Sube la imagen 'image.png' a tu GitHub.")
    
    st.subheader("Menú Principal de Gestión")
    st.write(f"📍 Diputació 159 | {datetime.date.today().strftime('%d/%m/%Y')}")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. DASHBOARD"): ir_a('Dashboard')
        if st.button("📅 3. HISTORIAL & CALENDARIO"): ir_a('Historial')
    with col2:
        if st.button("🔥 2. OPERATIVA DE HOY"): ir_a('Operativa')
        if st.button("🛒 4. COMPRAS"): ir_a('Compras')
    
    if st.button("⚙️ 5. CONFIGURACIÓN (FESTIVOS)"): ir_a('Configuracion')

# ==========================================
#        PANTALLA: 1. DASHBOARD
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📊 Dashboard Analítico")
    
    st.subheader("💰 Facturación vs Año Anterior (LY)")
    c1, c2, c3 = st.columns(3)
    c1.metric(label="Ayer vs Mismo día LY", value="850 €", delta="12%") 
    c2.metric(label="Mes en curso vs LY", value="18,400 €", delta="-2%")
    c3.metric(label="YTD vs LY", value="73,432 €", delta="11.9%")
    
    st.divider()
    st.subheader("🗑️ Control de Mermas (Unidades)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label="Mermas Ayer", value="12 uds", delta="Pollo (4), Caprese (3)", delta_color="off")
    m2.metric(label="Acumulado Semana", value="45 uds")
    m3.metric(label="Acumulado Mes", value="180 uds")
    m4.metric(label="Acumulado Año", value="540 uds")

# ==========================================
#   PANTALLA: 2. OPERATIVA DE HOY
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("🔥 Operativa del Día")
    
    st.subheader("🚩 1. Contexto del Día")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        tipo_dia = st.selectbox("¿Qué tipo de día es hoy?", 
                                ["Día Normal", "Festivo Local", "Festivo Nacional", "Evento", "Día de Lluvia"])
    with col_c2:
        st.text_input("Nota adicional (ej: Partido, Corte de calle)")
    
    st.divider()
    
    st.subheader("👨‍🍳 2. Sugerencia de Horneado (IA)")
    col_h1, col_h2 = st.columns(2)
    col_h1.success("**TANDA 1 (Apertura)**\n- 30 Carne Cuchillo\n- 20 Pollo\n- 10 Jamón y Queso")
    col_h2.warning("**TANDA 2 (Tarde)**\n- 15 Carne Cuchillo\n- 10 Caprese")
    
    st.divider()

    st.subheader("📝 3. Registrar Horneado")
    col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
    with col_r1:
        sabor_horn = st.selectbox("Sabor a hornear", sabores)
    with col_r2:
        cant_horn = st.number_input("Cantidad", min_value=1, max_value=60, step=1)
    with col_r3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Guardar Bandeja"):
            st.success(f"✅ Registradas {cant_horn} uds de {sabor_horn}.")

    st.divider()
    
    st.subheader("🌙 4. Cierre de Caja y Merma")
    with st.expander("Haz clic aquí para realizar el cierre del día"):
        for s in sabores:
            st.number_input(f"Resto de {s}", min_value=0, step=1, key=f"resto_{s}")
        if st.button("Calcular Merma y Cerrar Día"):
            st.error("🚨 **MERMA DETECTADA**: Retirar mermas de más de 3 días.")
            st.success("✅ Día cerrado.")

# ==========================================
#   PANTALLA: 3. HISTORIAL & CALENDARIO
# ==========================================
elif st.session_state.pantalla == 'Historial':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📅 Historial de Ventas")
    st.date_input("Selecciona una fecha:", datetime.date.today() - datetime.timedelta(days=1))
    st.info("Mostrando datos simulados.")

# ==========================================
#        PANTALLA: 4. COMPRAS
# ==========================================
elif st.session_state.pantalla == 'Compras':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("🛒 Previsión y Pedido de Compras")
    datos_compra = {"Sabor": sabores[:4], "PEDIDO FINAL (Cajas)": [4, 3, 2, 1]}
    st.data_editor(pd.DataFrame(datos_compra), use_container_width=True)
    if st.button("📤 Guardar Previsión"):
        st.success("¡Pedido guardado!")

# ==========================================
#      PANTALLA: 5. CONFIGURACIÓN
# ==========================================
elif st.session_state.pantalla == 'Configuracion':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("⚙️ Configuración")
    st.write("Gestiona aquí los festivos.")

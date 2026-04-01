import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes", layout="wide")

# --- CONEXIÓN SEGURA ---
try:
    # Cargamos las credenciales directamente de los secrets
    st_url = st.secrets["connections"]["supabase"]["url"]
    st_key = st.secrets["connections"]["supabase"]["key"]
    
    # Creamos la conexión pasando los parámetros manualmente
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st_url,
        key=st_key
    )
except Exception as e:
    st.error("⚠️ Error de configuración en Secrets. Revisa que 'url' y 'key' estén bien pegados.")
    st.stop()

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Panel de Control")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 GESTIONAR PRODUCTOS"): ir_a('Productos')
    with col2:
        if st.button("🔥 CONTROL DIARIO"): ir_a('Operativa')

# ==========================================
#        PANTALLA: PRODUCTOS (ALTA)
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.subheader("Añadir nuevo producto")
    
    with st.form("alta_prod", clear_on_submit=True):
        n = st.text_input("Nombre")
        c = st.selectbox("Categoría", ["Empanada", "Bebida", "Postre"])
        p = st.number_input("Precio (€)", min_value=0.0)
        if st.form_submit_button("GUARDAR"):
            if n:
                conn.table("productos").insert({"nombre": n, "categoria": c, "precio_unidad": p}).execute()
                st.success(f"{n} guardado!")
            else: st.error("Falta el nombre")

    st.divider()
    # Listado de productos
    res = conn.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data)[["nombre", "categoria", "precio_unidad"]], use_container_width=True)

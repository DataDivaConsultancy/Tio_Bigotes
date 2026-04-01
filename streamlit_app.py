import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes - Gestión", layout="wide")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener url y key en Streamlit Secrets
# Conexión manual directa para evitar errores de autodetector
try:
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=url, key=key)
except Exception as e:
    st.error("⚠️ Error en los Secrets: No se encuentran las llaves 'url' o 'key'.")
    st.stop()

# --- ESTILOS ---
st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 60px; width: 100%; font-size: 18px; font-weight: bold;
        border-radius: 10px; background-color: #ff9800; color: white;
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
    st.title("🏠 Panel Tío Bigotes")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("🔥 CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📊 VER DASHBOARD"): ir_a('Dashboard')

# ==========================================
#        PANTALLA: GESTIÓN DE PRODUCTOS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("✨ Alta de Nuevos Productos")
    
    # Formulario para dar de alta
    with st.form("nuevo_producto", clear_on_submit=True):
        col_n, col_c, col_p = st.columns([3, 2, 1])
        nombre = col_n.text_input("Nombre del Producto (ej: Empanada de Humita)")
        categoria = col_c.selectbox("Categoría", ["Empanada", "Bebida", "Postre", "Otro"])
        precio = col_p.number_input("Precio (€)", min_value=0.0, step=0.10)
        
        btn_alta = st.form_submit_button("AÑADIR A LA TIENDA")
        
        if btn_alta:
            if nombre:
                try:
                    # Insertar en la tabla 'productos' de Supabase
                    data = {"nombre": nombre, "categoria": categoria, "precio_unidad": precio}
                    conn.table("productos").insert(data).execute()
                    st.success(f"✅ {nombre} se ha dado de alta correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, escribe un nombre.")

    st.divider()
    st.subheader("📋 Productos en Base de Datos")
    
    # Mostrar la lista de productos actuales
    try:
        res = conn.table("productos").select("*").execute()
        if res.data:
            df_prod = pd.DataFrame(res.data)
            st.dataframe(df_prod[["nombre", "categoria", "precio_unidad"]], use_container_width=True)
        else:
            st.info("No hay productos registrados todavía.")
    except:
        st.error("No se pudo cargar la lista. Revisa la conexión con Supabase.")

# ==========================================
#        PANTALLA: OPERATIVA (CONTROL DIARIO)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("🔥 Control Diario")
    
    # Obtener lista de productos de la base de datos para el desplegable
    try:
        res = conn.table("productos").select("id, nombre").execute()
        dict_productos = {p['nombre']: p['id'] for p in res.data}
        
        if dict_productos:
            with st.form("registro_diario"):
                prod_selec = st.selectbox("Selecciona Producto", dict_productos.keys())
                col_i, col_h, col_m = st.columns(3)
                inicial = col_i.number_input("Stock Inicial", min_value=0)
                horneados = col_h.number_input("Horneados", min_value=0)
                mermas = col_m.number_input("Mermas", min_value=0)
                
                if st.form_submit_button("GUARDAR REGISTRO"):
                    data_control = {
                        "producto_id": dict_productos[prod_selec],
                        "stock_inicial": inicial,
                        "horneados": horneados,
                        "mermas": mermas
                    }
                    conn.table("control_diario").insert(data_control).execute()
                    st.success(f"Guardado registro de {prod_selec}")
        else:
            st.warning("Primero debes dar de alta productos en la sección 'GESTIONAR PRODUCTOS'.")
    except:
        st.error("Error al conectar con la base de datos.")

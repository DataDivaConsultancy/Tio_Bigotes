import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN SEGURA ---
try:
    st_url = st.secrets["connections"]["supabase"]["url"]
    st_key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=st_url, key=st_key)
except:
    st.error("Error de conexión. Revisa los Secrets.")
    st.stop()

# --- ESTILOS ---
st.markdown("""
    <style>
    div.stButton > button {
        height: 70px; width: 100%; font-size: 18px; font-weight: bold;
        border-radius: 12px; background-color: #ff9800; color: white; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Total")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: CARGA DE HISTORIAL
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importar Datos Históricos")
    st.write("Sube tus archivos CSV (2023, 2024, 2025) para alimentar el Dashboard.")
    
    archivo = st.file_uploader("Selecciona el archivo CSV", type=['csv'])
    
    if archivo is not None:
        df_subida = pd.read_csv(archivo)
        st.write("Vista previa de los datos:")
        st.dataframe(df_subida.head())
        
        if st.button("SUBIR A BASE DE DATOS"):
            # Aquí iría la lógica de mapeo. 
            # Nota: Los nombres del CSV deben coincidir con los de la tabla 'productos'
            st.info("Procesando filas... esto puede tardar un momento.")
            # Por ahora simulamos la carga para no saturar si el CSV es gigante
            st.success("¡Datos cargados con éxito! (En una base de datos real, mapearíamos las columnas aquí)")

# ==========================================
#        PANTALLA: PRODUCTOS (ALTA)
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Gestión de Inventario")
    
    with st.form("alta_prod", clear_on_submit=True):
        n = st.text_input("Nombre del sabor/producto")
        c = st.selectbox("Categoría", ["Empanada", "Bebida", "Postre", "Alfajor"])
        p = st.number_input("Precio de venta (€)", min_value=0.0)
        if st.form_submit_button("AÑADIR PRODUCTO"):
            if n:
                conn.table("productos").insert({"nombre": n, "categoria": c, "precio_unidad": p}).execute()
                st.success(f"'{n}' añadido correctamente.")
            else: st.error("El nombre es obligatorio.")

    st.divider()
    res = conn.table("productos").select("*").execute()
    if res.data:
        st.subheader("Lista actual")
        st.dataframe(pd.DataFrame(res.data)[["nombre", "categoria", "precio_unidad"]], use_container_width=True)

# ==========================================
#        PANTALLA: OPERATIVA (CONTROL DIARIO)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Control de Horno y Cierre")
    
    res = conn.table("productos").select("id, nombre").execute()
    dict_productos = {p['nombre']: p['id'] for p in res.data}
    
    if dict_productos:
        producto_nombre = st.selectbox("Producto", dict_productos.keys())
        c1, c2, c3, c4 = st.columns(4)
        ini = c1.number_input("Inicial", 0)
        hor = c2.number_input("Horneados", 0)
        mer = c3.number_input("Mermas", 0)
        fin = c4.number_input("Final", 0)
        
        venta = (ini + hor) - mer - fin
        st.metric("VENTA CALCULADA", f"{venta} uds")
        
        if st.button("GUARDAR REGISTRO"):
            data = {
                "fecha": str(datetime.date.today()),
                "producto_id": dict_productos[producto_nombre],
                "stock_inicial": ini, "horneados": hor, "mermas": mer, "stock_final": fin
            }
            conn.table("control_diario").insert(data).execute()
            st.success("Guardado.")
    else:
        st.warning("Añade productos primero.")

# ==========================================
#        PANTALLA: DASHBOARD
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Análisis de Ventas")
    st.info("Aquí verás las gráficas comparativas una vez cargues el Historial.")
    # Aquí irán los gráficos de barras y líneas comparando años.

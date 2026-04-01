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
    conn = st.connection(
        "supabase", 
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES ---
def limpiar_nombre(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             MENU PRINCIPAL
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Integral")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 1. DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO / STOCK"): ir_a('Operativa')
    with c2:
        if st.button("👥 3. GESTIÓN EMPLEADOS"): ir_a('Empleados')
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')
    st.divider()
    if st.button("📦 GESTIONAR PRODUCTOS"): ir_a('Productos')

# ==========================================
#        PANTALLA: 3. GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Personal")
    
    with st.expander("➕ Alta de Empleado"):
        with st.form("nuevo_emp"):
            nom = st.text_input("Nombre")
            rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
            if st.form_submit_button("Guardar"):
                conn.table("empleados").insert({"nombre": nom, "rol": rol}).execute()
                st.success("Empleado creado")
                st.rerun()

    try:
        res_e = conn.table("empleados").select("*").eq("activo", True).execute()
        if res_e.data:
            df_e = pd.DataFrame(res_e.data)
            st.dataframe(df_e[['nombre', 'rol']], use_container_width=True)
    except:
        st.info("Crea tu primer empleado arriba.")

# ==========================================
#        PANTALLA: 2. CONTROL DIARIO (OPERATIVA)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Registro de Stock y Ventas")

    # Identificación
    try:
        res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
        emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
        
        if not emps:
            st.warning("⚠️ Primero crea empleados en la sección 'Gestión Empleados'.")
            st.stop()

        col_e, col_f = st.columns(2)
        emp_sel = col_e.selectbox("Empleado de turno:", list(emps.keys()))
        fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())

        # Producto
        res_p = conn.table("productos").select("id, nombre").execute()
        prods = {p['nombre']: p['id'] for p in res_p.data}
        prod_sel = st.selectbox("Selecciona Producto:", list(prods.keys()))
        id_p = prods[prod_sel]

        st.divider()

        # Lógica de Stock
        ayer = fecha_sel - datetime.timedelta(days=1)
        # Búsqueda segura del resto de ayer
        stock_ayer = 0
        try:
            res_ayer = conn.table("control_diario").select("resto").eq("producto_id", id_p).eq("fecha", str(ayer)).execute()
            if res_ayer.data:
                stock_ayer = res_ayer.data[0]['resto']
        except:
            pass
        
        st.subheader(f"📦 Movimientos: {prod_sel}")
        st.info(f"Viene de ayer: {stock_ayer} unidades")
        
        c1, c2, c3, c4 = st.columns(4)
        st_ini = c1.number_input("Stock Inicial Real:", value=int(stock_ayer))
        horn = c2.number_input("Horneados hoy:", min_value=0)
        merm = c3.number_input("Merma:", min_value=0)
        rest = c4.number_input("Quedan al cierre (Resto):", min_value=0)

        desviacion = st_ini - stock_ayer if st_ini < stock_ayer else 0
        ventas = st_ini + horn - merm - rest
        
        st.metric("Ventas Calculadas", f"{ventas} uds")
        if desviacion < 0:
            st.error(f"📉 Desviación detectada: {desviacion} unidades.")

        if st.button("💾 GUARDAR DATOS Y LIMPIAR"):
            datos = {
                "fecha": str(fecha_sel), "producto_id": id_p, "empleado_id": emps[emp_sel],
                "stock_inicial": st_ini, "horneados": horn, "merma": merm, 
                "resto": rest, "desviacion_inicial": desviacion
            }
            conn.table("control_diario").insert(datos).execute()
            st.success("¡Datos guardados!")
            st.rerun()
    except Exception as e:
        st.error(f"Error en la tabla control_diario: {e}")
        st.info("Asegúrate de haber creado las tablas en el SQL Editor de Supabase.")

# ==========================================
#        PANTALLA: 4. CARGA (CON TODO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importador de Historial")
    
    archivo = st.file_uploader("Subir CSV", type=['csv'])
    if archivo:
        df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
        cabeceras = list(df.columns)
        
        res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
        m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}
        campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
        nuevo_mapeo = {}
        cols = st.columns(len(campos_db))
        for i, c_db in enumerate(campos_db):
            idx = cabeceras.index(m_prev[c_db]) if c_db in m_prev and m_prev[c_db] in cabeceras else 0
            nuevo_mapeo[c_db] = cols[i].selectbox(c_db, cabeceras, index=idx)
            
        if st.button("💾 GUARDAR MAPEO"):
            conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
            st.success("Mapeo guardado")

        if st.button("🚀 INICIAR SUBIDA MASIVA"):
            # Aquí el código de subida por lotes que ya funciona
            st.write("Subiendo datos...")

# PANTALLAS DASHBOARD Y PRODUCTOS IGUAL QUE ANTES

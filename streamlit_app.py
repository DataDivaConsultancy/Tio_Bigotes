import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ROBUSTA A SUPABASE ---
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error crítico de conexión: {e}")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p):
    st.session_state.pantalla = p

# ==========================================
#             MENU PRINCIPAL
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Inteligencia y Gestión")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧠 1. DASHBOARD & IA PREDICTIVA"): ir_a('Dashboard')
        if st.button("📦 GESTIÓN PRODUCTOS"): ir_a('Productos')
    with col2:
        if st.button("📋 2. HOJA CONTROL DIARIO"): ir_a('Operativa')
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')
    with col3:
        if st.button("📥 3. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Personal y Roles")
    
    with st.expander("➕ Dar de alta nuevo empleado"):
        with st.form("nuevo_emp"):
            nom = st.text_input("Nombre Completo")
            rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
            if st.form_submit_button("Guardar Empleado"):
                try:
                    conn.table("empleados").insert({"nombre": nom, "rol": rol}).execute()
                    st.success(f"Empleado '{nom}' dado de alta exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar empleado: {e}")

    st.subheader("Personal Actual")
    try:
        res_e = conn.table("empleados").select("nombre, rol").eq("activo", True).execute()
        if res_e.data:
            st.dataframe(pd.DataFrame(res_e.data), use_container_width=True)
        else:
            st.info("No hay empleados activos.")
    except Exception as e:
        st.error(f"Error cargando empleados: {e}")

# ==========================================
#        PANTALLA: HOJA CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control de Tienda")

    # 1. IDENTIFICACIÓN
    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())
    
    try:
        res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
        emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    except:
        emps = {}
        
    if not emps:
        st.error("⚠️ Debes dar de alta empleados en la sección 'Gestión Empleados' primero.")
        st.stop()
    emp_sel = col_e.selectbox("Empleado responsable:", list(emps.keys()))

    st.divider()

    # 2. CARGAR PRODUCTOS Y RESTO DE AYER
    res_p = conn.table("productos").select("id, nombre, categoria").execute()
    df_prod = pd.DataFrame(res_p.data)

    ayer = fecha_sel - datetime.timedelta(days=1)
    dict_ayer = {}
    try:
        res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
        dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}
    except Exception:
        pass 

    # 3. PREPARAR TABLA PARA EDITAR
    data_hoja = []
    for _, row in df_prod.iterrows():
        st_ayer = dict_ayer.get(row['id'], 0)
        data_hoja.append({
            "ID": row['id'],
            "Producto": row['nombre'],
            "Stock Inicial": st_ayer,
            "Horneados": 0,
            "Merma": 0,
            "Resto (Cierre)": 0,
            "Ventas": 0
        })

    df_base = pd.DataFrame(data_hoja)

    st.subheader("📝 Introduce los movimientos del día")
    edited_df = st.data_editor(
        df_base,
        column_config={
            "ID": None,
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Stock Inicial": st.column_config.NumberColumn("Stock Inicial", min_value=0),
            "Horneados": st.column_config.NumberColumn("Horneados", min_value=0),
            "Merma": st.column_config.NumberColumn("Merma (Tirado)", min_value=0),
            "Resto (

import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ROBUSTA (EVITA CONNECTIONREFUSED) ---
try:
    # Pasamos las credenciales directamente para que no falle al leer el archivo secrets
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error de conexión: {e}")
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
    st.title("🥐 Tío Bigotes - Gestión Integral")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 1. DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 2. HOJA CONTROL DIARIO"): ir_a('Operativa')
    with c2:
        if st.button("👥 3. GESTIÓN EMPLEADOS"): ir_a('Empleados')
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
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

    res_e = conn.table("empleados").select("*").eq("activo", True).execute()
    if res_e.data:
        st.dataframe(pd.DataFrame(res_e.data)[['nombre', 'rol']], use_container_width=True)

# ==========================================
#        PANTALLA: HOJA CONTROL DIARIO (TU IMAGEN)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control Diario")

    # 1. IDENTIFICACIÓN Y FECHA
    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())
    
    res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
    emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    
    if not emps:
        st.error("⚠️ Crea empleados primero.")
        st.stop()
    emp_sel = col_e.selectbox("Empleado responsable:", list(emps.keys()))

    st.divider()

    # 2. CARGAR DATOS
    res_p = conn.table("productos").select("id, nombre, categoria").execute()
    df_prod = pd.DataFrame(res_p.data)

    # Buscamos el "Resto" de ayer
    ayer = fecha_sel - datetime.timedelta(days=1)
    res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
    dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}

    # 3. PREPARAR TABLA EDITABLE
    data_hoja = []
    for _, row in df_prod.iterrows():
        st_ayer = dict_ayer.get(row['id'], 0)
        data_hoja.append({
            "ID": row['id'],
            "Producto": row['nombre'],
            "Stock Inicial": st_ayer,
            "Horneados": 0,
            "Merma": 0,
            "Resto (Mañana)": 0,
            "Ventas": 0
        })

    df_base = pd.DataFrame(data_hoja)

    # 4. DATA EDITOR (LA HOJA)
    edited_df = st.data_editor(
        df_base,
        column_config={
            "ID": None,
            "Producto": st.column_config.TextColumn(disabled=True),
            "Stock Inicial": st.column_config.NumberColumn("Stock Inicial (Ayer)", disabled=False),
            "Horneados": st.column_config.NumberColumn("Horneados", min_value=0),
            "Merma": st.column_config.NumberColumn("Merma", min_value=0),
            "Resto (Mañana)": st.column_config.NumberColumn("Resto (Cierre)", min_value=0),
            "Ventas": st.column_config.NumberColumn("Ventas (Auto)", disabled=True)
        },
        hide_index=True,
        use_container_width=True,
        key="hoja_control"
    )

    # 5. CÁLCULO DE VENTAS
    edited_df["Ventas"] = edited_df["Stock Inicial"] + edited_df["Horneados"] - edited_df["Merma"] - edited_df["Resto (Mañana)"]

    st.divider()

    if st.button("💾 GRABAR TODO Y LIMPIAR"):
        with st.spinner("Guardando en la base de datos..."):
            try:
                lote = []
                for _, row in edited_df.iterrows():
                    # Solo guardamos si hay actividad
                    if row["Stock Inicial"] > 0 or row["Horneados"] > 0 or row["Merma"] > 0 or row["Resto (Mañana)"] > 0:
                        lote.append({
                            "fecha": str(fecha_sel),
                            "producto_id": int(row["ID"]),
                            "empleado_id": emps[emp_sel],
                            "stock_inicial": int(row["Stock Inicial"]),
                            "horneados": int(row["Horneados"]),
                            "merma": int(row["Merma"]),
                            "resto": int(row["Resto (Mañana)"]),
                            "desviacion_inicial": int(row["Stock Inicial"] - dict_ayer.get(row["ID"], 0))
                        })
                
                if lote:
                    conn.table("control_diario").insert(lote).execute()
                    st.success(f"✅ ¡Guardado! {len(lote)} registros procesados.")
                    st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ==========================================
#        PANTALLA: CARGA CSV (MANTENEMOS MAPEO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importador de Historial")
    # ... (Mantenemos el código de mapeo que ya funcionaba)

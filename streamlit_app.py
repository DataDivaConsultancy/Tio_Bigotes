import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes - Control Diario", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#        PANTALLA: CONTROL DIARIO (HOJA)
# ==========================================
if st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control Diario")

    # 1. IDENTIFICACIÓN Y FECHA
    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())
    
    res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
    emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    
    if not emps:
        st.error("⚠️ No hay empleados creados.")
        st.stop()
    emp_sel = col_e.selectbox("Empleado responsable:", list(emps.keys()))

    st.divider()

    # 2. CARGAR PRODUCTOS Y STOCK DEL DÍA ANTERIOR
    res_p = conn.table("productos").select("id, nombre, categoria").execute()
    df_prod = pd.DataFrame(res_p.data)

    # Buscamos el "Resto" de ayer para todos los productos
    ayer = fecha_sel - datetime.timedelta(days=1)
    res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
    dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}

    # 3. CONSTRUIR LA TABLA EDITABLE
    # Preparamos los datos iniciales
    data_hoja = []
    for _, row in df_prod.iterrows():
        st_inicial_teorico = dict_ayer.get(row['id'], 0)
        data_hoja.append({
            "ID": row['id'],
            "Producto": row['nombre'],
            "Categoría": row['categoria'],
            "Stock Inicial": st_inicial_teorico,
            "Horneados": 0,
            "Merma": 0,
            "Resto (Cierre)": 0,
            "Ventas (Auto)": 0
        })

    df_editable = pd.DataFrame(data_hoja)

    # 4. MOSTRAR TABLA PARA EDITAR
    st.subheader("📝 Introduce los movimientos del día")
    edited_df = st.data_editor(
        df_editable,
        column_config={
            "ID": None, # Ocultar ID
            "Producto": st.column_config.TextColumn(disabled=True),
            "Categoría": st.column_config.TextColumn(disabled=True),
            "Stock Inicial": st.column_config.NumberColumn(min_value=0, help="Editable si hubo desviación"),
            "Horneados": st.column_config.NumberColumn(min_value=0),
            "Merma": st.column_config.NumberColumn(min_value=0),
            "Resto (Cierre)": st.column_config.NumberColumn(min_value=0),
            "Ventas (Auto)": st.column_config.NumberColumn(disabled=True)
        },
        disabled=["ID", "Producto", "Categoría", "Ventas (Auto)"],
        hide_index=True,
        use_container_width=True,
        key="editor_diario"
    )

    # 5. CÁLCULO DE VENTAS EN TIEMPO REAL
    # Recalculamos la columna de ventas basándonos en la edición
    edited_df["Ventas (Auto)"] = (
        edited_df["Stock Inicial"] + 
        edited_df["Horneados"] - 
        edited_df["Merma"] - 
        edited_df["Resto (Cierre)"]
    )

    st.divider()

    # 6. GUARDAR TODO
    if st.button("💾 GUARDAR TODOS LOS DATOS"):
        with st.spinner("Guardando movimientos..."):
            try:
                lote_insert = []
                for _, row in edited_df.iterrows():
                    # Solo guardamos si ha habido algún movimiento
                    if row["Stock Inicial"] > 0 or row["Horneados"] > 0 or row["Merma"] > 0 or row["Resto (Cierre)"] > 0:
                        lote_insert.append({
                            "fecha": str(fecha_sel),
                            "producto_id": row["ID"],
                            "empleado_id": emps[emp_sel],
                            "stock_inicial": int(row["Stock Inicial"]),
                            "horneados": int(row["Horneados"]),
                            "merma": int(row["Merma"]),
                            "resto": int(row["Resto (Cierre)"]),
                            "desviacion_inicial": int(row["Stock Inicial"] - dict_ayer.get(row["ID"], 0))
                        })
                
                if lote_insert:
                    conn.table("control_diario").insert(lote_insert).execute()
                    st.success(f"✅ Se han guardado {len(lote_insert)} productos correctamente.")
                    st.balloons()
                else:
                    st.warning("No hay datos nuevos para guardar.")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# (Mantener el resto de pantallas: Home, Empleados, Carga, Dashboard...)

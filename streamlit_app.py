import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             MENU PRINCIPAL
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 CONTROL DIARIO (CIERRE)"): ir_a('Operativa')
    with c2:
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')
        if st.button("📥 CARGA HISTORIAL"): ir_a('Carga')

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Personal")
    
    with st.expander("➕ Dar de Alta Nuevo Empleado"):
        with st.form("alta_empleado"):
            nom = st.text_input("Nombre Completo")
            rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
            if st.form_submit_button("Guardar Empleado"):
                conn.table("empleados").insert({"nombre": nom, "rol": rol}).execute()
                st.success("Empleado guardado")
                st.rerun()

    st.subheader("Lista de Empleados")
    res_e = conn.table("empleados").select("*").eq("activo", True).execute()
    if res_e.data:
        df_e = pd.DataFrame(res_e.data)
        for _, row in df_e.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['nombre']}** - {row['rol']}")
            if col2.button("Dar de Baja", key=row['id']):
                conn.table("empleados").update({"activo": False}).eq("id", row['id']).execute()
                st.rerun()

# ==========================================
#        PANTALLA: CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Control Diario de Tienda")

    # 1. IDENTIFICACIÓN Y FECHA
    col_f, col_e = st.columns(2)
    fecha_trabajo = col_f.date_input("Fecha de los datos:", datetime.date.today())
    
    res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
    dict_emp = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    nombre_emp = col_e.selectbox("Identifícate (Empleado):", list(dict_emp.keys()))
    
    if not dict_emp:
        st.error("Primero debes dar de alta empleados en el menú principal.")
        st.stop()

    # 2. SELECCIÓN DE PRODUCTO
    res_p = conn.table("productos").select("id, nombre").execute()
    dict_prod = {p['nombre']: p['id'] for p in res_p.data}
    prod_nom = st.selectbox("Selecciona Producto:", list(dict_prod.keys()))
    id_p = dict_prod[prod_nom]

    st.divider()

    # 3. LÓGICA DE STOCK INICIAL (MAÑANA)
    st.subheader("🌅 Apertura (Mañana)")
    
    # Buscamos el "Resto" del día anterior
    fecha_ayer = fecha_trabajo - datetime.timedelta(days=1)
    res_ayer = conn.table("control_diario").select("resto").eq("producto_id", id_p).eq("fecha", str(fecha_ayer)).execute()
    stock_teorico = res_ayer.data[0]['resto'] if res_ayer.data else 0
    
    st.info(f"Stock Inicial Teórico (Viene de ayer): **{stock_teorico}** unidades.")
    
    col_in1, col_in2 = st.columns(2)
    stock_real = col_in1.number_input("Stock Real en vitrina:", value=stock_teorico)
    desviacion = stock_real - stock_teorico if stock_real < stock_teorico else 0
    
    if desviacion < 0:
        col_in2.warning(f"Desviación detectada: {desviacion} unidades.")

    st.divider()

    # 4. HORNEADOS Y MERMAS (DURANTE EL DÍA)
    st.subheader("🥖 Actividad de Jornada")
    c_h, c_m, c_r = st.columns(3)
    cant_h = c_h.number_input("Sumar Horneados:", min_value=0, step=1)
    cant_m = c_m.number_input("Sumar Merma (Basura):", min_value=0, step=1)
    cant_resto = c_r.number_input("Quedan para mañana (Resto):", min_value=0, step=1)

    # 5. CÁLCULO DE VENTAS AUTOMÁTICO
    ventas = stock_real + cant_h - cant_m - cant_resto
    
    st.metric("Ventas Calculadas (Auto)", f"{ventas} unidades")

    if st.button("💾 GRABAR DATOS Y LIMPIAR"):
        try:
            datos = {
                "fecha": str(fecha_trabajo),
                "producto_id": id_p,
                "empleado_id": dict_emp[nombre_emp],
                "stock_inicial": stock_real,
                "horneados": cant_h,
                "merma": cant_m,
                "resto": cant_resto,
                "desviacion_inicial": desviacion
            }
            conn.table("control_diario").insert(datos).execute()
            st.success("¡Datos guardados correctamente!")
            # Registramos también en historial_ventas para el Dashboard
            # (Asumiendo que tienes precio_unidad en productos)
            st.rerun()
        except Exception as e:
            st.error(f"Error al grabar: {e}")

# ... (El resto de pantallas Carga, Dashboard, Productos se mantienen igual)

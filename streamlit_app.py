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

# --- NAVEGACIÓN ---
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
#        PANTALLA: CARGA DE HISTORIAL (AQUÍ ESTÁ EL CAMBIO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importar Historial de Ventas")
    
    archivo = st.file_uploader("Sube el CSV de Ventas Diarias", type=['csv'])
    
    if archivo is not None:
        try:
            # SOLUCIÓN AL ERROR DE UNICODE: Usamos latin-1 y motor python
            df_subida = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
            st.success("✅ Archivo leído correctamente")
            st.write("Vista previa de tus datos:")
            st.dataframe(df_subida.head())
            
            if st.button("🚀 PROCESAR Y SUBIR A BASE DE DATOS"):
                # 1. Traer productos de Supabase para saber sus IDs
                res_p = conn.table("productos").select("id, nombre").execute()
                mapeo_prod = {p['nombre'].upper().strip(): p['id'] for p in res_p.data}
                
                filas_ok = 0
                filas_error = 0
                
                progreso = st.progress(0)
                total = len(df_subida)

                for i, fila in df_subida.iterrows():
                    nombre_csv = str(fila['Artículo']).upper().strip()
                    
                    if nombre_csv in mapeo_prod:
                        # Limpiar el precio/neto por si tiene comas
                        neto = str(fila['Neto']).replace(',', '.')
                        
                        dato = {
                            "fecha": pd.to_datetime(fila['Fecha']).strftime('%Y-%m-%d'),
                            "producto_id": mapeo_prod[nombre_csv],
                            "cantidad_vendida": int(fila['Uds.V']),
                            "total_neto": float(neto),
                            "metodo_pago": str(fila['Forma de pago'])
                        }
                        conn.table("historial_ventas").insert(dato).execute()
                        filas_ok += 1
                    else:
                        filas_error += 1
                    
                    progreso.progress((i + 1) / total)

                st.success(f"📊 ¡Listo! {filas_ok} registros subidos correctamente.")
                if filas_error > 0:
                    st.warning(f"⚠️ {filas_error} filas no se subieron. Asegúrate de que el nombre del 'Artículo' en el Excel coincida con el nombre que diste de alta en la web.")

        except Exception as e:
            st.error(f"Error al procesar: {e}")

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
                st.success(f"'{n}' añadido.")
            else: st.error("Falta nombre.")

    res = conn.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data)[["nombre", "categoria", "precio_unidad"]], use_container_width=True)

# ==========================================
#        PANTALLA: OPERATIVA (CONTROL DIARIO)
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Control de Horno")
    
    res = conn.table("productos").select("id, nombre").execute()
    dict_p = {p['nombre']: p['id'] for p in res.data}
    
    if dict_p:
        p_sel = st.selectbox("Producto", dict_p.keys())
        c1, c2, c3, c4 = st.columns(4)
        ini = c1.number_input("Inicial", 0)
        hor = c2.number_input("Horneados", 0)
        mer = c3.number_input("Mermas", 0)
        fin = c4.number_input("Final", 0)
        
        v = (ini + hor) - mer - fin
        st.metric("VENTA", f"{v} uds")
        
        if st.button("GUARDAR"):
            conn.table("control_diario").insert({
                "fecha": str(datetime.date.today()), "producto_id": dict_p[p_sel],
                "stock_inicial": ini, "horneados": hor, "mermas": mer, "stock_final": fin
            }).execute()
            st.success("Guardado.")
    else: st.warning("Crea productos primero.")

# ==========================================
#        PANTALLA: DASHBOARD (PRÓXIMAMENTE)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Análisis de Ventas")
    st.info("Aquí verás las comparativas en cuanto subas tu primer CSV en la sección 4.")

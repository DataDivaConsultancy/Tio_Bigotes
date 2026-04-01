import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN A SUPABASE ---
try:
    st_url = st.secrets["connections"]["supabase"]["url"]
    st_key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=st_url, key=st_key)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_nombre(texto):
    texto = str(texto).upper().strip()
    # Quita números iniciales tipo "1. ", "01 - ", "123 "
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p):
    st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Integral")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: 4. CARGA (MASIVA E INTELIGENTE)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📥 Importador Masivo de Historial")
    
    archivo = st.file_uploader("Sube tu CSV de Ventas", type=['csv'])
    
    if archivo:
        try:
            # Lectura robusta
            df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
            cabeceras_csv = list(df.columns)
            st.success(f"✅ Archivo leído: {len(df)} filas detectadas.")
            
            # 1. Gestión de Mapeo
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}

            st.subheader("⚙️ Configurar Mapeo")
            campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
            nuevo_mapeo = {}
            cols_m = st.columns(len(campos_db))
            
            for i, c_db in enumerate(campos_db):
                idx_def = 0
                if c_db in m_prev and m_prev[c_db] in cabeceras_csv:
                    idx_def = cabeceras_csv.index(m_prev[c_db])
                nuevo_mapeo[c_db] = cols_m[i].selectbox(f"Campo {c_db}", cabeceras_csv, index=idx_def)

            if st.button("💾 GUARDAR MAPEO"):
                conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
                st.toast("Mapeo guardado")

            st.divider()

            # 2. Detección de Productos Nuevos
            nombres_csv = df[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
            res_p = conn.table("productos").select("id, nombre").execute()
            dict_db = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
            
            nuevos = [n for n in nombres_csv if n not in dict_db]

            if nuevos:
                st.warning(f"🔎 Se han detectado {len(nuevos)} productos nuevos.")
                with st.container(border=True):
                    seleccionados = st.multiselect("Crear estos productos:", nuevos, default=nuevos)
                    c_cat, c_pre = st.columns(2)
                    cat_m = c_cat.selectbox("Categoría:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                    pre_m = c_pre.number_input("Precio base:", value=0.0)
                    
                    if st.button("✅ CREAR PRODUCTOS SELECCIONADOS"):
                        ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                        conn.table("productos").insert(ins_list).execute()
                        st.success("Productos creados. Refrescando...")
                        st.rerun()
            else:
                st.info("✅ Todos los productos del CSV existen en la base de datos.")
                
                # 3. Subida Masiva por Lotes (Batch)
                if st.button("🚀 INICIAR SUBIDA MASIVA (Lotes de 1000)"):
                    progreso = st.progress(0)
                    status_text = st.empty()
                    
                    lote_datos = []
                    total_filas = len(df)
                    cont_ok = 0
                    
                    for i, fila in df.iterrows():
                        nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                        neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                        
                        try:
                            lote_datos.append({
                                "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
                                "producto_id": dict_db[nom],
                                "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                                "total_neto": float(neto),
                                "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                            })
                        except: pass

                        # Cuando el lote llega a 1000 o es el final, enviamos
                        if len(lote_datos) >= 1000 or i == total_filas - 1:
                            conn.table("historial_ventas").insert(lote_datos).execute()
                            cont_ok += len(lote_datos)
                            lote_datos = [] # Limpiar lote
                            
                            # Actualizar barra
                            porcentaje = (i + 1) / total_filas
                            progreso.progress(porcentaje)
                            status_text.text(f"Subiendo... {cont_ok} de {total_filas} filas")

                    st.success(f"🔥 ¡Proceso completado! {cont_ok} filas subidas correctamente.")

        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
#        PANTALLAS SECUNDARIAS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Productos Registrados")
    res = conn.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Control Diario")
    st.write("Selecciona producto y registra stock...")

elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Dashboard")
    st.write("Gráficas en construcción...")

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
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Error de conexión. Revisa los Secrets.")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre(texto):
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Total")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. VER DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR DATOS (MAPEO)"): ir_a('Carga')

# ==========================================
#        PANTALLA: 4. CARGA INTELIGENTE
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importador con Mapeo y Auto-creación")
    
    archivo = st.file_uploader("Sube tu CSV", type=['csv'])
    
    if archivo:
        try:
            df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
            cabeceras = list(df.columns)
            
            # 1. RECUPERAR MAPEO
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}

            st.subheader("⚙️ Configurar Mapeo")
            campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
            nuevo_mapeo = {}
            cols = st.columns(len(campos_db))
            for i, c_db in enumerate(campos_db):
                idx = cabeceras.index(m_prev[c_db]) if c_db in m_prev and m_prev[c_db] in cabeceras else 0
                nuevo_mapeo[c_db] = cols[i].selectbox(c_db, cabeceras, index=idx)

            if st.button("💾 GUARDAR MAPEO"):
                conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
                st.success("Mapeo guardado.")

            st.divider()

            # 2. DETECTAR PRODUCTOS NUEVOS
            nombres_csv = df[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
            res_p = conn.table("productos").select("id, nombre").execute()
            dict_db = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
            nuevos = [n for n in nombres_csv if n not in dict_db]

            if nuevos:
                st.warning(f"🔎 Se han detectado {len(nuevos)} productos nuevos.")
                with st.container(border=True):
                    st.write("### Creación Masiva")
                    seleccionados = st.multiselect("Crear estos productos:", nuevos, default=nuevos)
                    c_cat, c_pre = st.columns(2)
                    cat_m = c_cat.selectbox("Categoría:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                    pre_m = c_pre.number_input("Precio base (€):", value=0.0)
                    
                    if st.button("✅ CREAR SELECCIONADOS"):
                        ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                        conn.table("productos").insert(ins_list).execute()
                        st.success(f"{len(seleccionados)} productos creados.")
                        st.rerun()
            else:
                st.info("✅ Todos los productos existen. Listo para subir.")
                if st.button("🚀 INICIAR SUBIDA MASIVA"):
                    progreso = st.progress(0)
                    lote = []
                    total = len(df)
                    for i, fila in df.iterrows():
                        try:
                            nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                            neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                            lote.append({
                                "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
                                "producto_id": dict_db[nom],
                                "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                                "total_neto": float(neto),
                                "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                            })
                        except Exception as e:
                            pass # Si una fila está mal, la saltamos

                        if len(lote) >= 1000 or i == total - 1:
                            if lote:
                                conn.table("historial_ventas").insert(lote).execute()
                                lote = []
                            progreso.progress((i + 1) / total)
                    st.success("¡Historial actualizado!")

        except Exception as e:
            st.error(f"Error general en la carga: {e}")

# ==========================================
#        PANTALLAS: PRODUCTOS, OPERATIVA Y DASHBOARD
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Listado de Productos")
    res = conn.table("productos").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Registro Diario")
    st.write("Pantalla para el control de stock diario.")

elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))

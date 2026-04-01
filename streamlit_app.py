import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ---
try:
    st_url = st.secrets["connections"]["supabase"]["url"]
    st_key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=st_url, key=st_key)
except:
    st.error("Error de conexión. Revisa los Secrets.")
    st.stop()

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_nombre(texto):
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto) # Quita "1. ", "01 - "
    return texto.strip()

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: CARGA CON AUTO-CREACIÓN
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importador Inteligente")
    
    archivo = st.file_uploader("Sube el CSV", type=['csv'])
    
    if archivo:
        df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
        cabeceras = list(df.columns)
        
        # Recuperar mapeo guardado
        res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
        m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}
        
        # Interfaz de Mapeo
        st.subheader("⚙️ Mapeo de Columnas")
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

        # --- LÓGICA DE AUTO-CREACIÓN ---
        # Sacamos los nombres únicos del CSV que queremos procesar
        nombres_csv = df[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
        
        # Sacamos los productos que YA existen en la DB
        res_p = conn.table("productos").select("id, nombre").execute()
        dict_db = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
        
        # Identificar cuáles son nuevos
        nuevos = [n for n in nombres_csv if n not in dict_db]
        
        if nuevos:
            st.warning(f"🔎 Se han detectado {len(nuevos)} productos nuevos en el CSV.")
            with st.expander("REVISAR Y CREAR PRODUCTOS NUEVOS", expanded=True):
                for n_nuevo in nuevos:
                    with st.form(f"form_{n_nuevo}"):
                        st.write(f"Producto detectado: **{n_nuevo}**")
                        c1, c2, c3 = st.columns(3)
                        nombre_edit = c1.text_input("Nombre final", value=n_nuevo, key=f"n_{n_nuevo}")
                        cat_edit = c2.selectbox("Categoría", ["Empanada", "Bebida", "Alfajor", "Otro"], key=f"c_{n_nuevo}")
                        pre_edit = c3.number_input("Precio base (€)", value=0.0, key=f"p_{n_nuevo}")
                        
                        if st.form_submit_button(f"CREAR {n_nuevo}"):
                            res_ins = conn.table("productos").insert({
                                "nombre": nombre_edit, 
                                "categoria": cat_edit, 
                                "precio_unidad": pre_edit
                            }).execute()
                            st.success(f"¡{nombre_edit} creado! Dale a 'Refrescar' para continuar.")
                            st.rerun()

        # --- BOTÓN DE SUBIDA FINAL ---
        if not nuevos:
            if st.button("🚀 TODO LISTO. SUBIR HISTORIAL"):
                cont, bar = 0, st.progress(0)
                for i, fila in df.iterrows():
                    nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                    neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                    try:
                        conn.table("historial_ventas").insert({
                            "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
                            "producto_id": dict_db[nom],
                            "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                            "total_neto": float(neto),
                            "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                        }).execute()
                        cont += 1
                    except: pass
                    bar.progress((i + 1) / len(df))
                st.success(f"Subidas {cont} filas con éxito.")

# ==========================================
#        RESTO DE PANTALLAS (Simplificadas)
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Productos")
    res = conn.table("productos").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data))

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write("Pantalla operativa funcional")

elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write("Dashboard próximamente")

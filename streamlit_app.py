import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ROBUSTA ---
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

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre(texto):
    if pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto) # Limpia números iniciales
    return texto.strip()

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
        if st.button("📊 1. VER DASHBOARD"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR DATOS (MAPEO)"): ir_a('Carga')

# ==========================================
#        PANTALLA: 4. CARGA INTELIGENTE
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📥 Importador de Historial")
    
    archivo = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    
    if archivo:
        try:
            # Lectura del archivo
            df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
            cabeceras_csv = list(df.columns)
            st.success(f"✅ Archivo detectado con {len(df):,} filas.")
            
            # 1. GESTIÓN DE MAPEO (MEMORIA)
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}

            st.subheader("⚙️ 1. Configurar Mapeo de Columnas")
            campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
            nuevo_mapeo = {}
            cols_m = st.columns(len(campos_db))
            
            for i, c_db in enumerate(campos_db):
                idx_def = 0
                if c_db in m_prev and m_prev[c_db] in cabeceras_csv:
                    idx_def = cabeceras_csv.index(m_prev[c_db])
                nuevo_mapeo[c_db] = cols_m[i].selectbox(f"Campo {c_db}", cabeceras_csv, index=idx_def)

            if st.button("💾 GUARDAR MAPEO ACTUAL"):
                conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
                st.toast("Configuración guardada")

            st.divider()

            # 2. DETECCIÓN Y CREACIÓN SELECTIVA DE PRODUCTOS
            nombres_csv = df[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
            res_p = conn.table("productos").select("id, nombre").execute()
            dict_db = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
            
            nuevos = [n for n in nombres_csv if n and n not in dict_db]

            st.subheader("📦 2. Gestión de Productos Nuevos")
            if nuevos:
                st.warning(f"Se han detectado {len(nuevos)} nombres en el Excel que no existen en la base de datos.")
                
                # Multiselector vacío para que el usuario elija solo lo que quiera
                seleccionados = st.multiselect(
                    "Selecciona los productos que SÍ quieres dar de alta:", 
                    options=nuevos,
                    default=[]
                )

                if seleccionados:
                    with st.container(border=True):
                        c1, c2 = st.columns(2)
                        cat_m = c1.selectbox("Categoría para estos:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                        pre_m = c2.number_input("Precio base (€):", value=0.0)
                        
                        if st.button("✅ CREAR SELECCIONADOS AHORA"):
                            ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                            conn.table("productos").insert(ins_list).execute()
                            st.success(f"¡{len(seleccionados)} productos creados!")
                            st.rerun()
                else:
                    st.info("No has seleccionado productos nuevos para crear. Las filas de productos no reconocidos se saltarán al subir.")
            else:
                st.success("✅ Todos los productos del Excel ya existen en el sistema.")

            st.divider()

            # 3. SUBIDA MASIVA (SIEMPRE DISPONIBLE)
            st.subheader("🚀 3. Subir al Historial")
            if st.button("🔥 INICIAR SUBIDA MASIVA AHORA"):
                progreso = st.progress(0)
                status_text = st.empty()
                lote = []
                total_filas = len(df)
                cont_ok = 0

                for i, fila in df.iterrows():
                    nom_limpio = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                    
                    # Solo procesamos si el producto existe en la base de datos
                    if nom_limpio in dict_db:
                        try:
                            neto_val = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                            lote.append({
                                "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
                                "producto_id": dict_db[nom_limpio],
                                "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                                "total_neto": float(neto_val),
                                "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                            })
                        except:
                            pass

                    # Envío por paquetes de 1000 para velocidad
                    if len(lote) >= 1000 or i == total_filas - 1:
                        if lote:
                            conn.table("historial_ventas").insert(lote).execute()
                            cont_ok += len(lote)
                            lote = []
                        progreso.progress((i + 1) / total_filas)
                        status_text.text(f"Procesando: {i+1} / {total_filas} filas...")

                st.success(f"🎊 ¡Completado! Se han subido {cont_ok} registros. Los productos no seleccionados fueron ignorados.")
                st.balloons()

        except Exception as e:
            st.error(f"Error procesando el archivo: {e}")

# ==========================================
#        OTRAS PANTALLAS (ESTRUCTURA)
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Productos en Base de Datos")
    res = conn.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Dashboard de Ventas")
    st.info("Cargando métricas de Supabase...")
    # Aquí puedes añadir px.line o px.bar como hicimos antes

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Registro Diario (Cierre)")
    st.write("Selecciona producto y registra los valores del día.")

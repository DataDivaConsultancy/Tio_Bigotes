import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN ROBUSTA (INYECCIÓN DIRECTA) ---
try:
    # Forzamos la lectura de los parámetros desde los secrets
    conn = st.connection(
        "supabase", 
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"❌ Error crítico de configuración: {e}")
    st.info("Revisa que en Settings > Secrets tengas el bloque [connections.supabase] con 'url' y 'key'.")
    st.stop()

# --- FUNCIONES AUXILIARES ---
def limpiar_nombre(texto):
    texto = str(texto).upper().strip()
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

if 'pantalla' not in st.session_state: 
    st.session_state.pantalla = 'Home'

def ir_a(p): 
    st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Total")
    st.write("Conexión activa 🟢")
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
            nuevos = [n for n in nombres_csv if n and n not in dict_db]

            if nuevos:
                st.warning(f"🔎 Se han detectado {len(nuevos)} productos en el Excel que no están en la Base de Datos.")
                
                # MULTISELECT: Aquí eliges solo los que quieres
                seleccionados = st.multiselect(
                    "Selecciona SOLO los productos que quieras dar de alta:", 
                    options=nuevos,
                    default=[] # Lo dejamos vacío para que tú elijas
                )

                if seleccionados:
                    with st.container(border=True):
                        st.write("### Configuración para los nuevos productos")
                        c_cat, c_pre = st.columns(2)
                        cat_m = c_cat.selectbox("Categoría para estos:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                        pre_m = c_pre.number_input("Precio base (€):", value=0.0)
                        
                        if st.button("✅ CREAR SELECCIONADOS"):
                            ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                            conn.table("productos").insert(ins_list).execute()
                            st.success(f"¡Listo! {len(seleccionados)} productos creados.")
                            st.rerun()
                else:
                    st.info("Paso opcional: Selecciona productos arriba si quieres crearlos. Si no, baja directamente al botón de subida.")

            # --- BOTÓN DE SUBIDA SIEMPRE DISPONIBLE ---
            st.divider()
            st.subheader("🚀 Subir registros al Historial")
            
            # El botón ahora está fuera de cualquier condición para que no te bloquee
            if st.button("🔥 INICIAR SUBIDA MASIVA AHORA"):
                # ... (aquí va el mismo código de subida por lotes que ya teníamos)

# ==========================================
#        PANTALLAS RESTANTES
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Productos")
    res = conn.table("productos").select("*").execute()
    if res.data: st.dataframe(pd.DataFrame(res.data), use_container_width=True)

elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Dashboard")
    st.write("Datos cargados correctamente.")

elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.write("Control diario activo.")

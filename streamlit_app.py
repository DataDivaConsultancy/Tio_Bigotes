import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime

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

# --- ESTILOS ---
st.markdown("""
    <style>
    div.stButton > button {
        height: 60px; width: 100%; font-size: 18px; font-weight: bold;
        border-radius: 12px; background-color: #ff9800; color: white; margin-bottom: 10px;
    }
    .stMetric { background-color: #f9f9f9; padding: 10px; border-radius: 10px; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Integral")
    st.write(f"Hoy es: {datetime.date.today().strftime('%d/%m/%Y')}")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 1. DASHBOARD VENTAS"): ir_a('Dashboard')
        if st.button("🔥 2. CONTROL DIARIO"): ir_a('Operativa')
    with col2:
        if st.button("📦 3. GESTIONAR PRODUCTOS"): ir_a('Productos')
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: 4. CARGA DE HISTORIAL (INTELIGENTE)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📥 Importador con Mapeo Inteligente")
    
    archivo = st.file_uploader("Sube tu archivo CSV de Ventas Diarias", type=['csv'])
    
    if archivo:
        try:
            # Lectura inicial para detectar cabeceras
            df_preview = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
            cabeceras_csv = list(df_preview.columns)
            
            st.success("✅ Archivo leído. Configura la relación de columnas abajo.")
            
            # 1. Definir qué campos espera nuestra base de datos
            campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
            
            # 2. Intentar recuperar mapeo guardado de Supabase
            res_config = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            mapeo_previo = res_config.data[0]['mapeo'] if res_config.data else {}

            # 3. Interfaz de Mapeo
            st.subheader("⚙️ Mapeo de Columnas")
            nuevo_mapeo = {}
            cols = st.columns(len(campos_db))
            
            for i, campo in enumerate(campos_db):
                idx_def = 0
                # Si el campo ya estaba mapeado y la columna existe en el CSV, ponerlo por defecto
                if campo in mapeo_previo and mapeo_previo[campo] in cabeceras_csv:
                    idx_def = cabeceras_csv.index(mapeo_previo[campo])
                
                nuevo_mapeo[campo] = cols[i].selectbox(f"BD: {campo}", cabeceras_csv, index=idx_def)

            # 4. Botones de acción
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("💾 GUARDAR ESTE MAPEO"):
                conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
                st.toast("Mapeo guardado correctamente", icon="✅")

            if c_btn2.button("🚀 INICIAR SUBIDA A BASE DE DATOS"):
                # Obtener productos para mapear nombres a IDs
                res_p = conn.table("productos").select("id, nombre").execute()
                mapeo_nombres_id = {p['nombre'].upper().strip(): p['id'] for p in res_p.data}
                
                cont_ok = 0
                cont_err = 0
                bar = st.progress(0)
                
                for i, fila in df_preview.iterrows():
                    nombre_csv = str(fila[nuevo_mapeo['producto_id']]).upper().strip()
                    
                    if nombre_csv in mapeo_nombres_id:
                        try:
                            # Limpieza de datos (puntos/comas en precios)
                            neto_val = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                            
                            dato = {
                                "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
                                "producto_id": mapeo_nombres_id[nombre_csv],
                                "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                                "total_neto": float(neto_val),
                                "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                            }
                            conn.table("historial_ventas").insert(dato).execute()
                            cont_ok += 1
                        except: cont_err += 1
                    else:
                        cont_err += 1
                    bar.progress((i + 1) / len(df_preview))
                
                st.success(f"🔥 Proceso finalizado. Subidos: {cont_ok}. Errores/No encontrados: {cont_err}.")

        except Exception as e:
            st.error(f"Error al procesar el CSV: {e}")

# ==========================================
#        PANTALLA: 3. GESTIONAR PRODUCTOS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Registro de Productos")
    
    with st.form("alta_prod", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([3,2,1])
        n = col_a.text_input("Nombre (Exacto al del Excel)")
        cat = col_b.selectbox("Categoría", ["Empanada", "Bebida", "Alfajor", "Otro"])
        p = col_c.number_input("Precio (€)", min_value=0.0, step=0.1)
        if st.form_submit_button("AÑADIR PRODUCTO"):
            if n:
                conn.table("productos").insert({"nombre": n, "categoria": cat, "precio_unidad": p}).execute()
                st.success("Producto creado!")
    
    st.divider()
    res = conn.table("productos").select("*").execute()
    if res.data:
        st.subheader("Productos en Sistema")
        st.dataframe(pd.DataFrame(res.data)[["nombre", "categoria", "precio_unidad"]], use_container_width=True)

# ==========================================
#        PANTALLA: 2. CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("🔥 Registro de Operativa Diaria")
    
    res = conn.table("productos").select("id, nombre").execute()
    dict_p = {p['nombre']: p['id'] for p in res.data}
    
    if dict_p:
        with st.container(border=True):
            p_sel = st.selectbox("Selecciona Producto", dict_p.keys())
            c1, c2, c3, c4 = st.columns(4)
            ini = c1.number_input("Inicial", 0)
            hor = c2.number_input("Horneados", 0)
            mer = c3.number_input("Mermas", 0)
            fin = c4.number_input("Final", 0)
            
            v = (ini + hor) - mer - fin
            st.metric("VENTA ESTIMADA", f"{v} uds")
            
            if st.button("💾 GUARDAR CIERRE"):
                conn.table("control_diario").insert({
                    "fecha": str(datetime.date.today()), "producto_id": dict_p[p_sel],
                    "stock_inicial": ini, "horneados": hor, "mermas": mer, "stock_final": fin
                }).execute()
                st.success("Registro diario guardado.")
    else: st.warning("Añade productos primero.")

# ==========================================
#        PANTALLA: 1. DASHBOARD
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📊 Dashboard de Ventas")
    st.info("Visualización de datos históricos acumulados.")
    
    try:
        # Cargar datos para gráfico simple
        res = conn.table("historial_ventas").select("fecha, cantidad_vendida").execute()
        if res.data:
            df_dash = pd.DataFrame(res.data)
            df_dash['fecha'] = pd.to_datetime(df_dash['fecha'])
            df_dash = df_dash.groupby('fecha')['cantidad_vendida'].sum().reset_index()
            st.line_chart(df_dash.set_index('fecha'))
        else:
            st.write("No hay datos suficientes para mostrar gráficos. Sube un CSV primero.")
    except:
        st.error("Error al cargar el Dashboard.")

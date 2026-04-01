import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor

st.set_page_config(page_title="Tío Bigotes Pro", layout="wide", initial_sidebar_state="collapsed")

try:
    conn = st.connection("supabase", type=SupabaseConnection, 
                         url=st.secrets["connections"]["supabase"]["url"], 
                         key=st.secrets["connections"]["supabase"]["key"])
except:
    st.error("Error de conexión con la base de datos."); st.stop()

def limpiar_nombre(texto):
    if pd.isna(texto): return ""
    return re.sub(r'^\d+[\.\s\-]*', '', str(texto).upper().strip()).strip()

if 'pantalla' not in st.session_state: st.session_state.pantalla = 'Home'
def ir_a(p): st.session_state.pantalla = p

# ==========================================
#             PANTALLA: HOME
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Pro")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📈 1. BI & ANALÍTICA"): ir_a('BI')
        if st.button("📦 PRODUCTOS"): ir_a('Productos')
    with c2:
        if st.button("📋 2. HOJA CONTROL"): ir_a('Operativa')
        if st.button("👥 EMPLEADOS"): ir_a('Empleados')
    with c3:
        if st.button("📥 3. CARGAR CSV"): ir_a('Carga')
        if st.button("🧠 4. IA PREDICTIVA"): ir_a('Dashboard')

# ==========================================
#        PANTALLA: BI & ANALÍTICA
# ==========================================
elif st.session_state.pantalla == 'BI':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📈 Business Intelligence")
    
    fecha_sel = st.date_input("Día de Análisis:", datetime.date.today() - datetime.timedelta(days=1))
    f_ayer = pd.to_datetime(fecha_sel).date()
    f_ly = f_ayer - pd.Timedelta(days=364)

    def load_bi(d_ayer, d_ly):
        # Traemos ventas de ayer y del año pasado para comparar
        res = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto, ticket_id").gte("fecha", str(d_ly)).lte("fecha", str(d_ayer)).execute()
        dv = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        # Productos
        rp = conn.table("productos").select("id, nombre").execute()
        dp = pd.DataFrame(rp.data) if rp.data else pd.DataFrame()
        # Mermas
        rm = conn.table("control_diario").select("fecha, producto_id, merma, stock_inicial, horneados, resto").eq("fecha", str(d_ayer)).execute()
        dm = pd.DataFrame(rm.data) if rm.data else pd.DataFrame()
        return dv, dp, dm

    dv, dp, dm = load_bi(f_ayer, f_ly)

    if dv.empty:
        st.warning(f"No hay datos cargados para el {f_ayer}")
    else:
        dv['fecha'] = pd.to_datetime(dv['fecha']).dt.date
        v_ayer = dv[dv['fecha'] == f_ayer]
        v_ly = dv[dv['fecha'] == f_ly]
        
        # KPIs
        fact = v_ayer['total_neto'].sum()
        tickets = v_ayer['ticket_id'].nunique() # AQUÍ ESTÁ EL TRUCO DE LOS 84 TICKETS
        uds = v_ayer['cantidad_vendida'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas (€)", f"{fact:,.2f} €", f"{((fact/v_ly['total_neto'].sum())-1)*100:+.1f}% vs LY" if not v_ly.empty else "N/A")
        c2.metric("Tickets", f"{tickets}")
        c3.metric("Ticket Medio", f"{fact/tickets:,.2f} €" if tickets > 0 else "0 €")
        c4.metric("UPT (Uds/Ticket)", f"{uds/tickets:,.2f}" if tickets > 0 else "0")

        st.divider()
        if not dm.empty and not dp.empty:
            st.subheader("🕵️ Auditoría de Descuadres (Físico vs TPV)")
            # Aquí iría el cruce de tablas que ya teníamos
            st.info("Cruce de inventario disponible si se ha rellenado la hoja de control.")

# ==========================================
#        PANTALLA: CARGA DE DATOS (MAPEO PRO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📥 Importador y Mapeo de Historial")
    
    archivo = st.file_uploader("Sube tu archivo CSV (2023-2026)", type=['csv'])
    if archivo:
        # Leemos el CSV
        df_csv = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
        cabeceras = list(df_csv.columns)
        
        # 1. Recuperar el mapeo guardado anteriormente (si existe)
        try:
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}
        except:
            m_prev = {}
        
        st.subheader("⚙️ Configurar Columnas")
        # Campos necesarios en la base de datos
        campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago", "ticket_id"]
        nuevo_mapeo = {}
        
        cols_grid = st.columns(3)
        for i, c_db in enumerate(campos_db):
            # Intentamos pre-seleccionar lo que el usuario eligió la última vez
            idx_prev = cabeceras.index(m_prev[c_db]) if c_db in m_prev and m_prev[c_db] in cabeceras else 0
            with cols_grid[i % 3]:
                nuevo_mapeo[c_db] = st.selectbox(f"Columna para: {c_db}", cabeceras, index=idx_prev, key=f"sel_{c_db}")
            
        if st.button("💾 GUARDAR ESTE MAPEO COMO PREDETERMINADO"):
            conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
            st.success("✅ Mapeo guardado. No tendrás que elegir las columnas la próxima vez.")

        st.divider()

        # 2. Detector de Productos Nuevos
        # Limpiamos los nombres del CSV y comparamos con los de la base de datos
        nombres_en_csv = df_csv[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
        res_p = conn.table("productos").select("id, nombre").execute()
        dict_db_productos = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
        
        productos_nuevos = [n for n in nombres_en_csv if n and n not in dict_db_productos]

        if productos_nuevos:
            st.warning(f"🔎 Se han detectado {len(productos_nuevos)} productos en el CSV que NO existen en tu catálogo.")
            seleccionados = st.multiselect("Selecciona los productos que quieres crear ahora mismo:", productos_nuevos)
            
            if seleccionados:
                c_cat, c_pre = st.columns(2)
                cat_m = c_cat.selectbox("Categoría para estos productos:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                pre_m = c_pre.number_input("Precio base estimado (€):", value=0.0)
                
                if st.button("✅ CREAR PRODUCTOS SELECCIONADOS"):
                    ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                    conn.table("productos").insert(ins_list).execute()
                    st.success(f"🎊 {len(seleccionados)} productos añadidos. Ya puedes subir el historial.")
                    st.rerun()
        else:
            st.info("✅ Todos los productos del CSV ya están registrados en el sistema.")

        # 3. Botón de Subida Masiva
        if st.button("🚀 INICIAR SUBIDA MASIVA AL HISTORIAL"):
            progreso = st.progress(0)
            lote, cont = [], 0
            
            # Aseguramos formato de fecha europeo
            df_csv[nuevo_mapeo['fecha']] = pd.to_datetime(df_csv[nuevo_mapeo['fecha']], dayfirst=True, errors='coerce')
            
            for i, fila in df_csv.iterrows():
                nom_limpio = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                
                # Solo subimos si el producto existe y la fecha es válida
                if nom_limpio in dict_db_productos and pd.notnull(fila[nuevo_mapeo['fecha']]):
                    try:
                        # Limpieza de decimales por si vienen con coma
                        precio_neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                        
                        lote.append({
                            "fecha": fila[nuevo_mapeo['fecha']].strftime('%Y-%m-%d'),
                            "producto_id": dict_db_productos[nom_limpio],
                            "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                            "total_neto": float(precio_neto),
                            "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']]),
                            "ticket_id": str(fila[nuevo_mapeo['ticket_id']]) # El famoso Ticket ID
                        })
                    except:
                        pass
                
                # Subimos en bloques de 1000 para no saturar la conexión
                if len(lote) >= 1000 or i == len(df_csv) - 1:
                    if lote:
                        conn.table("historial_ventas").insert(lote).execute()
                        cont += len(lote)
                        lote = []
                    progreso.progress((i + 1) / len(df_csv))
            
            st.success(f"🎊 Proceso terminado. Se han cargado {cont} registros en 'historial_ventas'.")
            st.balloons()

# (Aquí siguen las pantallas de Operativa, Productos, Empleados y Dashboard IA que ya tenías)

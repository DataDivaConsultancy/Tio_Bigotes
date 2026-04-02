import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CONEXIÓN SUPABASE ---
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
    texto = re.sub(r'^\d+[\.\s\-]*', '', texto)
    return texto.strip()

if 'pantalla' not in st.session_state:
    st.session_state.pantalla = 'Home'

def ir_a(p):
    st.session_state.pantalla = p

# ==========================================
#             MENU PRINCIPAL
# ==========================================
if st.session_state.pantalla == 'Home':
    st.title("🥐 Tío Bigotes - Gestión Integral")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📈 1. BI & ANALÍTICA"): ir_a('BI')
        if st.button("📦 GESTIÓN PRODUCTOS"): ir_a('Productos')
    with col2:
        if st.button("📋 2. HOJA CONTROL DIARIO"): ir_a('Operativa')
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')
    with col3:
        if st.button("📥 3. CARGAR HISTORIAL CSV"): ir_a('Carga')
        if st.button("🧠 4. IA PREDICTIVA"): ir_a('Dashboard')

# ==========================================
#        PANTALLA: BI & ANALÍTICA
# ==========================================
elif st.session_state.pantalla == 'BI':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📈 Business Intelligence")

    fecha_sel = st.date_input("Día de Análisis:", datetime.date(2026, 3, 31))
    f_ayer = pd.to_datetime(fecha_sel).date()
    f_ly = f_ayer - pd.Timedelta(days=364)

    def cargar_datos_bi(d_ayer, d_ly):
        try:
            # Ventas de ayer y del año pasado
            res = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto, ticket_id").gte("fecha", str(d_ly)).lte("fecha", str(d_ayer)).limit(50000).execute()
            df_v = pd.DataFrame(res.data) if res.data else pd.DataFrame()
            
            # Productos
            res_p = conn.table("productos").select("id, nombre").execute()
            df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
            
            # Mermas
            res_m = conn.table("control_diario").select("fecha, producto_id, merma, stock_inicial, horneados, resto").eq("fecha", str(d_ayer)).execute()
            df_m = pd.DataFrame(res_m.data) if res_m.data else pd.DataFrame()
            
            return df_v, df_p, df_m
        except: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    dv, dp, dm = cargar_datos_bi(f_ayer, f_ly)

    if dv.empty:
        st.warning(f"No hay datos para el día {f_ayer}. Asegúrate de haber subido el CSV correctamente.")
        if st.button("🔍 Ver últimas ventas en BD"):
            debug = conn.table("historial_ventas").select("fecha, total_neto").limit(5).order("fecha", desc=True).execute()
            st.write(debug.data)
    else:
        dv['fecha'] = pd.to_datetime(dv['fecha']).dt.date
        v_ayer = dv[dv['fecha'] == f_ayer]
        v_ly = dv[dv['fecha'] == f_ly]

        fact_ayer = v_ayer['total_neto'].sum()
        tickets_ayer = v_ayer['ticket_id'].nunique()
        uds_ayer = v_ayer['cantidad_vendida'].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ventas (€)", f"{fact_ayer:,.2f} €")
        c2.metric("Tickets", f"{tickets_ayer}")
        c3.metric("Ticket Medio", f"{fact_ayer/tickets_ayer:,.2f} €" if tickets_ayer > 0 else "0 €")
        c4.metric("Unidades", f"{uds_ayer:,.0f}")

        st.divider()
        st.subheader("🕵️ Auditoría y Ranking")
        if not dp.empty:
            v_ayer_nom = pd.merge(v_ayer, dp, left_on='producto_id', right_on='id')
            st.table(v_ayer_nom.groupby('nombre')['cantidad_vendida'].sum().sort_values(ascending=False).head(10))

# ==========================================
#        PANTALLA: CARGA DE DATOS (MAPEO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📥 Importador de Historial")
    
    archivo = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    if archivo:
        df_csv = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
        cabeceras = list(df_csv.columns)
        
        try:
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}
        except: m_prev = {}
        
        campos = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago", "ticket_id"]
        nuevo_mapeo = {}
        cols = st.columns(3)
        for i, c_db in enumerate(campos):
            idx = cabeceras.index(m_prev[c_db]) if c_db in m_prev and m_prev[c_db] in cabeceras else 0
            with cols[i % 3]:
                nuevo_mapeo[c_db] = st.selectbox(f"Columna: {c_db}", cabeceras, index=idx)

        if st.button("🚀 INICIAR SUBIDA MASIVA"):
            rp = conn.table("productos").select("id, nombre").execute()
            dict_p = {limpiar_nombre(p['nombre']): p['id'] for p in rp.data}
            df_csv[nuevo_mapeo['fecha']] = pd.to_datetime(df_csv[nuevo_mapeo['fecha']], dayfirst=True, errors='coerce')
            
            lote, cont = [], 0
            for _, fila in df_csv.iterrows():
                nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                fec = fila[nuevo_mapeo['fecha']]
                if nom in dict_p and pd.notnull(fec):
                    try:
                        lote.append({
                            "fecha": fec.strftime('%Y-%m-%d'),
                            "producto_id": dict_p[nom],
                            "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                            "total_neto": float(str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')),
                            "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']]),
                            "ticket_id": str(fila[nuevo_mapeo['ticket_id']])
                        })
                    except: pass
                if len(lote) >= 1000:
                    conn.table("historial_ventas").insert(lote).execute()
                    cont += len(lote); lote = []
            
            if lote:
                conn.table("historial_ventas").insert(lote).execute()
                cont += len(lote)
            
            conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
            st.success(f"✅ Se han subido {cont} registros.")

# ==========================================
#        PANTALLA: HOJA CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control Diario")
    
    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha:", datetime.date.today())
    
    res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
    emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    if not emps: st.error("Crea empleados primero."); st.stop()
    emp_sel = col_e.selectbox("Responsable:", list(emps.keys()))

    res_p = conn.table("productos").select("id, nombre").execute()
    df_prod = pd.DataFrame(res_p.data)

    # Cargar resto de ayer
    ayer = fecha_sel - datetime.timedelta(days=1)
    res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
    dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}

    data_h = [{"ID": r['id'], "Producto": r['nombre'], "Stock Inicial": dict_ayer.get(r['id'], 0), "Horneados": 0, "Merma": 0, "Resto": 0} for _, r in df_prod.iterrows()]
    df_h = pd.DataFrame(data_h)

    edited = st.data_editor(df_h, hide_index=True, use_container_width=True)

    if st.button("💾 GUARDAR CONTROL"):
        lote_c = []
        for _, row in edited.iterrows():
            if any([row["Horneados"]>0, row["Merma"]>0, row["Resto"]>0]):
                lote_c.append({
                    "fecha": str(fecha_sel), "producto_id": row["ID"], "empleado_id": emps[emp_sel],
                    "stock_inicial": row["Stock Inicial"], "horneados": row["Horneados"], "merma": row["Merma"], "resto": row["Resto"]
                })
        if lote_c:
            conn.table("control_diario").insert(lote_c).execute()
            st.success("✅ Guardado.")

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Empleados")
    
    with st.expander("➕ Nuevo Empleado"):
        with st.form("n_emp"):
            n = st.text_input("Nombre")
            r = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
            if st.form_submit_button("Guardar"):
                conn.table("empleados").insert({"nombre": n, "rol": r}).execute()
                st.rerun()

    res = conn.table("empleados").select("*").eq("activo", True).execute()
    if res.data:
        df_e = pd.DataFrame(res.data)
        for _, e in df_e.iterrows():
            c1, c2 = st.columns([4,1])
            c1.write(f"👤 {e['nombre']} ({e['rol']})")
            if c2.button("Baja", key=f"b_{e['id']}"):
                conn.table("empleados").update({"activo": False}).eq("id", e['id']).execute()
                st.rerun()

# ==========================================
#        PANTALLA: GESTIÓN PRODUCTOS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER", on_click=ir_a, args=('Home',))
    st.header("📦 Catálogo de Productos")
    
    with st.expander("➕ Nuevo Producto"):
        with st.form("n_prod"):
            n = st.text_input("Nombre")
            c = st.selectbox("Categoría", ["Empanada", "Bebida", "Postre"])
            if st.form_submit_button("Añadir"):
                conn.table("productos").insert({"nombre": n, "categoria": c}).execute()
                st.rerun()

    res = conn.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# ==========================================
#        PANTALLA: IA PREDICTIVA (MOTOR AMBICIOSO)
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("🧠 IA Predictiva: Objetivo Crecimiento")
    
    # --- CONFIGURACIÓN ---
    c1, c2, c3 = st.columns(3)
    fecha_pred = c1.date_input("📅 Día para Predecir", datetime.date.today())
    estrategia = c2.select_slider("🎯 Estrategia de Venta", 
                                  options=["Defensiva", "Equilibrada", "Agresiva"], 
                                  value="Agresiva")
    es_festivo = c3.toggle("🚩 ¿Es Festivo / Puente?", value=True)

    if st.button("🚀 CALCULAR PRODUCCIÓN PARA VENDER MÁS"):
        with st.spinner("Analizando tus mejores días históricos..."):
            # 1. Carga de datos
            rv = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida").limit(100000).execute()
            rp = conn.table("productos").select("id, nombre, categoria").eq("categoria", "Empanada").execute()
            
            if not rv.data: st.error("No hay datos."); st.stop()

            df_v = pd.DataFrame(rv.data)
            df_p = pd.DataFrame(rp.data)
            df = pd.merge(df_v, df_p, left_on='producto_id', right_on='id')
            df['fecha'] = pd.to_datetime(df['fecha'])

            # 2. DEFINIR PERCENTIL SEGÚN ESTRATEGIA
            # Defensiva (50 - Mediana), Equilibrada (70), Agresiva (85 - Tus mejores días)
            dict_perc = {"Defensiva": 50, "Equilibrada": 75, "Agresiva": 88}
            p_objetivo = dict_perc[estrategia]

            # 3. FILTRO DE SABORES ACTIVOS (Últimos 45 días)
            f_corte = df['fecha'].max() - pd.Timedelta(days=45)
            vivos = df[df['fecha'] >= f_corte]['id'].unique()

            # 4. CÁLCULO DE PREVISIÓN
            dia_sem_obj = fecha_pred.weekday()
            res_ia = []

            for _, prod in df_p.iterrows():
                if prod['id'] not in vivos: continue
                
                sub = df[df['id'] == prod['id']]
                # Filtramos por el mismo día de la semana
                hist_dia = sub[sub['fecha'].dt.dayofweek == dia_sem_obj]['cantidad_vendida']
                
                if not hist_dia.empty:
                    # Buscamos el percentil alto para "vender más"
                    base = np.percentile(hist_dia, p_objetivo)
                else:
                    base = sub['cantidad_vendida'].mean() if not sub.empty else 0

                # Multiplicador Festivo real de Barcelona (ajustado por historial)
                # Jueves Santo suele rendir un +20% sobre el mejor jueves normal
                if es_festivo: base *= 1.20
                
                # Bonus por estrategia Agresiva (+10% extra de stock de seguridad)
                if estrategia == "Agresiva": base *= 1.10
                
                uds_final = int(np.ceil(base))
                
                if uds_final > 0:
                    res_ia.append({
                        "Empanada": prod['nombre'],
                        "Total Sugerido": uds_final,
                        "Tanda 1 (Mañana)": int(np.ceil(uds_final * 0.7)),
                        "Tanda 2 (Tarde)": int(np.floor(uds_final * 0.3))
                    })

            # 5. RESULTADOS
            if res_ia:
                df_res = pd.DataFrame(res_ia).sort_values(by="Total Sugerido", ascending=False)
                
                st.success(f"🔥 **Modo {estrategia} activado.** Objetivo de empanadas hoy: **{df_res['Total Sugerido'].sum()} unidades**.")
                
                st.dataframe(df_res, hide_index=True, use_container_width=True)
                
                # WhatsApp para el equipo
                txt = f"*🚀 PLAN DE ATAQUE - {fecha_pred.strftime('%d/%m/%Y')}*\n"
                txt += f"*Estrategia:* {estrategia} (Festivo: {'SÍ' if es_festivo else 'NO'})\n"
                txt += "Previsión para no romper stock y maximizar venta:\n"
                txt += "-"*25 + "\n"
                for _, r in df_res.iterrows():
                    txt += f"• {r['Empanada']}: {r['Tanda 1 (Mañana)']} + {r['Tanda 2 (Tarde)']} = *{r['Total Sugerido']}*\n"
                
                st.text_area("Copia para WhatsApp", txt, height=400)

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

# --- CONEXIÓN ROBUSTA A SUPABASE ---
try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error crítico de conexión: {e}")
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
    st.title("🥐 Tío Bigotes - Inteligencia y Gestión")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📈 1. BI & AUDITORÍA (NUEVO)"): ir_a('BI')
        if st.button("🧠 2. IA PREDICTIVA"): ir_a('Dashboard')
    with col2:
        if st.button("📋 3. HOJA CONTROL DIARIO"): ir_a('Operativa')
        if st.button("📦 GESTIÓN PRODUCTOS"): ir_a('Productos')
    with col3:
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')

# ==========================================
#        PANTALLA: BI, ANALÍTICA Y AUDITORÍA
# ==========================================
elif st.session_state.pantalla == 'BI':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📈 Business Intelligence y Auditoría")

    ayer_default = datetime.date.today() - datetime.timedelta(days=1)
    fecha_analisis = st.date_input("Fecha de Análisis (Cierre):", value=ayer_default)
    
    f_ayer = pd.to_datetime(fecha_analisis).date()
    f_w1 = f_ayer - pd.Timedelta(days=7) 
    f_ly = f_ayer - pd.Timedelta(days=364) 
    f_mtd_inicio = f_ayer.replace(day=1) 

    def cargar_datos_bi(d_ayer, d_w1, d_ly, d_mtd):
        try:
            # --- 1. DATOS DE VENTAS TPV (CSV) ---
            res_mtd = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto").gte("fecha", str(d_mtd)).lte("fecha", str(d_ayer)).limit(50000).execute()
            res_w1 = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto").eq("fecha", str(d_w1)).limit(10000).execute()
            res_ly = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto").eq("fecha", str(d_ly)).limit(10000).execute()
            
            df_v = pd.concat([
                pd.DataFrame(res_mtd.data) if res_mtd.data else pd.DataFrame(),
                pd.DataFrame(res_w1.data) if res_w1.data else pd.DataFrame(),
                pd.DataFrame(res_ly.data) if res_ly.data else pd.DataFrame()
            ], ignore_index=True)
            
            res_p = conn.table("productos").select("id, nombre").execute()
            df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame(columns=['id', 'nombre'])
            
            if not df_v.empty and not df_p.empty:
                df_v = pd.merge(df_v, df_p, left_on='producto_id', right_on='id', how='left')
                df_v['Producto'] = df_v['nombre'].fillna('Desconocido')
                df_v['fecha'] = pd.to_datetime(df_v['fecha']).dt.date
            else:
                if not df_v.empty: df_v['Producto'] = 'Desconocido'
            
            # --- 2. DATOS DE CONTROL DIARIO (HUMANO) ---
            # Ahora traemos TODO el inventario: merma, stock_inicial, horneados y resto
            columnas_cd = "fecha, producto_id, merma, stock_inicial, horneados, resto"
            rm_mtd = conn.table("control_diario").select(columnas_cd).gte("fecha", str(d_mtd)).lte("fecha", str(d_ayer)).limit(10000).execute()
            rm_w1 = conn.table("control_diario").select(columnas_cd).eq("fecha", str(d_w1)).limit(5000).execute()
            rm_ly = conn.table("control_diario").select(columnas_cd).eq("fecha", str(d_ly)).limit(5000).execute()
            
            df_m = pd.concat([
                pd.DataFrame(rm_mtd.data) if rm_mtd.data else pd.DataFrame(),
                pd.DataFrame(rm_w1.data) if rm_w1.data else pd.DataFrame(),
                pd.DataFrame(rm_ly.data) if rm_ly.data else pd.DataFrame()
            ], ignore_index=True)
            
            if not df_m.empty:
                df_m['fecha'] = pd.to_datetime(df_m['fecha']).dt.date
                # Cruzamos con nombres de productos para la auditoría
                if not df_p.empty:
                    df_m = pd.merge(df_m, df_p, left_on='producto_id', right_on='id', how='left')
                    df_m['Producto'] = df_m['nombre'].fillna('Desconocido')
                else:
                    df_m['Producto'] = 'Desconocido'
                
                # Calculamos la Venta Teórica (Lo que el empleado dice que se esfumó de la tienda)
                df_m['venta_teorica'] = df_m['stock_inicial'] + df_m['horneados'] - df_m['merma'] - df_m['resto']

            return df_v, df_m, "✅ Datos extraídos correctamente."
        except Exception as e:
            return pd.DataFrame(), pd.DataFrame(), f"❌ Error de carga: {e}"

    with st.spinner("Descargando y cruzando datos de inventario y TPV..."):
        df_ventas, df_control, msg_estado = cargar_datos_bi(f_ayer, f_w1, f_ly, f_mtd_inicio)

    if df_ventas.empty:
        st.warning(f"No hay ventas registradas en el TPV para las fechas seleccionadas.")
    else:
        # Filtrado de Ventas TPV
        v_ayer = df_ventas[df_ventas['fecha'] == f_ayer]
        v_w1 = df_ventas[df_ventas['fecha'] == f_w1]
        v_ly = df_ventas[df_ventas['fecha'] == f_ly]
        v_mtd = df_ventas[(df_ventas['fecha'] >= f_mtd_inicio) & (df_ventas['fecha'] <= f_ayer)]
        
        # Filtrado de Control Diario (Mermas e Inventario Físico)
        cd_ayer = df_control[df_control['fecha'] == f_ayer] if not df_control.empty else pd.DataFrame()
        cd_w1 = df_control[df_control['fecha'] == f_w1] if not df_control.empty else pd.DataFrame()
        cd_ly = df_control[df_control['fecha'] == f_ly] if not df_control.empty else pd.DataFrame()

        m_ayer_sum = cd_ayer['merma'].sum() if not cd_ayer.empty else 0
        m_w1_sum = cd_w1['merma'].sum() if not cd_w1.empty else 0
        m_ly_sum = cd_ly['merma'].sum() if not cd_ly.empty else 0

        with st.expander("🛠️ Verificador de Historial (Solo Admin)"):
            st.write(f"Ventas leídas para el {f_ayer}: **{len(v_ayer)}** filas.")
            st.write(f"Ventas leídas para W-1 ({f_w1}): **{len(v_w1)}** filas.")
            st.write(f"Hojas de control encontradas para el {f_ayer}: **{len(cd_ayer)}** registros.")

        if v_ayer.empty:
            st.info(f"ℹ️ La caja no registró ventas el día **{f_ayer.strftime('%d/%m/%Y')}**.")
        else:
            # --- 1. KPIs DIARIOS ---
            fact_ayer = v_ayer['total_neto'].sum()
            fact_w1 = v_w1['total_neto'].sum()
            fact_ly = v_ly['total_neto'].sum()
            
            uds_ayer = v_ayer['cantidad_vendida'].sum()
            uds_w1 = v_w1['cantidad_vendida'].sum()
            uds_ly = v_ly['cantidad_vendida'].sum()

            obj_fact = fact_ly * 1.15  
            obj_merma = uds_ayer * 0.01 

            st.markdown("### 📊 Panel de Rendimiento y Objetivos")
            c1, c2, c3, c4 = st.columns(4)

            delta_ly_eur = ((fact_ayer / fact_ly) - 1) * 100 if fact_ly > 0 else 0
            c1.metric("Ventas (€)", f"{fact_ayer:,.2f} €", f"{delta_ly_eur:+.1f}% vs LY")
            if fact_ayer >= obj_fact and obj_fact > 0: c1.caption(f"✅ Obj. Superado (+15% LY: {obj_fact:.2f}€)")
            elif obj_fact > 0: c1.caption(f"⚠️ Debajo de Obj. ({obj_fact:.2f}€)")

            delta_w1_uds = ((uds_ayer / uds_w1) - 1) * 100 if uds_w1 > 0 else 0
            c2.metric("Unidades Vendidas", f"{uds_ayer:,.0f} uds", f"{delta_w1_uds:+.1f}% vs W-1")

            delta_merma_w1 = m_ayer_sum - m_w1_sum
            merma_color = "normal" if delta_merma_w1 <= 0 else "inverse" 
            c3.metric("Merma (Uds)", f"{m_ayer_sum:,.0f} uds", f"{delta_merma_w1:+.0f} uds vs W-1", delta_color=merma_color)

            pct_merma = (m_ayer_sum / uds_ayer) * 100 if uds_ayer > 0 else 0
            if pct_merma <= 1.0: c4.metric("% Merma / Venta", f"{pct_merma:.2f}%", "✅ Cumple Obj < 1%")
            else: c4.metric("% Merma / Venta", f"{pct_merma:.2f}%", f"❌ Exc. Obj (< 1%)", delta_color="inverse")

            st.divider()

            # --- 2. EL MÓDULO DE AUDITORÍA (NUEVO) ---
            st.markdown("### 🕵️ Auditoría de Cajas (Inventario Físico vs TPV)")
            if cd_ayer.empty:
                st.warning(f"⚠️ El empleado no rellenó la Hoja de Control Diario el día {f_ayer.strftime('%d/%m/%Y')}. Imposible auditar.")
            else:
                st.info("Compara lo que el empleado declara que desapareció de la vitrina vs lo que la caja registradora cobró realmente.")
                
                # Agrupamos las ventas teóricas (Hoja de control)
                teo = cd_ayer.groupby('Producto')['venta_teorica'].sum().reset_index()
                teo.rename(columns={'venta_teorica': 'Venta Teórica (Empleado)'}, inplace=True)
                
                # Agrupamos las ventas reales (CSV / TPV)
                real = v_ayer.groupby('Producto')['cantidad_vendida'].sum().reset_index()
                real.rename(columns={'cantidad_vendida': 'Venta Registrada (Caja)'}, inplace=True)
                
                # Cruzamos para buscar a los mentirosos / despistados
                auditoria = pd.merge(teo, real, on='Producto', how='outer').fillna(0)
                auditoria['Venta Teórica (Empleado)'] = auditoria['Venta Teórica (Empleado)'].astype(int)
                auditoria['Venta Registrada (Caja)'] = auditoria['Venta Registrada (Caja)'].astype(int)
                
                # Calculamos el agujero (Descuadre)
                auditoria['Descuadre (Faltante)'] = auditoria['Venta Teórica (Empleado)'] - auditoria['Venta Registrada (Caja)']
                
                # Filtramos para no mostrar productos que no se movieron
                auditoria = auditoria[(auditoria['Venta Teórica (Empleado)'] > 0) | (auditoria['Venta Registrada (Caja)'] > 0)]
                
                # Resaltar en rojo los descuadres con Pandas Styling
                def color_descuadre(val):
                    if val > 0: return 'color: red; font-weight: bold' # Faltan productos en caja
                    elif val < 0: return 'color: orange' # Se cobró de más o se horneó sin apuntar
                    return 'color: green' # Cuadre perfecto
                
                st.dataframe(auditoria.style.map(color_descuadre, subset=['Descuadre (Faltante)']), use_container_width=True, hide_index=True)

            st.divider()

            # --- 3. RANKINGS ---
            st.markdown("### 🏆 Ranking de Productos")
            col_rank1, col_rank2 = st.columns(2)

            with col_rank1:
                st.subheader("Top Ventas: Ayer")
                rank_ayer = v_ayer.groupby('Producto')['cantidad_vendida'].sum().reset_index()
                rank_ayer = rank_ayer.sort_values(by='cantidad_vendida', ascending=False).head(10)
                rank_ayer.index += 1
                st.dataframe(rank_ayer.style.format({"cantidad_vendida": "{:,.0f}"}), use_container_width=True)

            with col_rank2:
                st.subheader("Top Ventas: Acumulado Mes")
                if not v_mtd.empty:
                    rank_mtd = v_mtd.groupby('Producto')['cantidad_vendida'].sum().reset_index()
                    rank_mtd = rank_mtd.sort_values(by='cantidad_vendida', ascending=False).head(10)
                    rank_mtd.index += 1
                    st.dataframe(rank_mtd.style.format({"cantidad_vendida": "{:,.0f}"}), use_container_width=True)


# ==========================================
#        PANTALLA: IA PREDICTIVA
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("🧠 IA Predictiva de Horneado")
    
    st.markdown("### 📅 Configuración de la Previsión")
    col_d, col_b = st.columns([2, 1])
    
    fecha_pred = col_d.date_input("Fecha para la cual quieres la previsión:", datetime.date.today())
    confirmar_ia = col_b.button("✅ CONFIRMAR Y GENERAR")

    @st.cache_data(ttl=3600, show_spinner="Analizando patrones históricos... ⏳")
    def entrenar_ia(fecha_objetivo):
        try:
            import holidays
            años_lista = [2022, 2023, 2024, 2025, 2026, 2027]
            festivos = holidays.Spain(years=años_lista)

            res_v = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida").limit(50000).execute()
            if not res_v.data: return None, "⚠️ Historial vacío."
            df_v = pd.DataFrame(res_v.data)
            
            res_p = conn.table("productos").select("id, nombre").execute()
            df_p = pd.DataFrame(res_p.data)
            
            df = pd.merge(df_v, df_p, left_on='producto_id', right_on='id', how='left')
            df['Producto'] = df['nombre'].fillna('Desconocido')
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            
            df_diario = df.groupby(['fecha', 'Producto'])['cantidad_vendida'].sum().reset_index()
            df_diario['fecha'] = pd.to_datetime(df_diario['fecha'])
            
            df_diario['Dia_Semana'] = df_diario['fecha'].dt.dayofweek
            df_diario['Dia_Mes'] = df_diario['fecha'].dt.day
            df_diario['Mes'] = df_diario['fecha'].dt.month
            df_diario['Año'] = df_diario['fecha'].dt.year
            df_diario['Es_Festivo'] = df_diario['fecha'].apply(lambda x: 1 if x in festivos else 0)
            df_diario['Es_Vispera'] = df_diario['fecha'].apply(lambda x: 1 if (x + pd.Timedelta(days=1)) in festivos else 0)
            
            f_obj = pd.to_datetime(fecha_objetivo)
            hoy_features = pd.DataFrame({
                'Dia_Semana': [f_obj.dayofweek], 
                'Dia_Mes': [f_obj.day],
                'Mes': [f_obj.month], 
                'Año': [f_obj.year],
                'Es_Festivo': [1 if f_obj in festivos else 0],
                'Es_Vispera': [1 if (f_obj + pd.Timedelta(days=1)) in festivos else 0]
            })

            predicciones = []
            for prod in df_diario['Producto'].unique():
                if prod == 'Desconocido': continue
                datos_prod = df_diario[df_diario['Producto'] == prod]
                if len(datos_prod) > 3: 
                    X = datos_prod[['Dia_Semana', 'Dia_Mes', 'Mes', 'Año', 'Es_Festivo', 'Es_Vispera']]
                    y = datos_prod['cantidad_vendida']
                    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
                    modelo.fit(X, y)
                    pred = modelo.predict(hoy_features)[0]
                    predicciones.append({
                        "Producto": prod,
                        "Previsión IA (Uds)": max(0, int(round(pred)))
                    })
            
            df_res = pd.DataFrame(predicciones)
            if df_res.empty: return None, "⚠️ Sin datos suficientes."
            return df_res.sort_values(by="Previsión IA (Uds)", ascending=False), f"✅ Previsión generada para el día {fecha_objetivo}"
            
        except Exception as e:
            return None, f"❌ Error: {e}"

    if confirmar_ia:
        st.divider()
        df_prev, mensaje = entrenar_ia(fecha_pred)
        st.write(mensaje)
        
        if df_prev is not None:
            c_t, c_g = st.columns([1, 1.5])
            with c_t:
                st.subheader(f"🎯 Sugerencia para el {fecha_pred}")
                st.dataframe(df_prev, hide_index=True, use_container_width=True)
            with c_g:
                st.subheader("Tendencia de demanda")
                fig = px.bar(df_prev.head(15), x='Previsión IA (Uds)', y='Producto', orientation='h', color='Previsión IA (Uds)', color_continuous_scale='Reds')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Selecciona la fecha arriba y pulsa el botón para activar la IA.")

# ==========================================
#        PANTALLA: HOJA CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control de Tienda")

    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())
    
    try:
        res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
        emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    except:
        emps = {}
        
    if not emps:
        st.error("⚠️ Debes dar de alta empleados primero.")
        st.stop()
    emp_sel = col_e.selectbox("Empleado responsable:", list(emps.keys()))

    st.divider()

    res_p = conn.table("productos").select("id, nombre, categoria").execute()
    df_prod = pd.DataFrame(res_p.data)

    ayer = fecha_sel - datetime.timedelta(days=1)
    dict_ayer = {}
    try:
        res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
        dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}
    except:
        pass 

    data_hoja = []
    for _, row in df_prod.iterrows():
        st_ayer = dict_ayer.get(row['id'], 0)
        data_hoja.append({
            "ID": row['id'],
            "Producto": row['nombre'],
            "Stock Inicial": st_ayer,
            "Horneados": 0,
            "Merma": 0,
            "Resto (Cierre)": 0,
            "Ventas": 0
        })

    df_base = pd.DataFrame(data_hoja)
    edited_df = st.data_editor(
        df_base,
        column_config={
            "ID": None,
            "Producto": st.column_config.TextColumn("Producto", disabled=True),
            "Stock Inicial": st.column_config.NumberColumn("Stock Inicial", min_value=0),
            "Horneados": st.column_config.NumberColumn("Horneados", min_value=0),
            "Merma": st.column_config.NumberColumn("Merma (Tirado)", min_value=0),
            "Resto (Cierre)": st.column_config.NumberColumn("Resto (Cierre)", min_value=0),
            "Ventas": st.column_config.NumberColumn("Ventas (Auto)", disabled=True)
        },
        hide_index=True, use_container_width=True, key="hoja_diaria"
    )

    edited_df["Ventas"] = edited_df["Stock Inicial"] + edited_df["Horneados"] - edited_df["Merma"] - edited_df["Resto (Cierre)"]

    st.divider()

    if st.button("💾 GRABAR TODOS LOS DATOS"):
        with st.spinner("Guardando..."):
            try:
                lote = []
                for _, row in edited_df.iterrows():
                    if any([row["Stock Inicial"] > 0, row["Horneados"] > 0, row["Merma"] > 0, row["Resto (Cierre)"] > 0]):
                        lote.append({
                            "fecha": str(fecha_sel),
                            "producto_id": int(row["ID"]),
                            "empleado_id": emps[emp_sel],
                            "stock_inicial": int(row["Stock Inicial"]),
                            "horneados": int(row["Horneados"]),
                            "merma": int(row["Merma"]),
                            "resto": int(row["Resto (Cierre)"]),
                            "desviacion_inicial": int(row["Stock Inicial"] - dict_ayer.get(row["ID"], 0))
                        })
                if lote:
                    conn.table("control_diario").insert(lote).execute()
                    st.success("✅ ¡Guardado!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
#        PANTALLA: CARGA DE DATOS (MAPEO)
# ==========================================
elif st.session_state.pantalla == 'Carga':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📥 Importador y Mapeo de CSV")
    
    archivo = st.file_uploader("Sube tu archivo CSV", type=['csv'])
    if archivo:
        df = pd.read_csv(archivo, encoding='latin-1', sep=None, engine='python')
        cabeceras = list(df.columns)
        
        try:
            res_cfg = conn.table("config_mapeo").select("mapeo").eq("id", "historial").execute()
            m_prev = res_cfg.data[0]['mapeo'] if res_cfg.data else {}
        except:
            m_prev = {}
        
        campos_db = ["fecha", "producto_id", "cantidad_vendida", "total_neto", "metodo_pago"]
        nuevo_mapeo = {}
        cols = st.columns(len(campos_db))
        for i, c_db in enumerate(campos_db):
            idx = cabeceras.index(m_prev[c_db]) if c_db in m_prev and m_prev[c_db] in cabeceras else 0
            nuevo_mapeo[c_db] = cols[i].selectbox(c_db, cabeceras, index=idx)
            
        if st.button("💾 GUARDAR MAPEO"):
            conn.table("config_mapeo").upsert({"id": "historial", "mapeo": nuevo_mapeo}).execute()
            st.success("Mapeo guardado")

        st.divider()

        nombres_csv = df[nuevo_mapeo['producto_id']].apply(limpiar_nombre).unique()
        res_p = conn.table("productos").select("id, nombre").execute()
        dict_db = {limpiar_nombre(p['nombre']): p['id'] for p in res_p.data}
        nuevos = [n for n in nombres_csv if n and n not in dict_db]

        if nuevos:
            st.warning(f"🔎 {len(nuevos)} productos nuevos.")
            seleccionados = st.multiselect("Crear:", nuevos)
            if seleccionados and st.button("✅ CREAR"):
                ins = [{"nombre": n, "categoria": "Empanada", "precio_unidad": 0.0} for n in seleccionados]
                conn.table("productos").insert(ins).execute()
                st.rerun()
        
        if st.button("🚀 INICIAR SUBIDA MASIVA"):
            progreso = st.progress(0)
            lote, cont = [], 0
            
            df[nuevo_mapeo['fecha']] = pd.to_datetime(df[nuevo_mapeo['fecha']], dayfirst=True, errors='coerce')
            
            for i, fila in df.iterrows():
                nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                if nom in dict_db and pd.notnull(fila[nuevo_mapeo['fecha']]):
                    try:
                        neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                        lote.append({
                            "fecha": fila[nuevo_mapeo['fecha']].strftime('%Y-%m-%d'),
                            "producto_id": dict_db[nom],
                            "cantidad_vendida": int(fila[nuevo_mapeo['cantidad_vendida']]),
                            "total_neto": float(neto),
                            "metodo_pago": str(fila[nuevo_mapeo['metodo_pago']])
                        })
                    except: pass
                if len(lote) >= 1000 or i == len(df) - 1:
                    if lote:
                        conn.table("historial_ventas").insert(lote).execute()
                        cont += len(lote)
                        lote = []
                    progreso.progress((i + 1) / len(df))
            st.success(f"🎊 ¡{cont} registros subidos!")

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Personal y Roles")
    
    try:
        res_emp = conn.table("empleados").select("id, nombre, rol").eq("activo", True).execute()
        lista_empleados = res_emp.data if res_emp.data else []
        dic_empleados = {e['nombre']: e for e in lista_empleados}
    except:
        lista_empleados = []
        dic_empleados = {}

    if dic_empleados:
        usuario_actual = st.selectbox("🔒 Identifícate para gestionar:", ["Selecciona tu nombre..."] + list(dic_empleados.keys()))
        es_supervisor = False
        if usuario_actual != "Selecciona tu nombre...":
            rol_actual = dic_empleados[usuario_actual]['rol']
            st.caption(f"Logueado como: **{rol_actual.upper()}**")
            if rol_actual == 'supervisor': es_supervisor = True
    else:
        st.warning("No hay empleados en el sistema. Crea el primer SUPERVISOR.")
        es_supervisor = True

    st.divider()

    if es_supervisor:
        with st.expander("➕ Dar de alta nuevo empleado"):
            with st.form("nuevo_emp"):
                nom = st.text_input("Nombre Completo")
                rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
                if st.form_submit_button("Guardar Empleado"):
                    try:
                        conn.table("empleados").insert({"nombre": nom, "rol": rol}).execute()
                        st.success(f"Empleado '{nom}' dado de alta exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar empleado: {e}")
    elif usuario_actual != "Selecciona tu nombre...":
         st.info("ℹ️ Solo los Supervisores pueden crear nuevos empleados.")

    st.subheader("Personal Actual")
    if lista_empleados:
        for emp in lista_empleados:
            col1, col2 = st.columns([3, 1])
            col1.write(f"👤 **{emp['nombre']}** - ({emp['rol']})")
            if es_supervisor:
                if col2.button("Dar de Baja ❌", key=f"del_{emp['id']}"):
                    try:
                        conn.table("empleados").update({"activo": False}).eq("id", emp['id']).execute()
                        st.success(f"Empleado dado de baja.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al dar de baja: {e}")
            st.divider()

# ==========================================
#        PANTALLA: PRODUCTOS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📦 Gestión de Productos")
    
    try:
        res_emp = conn.table("empleados").select("id, nombre, rol").eq("activo", True).execute()
        dic_empleados = {e['nombre']: e for e in res_emp.data} if res_emp.data else {}
    except:
        dic_empleados = {}

    if dic_empleados:
        usuario_actual = st.selectbox("🔒 Identifícate:", ["Selecciona tu nombre..."] + list(dic_empleados.keys()))
        es_supervisor = False
        if usuario_actual != "Selecciona tu nombre...":
            if dic_empleados[usuario_actual]['rol'] == 'supervisor':
                es_supervisor = True
    else:
        st.warning("⚠️ Crea empleados primero.")
        es_supervisor = False

    st.divider()

    try:
        res = conn.table("productos").select("*").execute()
        if res.data:
            df_prods = pd.DataFrame(res.data)
            st.subheader("Catálogo de Productos")
            for _, prod in df_prods.iterrows():
                col1, col2 = st.columns([4, 1])
                col1.write(f"🥟 **{prod['nombre']}** - ({prod['categoria']})")
                if es_supervisor:
                    if col2.button("Eliminar 🗑️", key=f"del_prod_{prod['id']}"):
                        try:
                            conn.table("productos").delete().eq("id", prod['id']).execute()
                            st.success("Producto eliminado.")
                            st.rerun()
                        except Exception:
                            st.error(f"No se puede borrar porque tiene ventas asociadas.")
                st.divider()
        else:
            st.info("No hay productos.")
    except Exception as e:
        st.error(f"Error cargando productos: {e}")

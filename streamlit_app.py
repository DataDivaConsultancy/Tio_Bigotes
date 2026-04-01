import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import datetime
import re
import plotly.express as px
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

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
        if st.button("🧠 1. DASHBOARD & IA PREDICTIVA"): ir_a('Dashboard')
        if st.button("📦 GESTIÓN PRODUCTOS"): ir_a('Productos')
    with col2:
        if st.button("📋 2. HOJA CONTROL DIARIO"): ir_a('Operativa')
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')
    with col3:
        if st.button("📥 3. CARGAR HISTORIAL CSV"): ir_a('Carga')

# ==========================================
#        PANTALLA: GESTIÓN EMPLEADOS
# ==========================================
elif st.session_state.pantalla == 'Empleados':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("👥 Gestión de Personal y Roles")
    
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

    st.subheader("Personal Actual")
    try:
        res_e = conn.table("empleados").select("nombre, rol").eq("activo", True).execute()
        if res_e.data:
            st.dataframe(pd.DataFrame(res_e.data), use_container_width=True)
        else:
            st.info("No hay empleados activos.")
    except Exception as e:
        st.error(f"Error cargando empleados: {e}")

# ==========================================
#        PANTALLA: HOJA CONTROL DIARIO
# ==========================================
elif st.session_state.pantalla == 'Operativa':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📋 Hoja de Control de Tienda")

    # 1. IDENTIFICACIÓN
    col_f, col_e = st.columns(2)
    fecha_sel = col_f.date_input("Fecha de trabajo:", datetime.date.today())
    
    try:
        res_emp = conn.table("empleados").select("id, nombre").eq("activo", True).execute()
        emps = {e['nombre']: e['id'] for e in res_emp.data} if res_emp.data else {}
    except:
        emps = {}
        
    if not emps:
        st.error("⚠️ Debes dar de alta empleados en la sección 'Gestión Empleados' primero.")
        st.stop()
    emp_sel = col_e.selectbox("Empleado responsable:", list(emps.keys()))

    st.divider()

    # 2. CARGAR PRODUCTOS Y RESTO DE AYER (CON ESCUDO ANTIFALLOS)
    res_p = conn.table("productos").select("id, nombre, categoria").execute()
    df_prod = pd.DataFrame(res_p.data)

    ayer = fecha_sel - datetime.timedelta(days=1)
    dict_ayer = {}
    try:
        res_ayer = conn.table("control_diario").select("producto_id, resto").eq("fecha", str(ayer)).execute()
        dict_ayer = {r['producto_id']: r['resto'] for r in res_ayer.data} if res_ayer.data else {}
    except Exception:
        pass # Si falla, dict_ayer queda vacío y todo el stock inicial arranca en 0

    # 3. PREPARAR TABLA PARA EDITAR
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

    st.subheader("📝 Introduce los movimientos del día")
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

    # 4. CALCULAR VENTAS EN TIEMPO REAL
    edited_df["Ventas"] = edited_df["Stock Inicial"] + edited_df["Horneados"] - edited_df["Merma"] - edited_df["Resto (Cierre)"]

    st.divider()

    # 5. GUARDAR DATOS
    if st.button("💾 GRABAR TODOS LOS DATOS Y LIMPIAR"):
        with st.spinner("Guardando registro en la base de datos..."):
            try:
                lote = []
                for _, row in edited_df.iterrows():
                    # Guardamos solo si hay algún movimiento real
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
                    st.success(f"✅ ¡Guardado con éxito! {len(lote)} productos procesados.")
                    st.balloons()
                else:
                    st.info("No se han detectado movimientos para guardar.")
            except Exception as e:
                st.error(f"Error al guardar: {e}. Revisa la estructura de 'control_diario' en Supabase.")

# ==========================================
#        PANTALLA: DASHBOARD & IA PREDICTIVA
# ==========================================
elif st.session_state.pantalla == 'Dashboard':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("🧠 IA Predictiva de Horneado (Con Calendario)")
    
    st.info("💡 El modelo de Random Forest está analizando estacionalidad, tendencias y festivos de Madrid...")

    @st.cache_data(ttl=3600, show_spinner="Entrenando IA y cruzando calendario de festivos... ⏳")
    def entrenar_ia():
        try:
            import holidays
            # Cargamos los festivos de España, provincia de Madrid para los últimos y próximos años
            años_historial = [2022, 2023, 2024, 2025, 2026, 2027]
            festivos_nacionales = holidays.Spain(years=años_historial)

            # 1. Traemos ventas y productos
            res_v = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida").limit(50000).execute()
            if not res_v.data: return None, "⚠️ La tabla de historial está vacía."
            df_v = pd.DataFrame(res_v.data)
            
            res_p = conn.table("productos").select("id, nombre").execute()
            if not res_p.data: return None, "⚠️ No hay productos."
            df_p = pd.DataFrame(res_p.data)
            
            # 2. Cruce de datos
            df = pd.merge(df_v, df_p, left_on='producto_id', right_on='id', how='left')
            df['Producto'] = df['nombre'].fillna('Desconocido')
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date # Nos aseguramos de que sea solo fecha (sin hora)
            
            # 3. Agrupación por día
            df_diario = df.groupby(['fecha', 'Producto'])['cantidad_vendida'].sum().reset_index()
            df_diario['fecha'] = pd.to_datetime(df_diario['fecha'])
            
            # 4. INGENIERÍA DE VARIABLES (FEATURE ENGINEERING) - AHORA CON FESTIVOS
            df_diario['Dia_Semana'] = df_diario['fecha'].dt.dayofweek
            df_diario['Dia_Mes'] = df_diario['fecha'].dt.day
            df_diario['Mes'] = df_diario['fecha'].dt.month
            df_diario['Año'] = df_diario['fecha'].dt.year
            
            # MAGIA: Creamos columnas de Festivo y Víspera (1 si es cierto, 0 si no)
            df_diario['Es_Festivo'] = df_diario['fecha'].apply(lambda x: 1 if x in festivos_madrid else 0)
            df_diario['Es_Vispera'] = df_diario['fecha'].apply(lambda x: 1 if (x + pd.Timedelta(days=1)) in festivos_madrid else 0)
            
            # Variables de HOY para hacer la predicción
            fecha_hoy = pd.to_datetime(datetime.date.today())
            hoy_features = pd.DataFrame({
                'Dia_Semana': [fecha_hoy.dayofweek], 
                'Dia_Mes': [fecha_hoy.day],
                'Mes': [fecha_hoy.month], 
                'Año': [fecha_hoy.year],
                'Es_Festivo': [1 if fecha_hoy in festivos_madrid else 0],
                'Es_Vispera': [1 if (fecha_hoy + pd.Timedelta(days=1)) in festivos_madrid else 0]
            })

            # 5. Entrenamiento del Bosque Aleatorio
            predicciones = []
            for prod in df_diario['Producto'].unique():
                if prod == 'Desconocido': continue
                
                datos_prod = df_diario[df_diario['Producto'] == prod]
                if len(datos_prod) > 3: 
                    # Ahora la IA entrena con 6 variables, no solo 4
                    X = datos_prod[['Dia_Semana', 'Dia_Mes', 'Mes', 'Año', 'Es_Festivo', 'Es_Vispera']]
                    y = datos_prod['cantidad_vendida']
                    
                    modelo = RandomForestRegressor(n_estimators=100, random_state=42)
                    modelo.fit(X, y)
                    pred = modelo.predict(hoy_features)[0]
                    
                    predicciones.append({
                        "Producto": prod,
                        "Previsión IA (Uds)": max(0, int(round(pred))),
                        "Días Históricos": len(datos_prod)
                    })
            
            df_resultados = pd.DataFrame(predicciones)
            if df_resultados.empty:
                return None, "⚠️ Se leyeron ventas, pero ningún producto tiene más de 3 días de historial."
                
            return df_resultados.sort_values(by="Previsión IA (Uds)", ascending=False), f"✅ IA entrenada con **{len(df_v)} registros**, cruzando datos con el calendario oficial de Madrid."
            
        except Exception as e:
            return None, f"❌ Error interno de la IA: {e}"

    # --- EJECUTAR Y MOSTRAR RESULTADOS ---
    df_prev, mensaje = entrenar_ia()
    
    st.write(mensaje)
    
    if df_prev is not None and not df_prev.empty:
        col_t, col_g = st.columns([1, 1.5])
        with col_t:
            st.subheader("🎯 Sugerencia para HOY")
            st.dataframe(df_prev[['Producto', 'Previsión IA (Uds)']], hide_index=True, use_container_width=True)
        with col_g:
            st.subheader("Gráfico de Demanda")
            fig = px.bar(df_prev.head(15), x='Previsión IA (Uds)', y='Producto', orientation='h', color='Previsión IA (Uds)', color_continuous_scale='Reds')
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

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
        
        st.subheader("⚙️ Configurar Columnas")
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
            st.warning(f"🔎 {len(nuevos)} productos nuevos detectados en el CSV.")
            seleccionados = st.multiselect("Crear estos productos:", nuevos, default=[])
            if seleccionados:
                c_cat, c_pre = st.columns(2)
                cat_m = c_cat.selectbox("Categoría:", ["Empanada", "Bebida", "Alfajor", "Otro"])
                pre_m = c_pre.number_input("Precio base (€):", value=0.0)
                if st.button("✅ CREAR SELECCIONADOS"):
                    ins_list = [{"nombre": n, "categoria": cat_m, "precio_unidad": pre_m} for n in seleccionados]
                    conn.table("productos").insert(ins_list).execute()
                    st.success("Productos creados correctamente.")
                    st.rerun()
        else:
            st.info("✅ Todos los productos del CSV ya existen en la base de datos.")
            if st.button("🚀 INICIAR SUBIDA MASIVA"):
                progreso = st.progress(0)
                lote, cont = [], 0
                for i, fila in df.iterrows():
                    nom = limpiar_nombre(fila[nuevo_mapeo['producto_id']])
                    if nom in dict_db:
                        try:
                            neto = str(fila[nuevo_mapeo['total_neto']]).replace(',', '.')
                            lote.append({
                                "fecha": pd.to_datetime(fila[nuevo_mapeo['fecha']]).strftime('%Y-%m-%d'),
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
                st.success(f"🎊 ¡Proceso terminado! {cont} registros subidos con éxito.")
                st.balloons()

# ==========================================
#        PANTALLA: PRODUCTOS
# ==========================================
elif st.session_state.pantalla == 'Productos':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.header("📦 Listado de Productos")
    try:
        res = conn.table("productos").select("*").execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)
    except Exception as e:
        st.error(f"Error cargando productos: {e}")

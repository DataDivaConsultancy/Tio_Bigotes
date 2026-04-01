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
        if st.button("📈 1. BI & ANALÍTICA"): ir_a('BI')
        if st.button("🧠 2. IA PREDICTIVA"): ir_a('Dashboard')
    with col2:
        if st.button("📋 3. HOJA CONTROL DIARIO"): ir_a('Operativa')
        if st.button("📦 GESTIÓN PRODUCTOS"): ir_a('Productos')
    with col3:
        if st.button("📥 4. CARGAR HISTORIAL CSV"): ir_a('Carga')
        if st.button("👥 GESTIÓN EMPLEADOS"): ir_a('Empleados')

# ==========================================
#        PANTALLA: BI & ANALÍTICA
# ==========================================
elif st.session_state.pantalla == 'BI':
    st.button("⬅️ VOLVER AL MENÚ", on_click=ir_a, args=('Home',))
    st.title("📈 Business Intelligence: Tío Bigotes")

    ayer_default = datetime.date.today() - datetime.timedelta(days=1)
    fecha_analisis = st.date_input("Fecha de Análisis (Cierre):", value=ayer_default)
    
    f_ayer = pd.to_datetime(fecha_analisis).date()
    f_w1 = f_ayer - pd.Timedelta(days=7) 
    f_ly = f_ayer - pd.Timedelta(days=364) 
    f_mtd_inicio = f_ayer.replace(day=1) 

    @st.cache_data(ttl=60) 
    def cargar_datos_bi():
        try:
            res_v = conn.table("historial_ventas").select("fecha, producto_id, cantidad_vendida, total_neto").order("fecha", desc=True).limit(50000).execute()
            if not res_v.data: 
                return pd.DataFrame(), pd.DataFrame(), "⚠️ No hay datos de ventas en la base de datos."
            df_v = pd.DataFrame(res_v.data)
            
            res_p = conn.table("productos").select("id, nombre").execute()
            df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame(columns=['id', 'nombre'])
            
            if not df_p.empty:
                df_v = pd.merge(df_v, df_p, left_on='producto_id', right_on='id', how='left')
                df_v['Producto'] = df_v['nombre'].fillna('Desconocido')
            else:
                df_v['Producto'] = 'Desconocido'
            
            df_v['fecha'] = pd.to_datetime(df_v['fecha']).dt.date
            
            res_m = conn.table("control_diario").select("fecha, producto_id, merma").order("fecha", desc=True).limit(10000).execute()
            df_m = pd.DataFrame(res_m.data) if res_m.data else pd.DataFrame()
            if not df_m.empty:
                df_m['fecha'] = pd.to_datetime(df_m['fecha']).dt.date

            return df_v, df_m, "✅ Datos cargados correctamente."
        except Exception as e:
            return pd.DataFrame(), pd.DataFrame(), f"❌ Error de carga: {e}"

    df_ventas, df_merma, msg_estado = cargar_datos_bi()

    if df_ventas.empty:
        st.warning(msg_estado)
    else:
        v_ayer = df_ventas[df_ventas['fecha'] == f_ayer]
        v_w1 = df_ventas[df_ventas['fecha'] == f_w1]
        v_ly = df_ventas[df_ventas['fecha'] == f_ly]
        v_mtd = df_ventas[(df_ventas['fecha'] >= f_mtd_inicio) & (df_ventas['fecha'] <= f_ayer)]
        
        m_ayer = df_merma[df_merma['fecha'] == f_ayer]['merma'].sum() if not df_merma.empty else 0
        m_w1 = df_merma[df_merma['fecha'] == f_w1]['merma'].sum() if not df_merma.empty else 0
        m_ly = df_merma[df_merma['fecha'] == f_ly]['merma'].sum() if not df_merma.empty else 0

        with st.expander("🛠️ Verificador de Datos Interno (Solo Admin)"):
            st.write(f"Buscando datos para Ayer ({f_ayer}): {len(v_ayer)} registros encontrados.")
            st.write(f"Buscando datos para W-1 ({f_w1}): {len(v_w1)} registros encontrados.")
            st.write(f"Buscando datos para LY ({f_ly}): {len(v_ly)} registros encontrados.")

        if v_ayer.empty:
            st.info(f"ℹ️ No se han encontrado ventas registradas para el día **{f_ayer.strftime('%d/%m/%Y')}**.")
        else:
            fact_ayer = v_ayer['total_neto'].sum()
            fact_w1 = v_w1['total_neto'].sum()
            fact_ly = v_ly['total_neto'].sum()
            
            uds_ayer = v_ayer['cantidad_vendida'].sum()
            uds_w1 = v_w1['cantidad_vendida'].sum()
            uds_ly = v_ly['cantidad_vendida'].sum()

            obj_fact = fact_ly * 1.15  
            obj_merma = uds_ayer * 0.01 

            st.markdown("### 📊 Panel de Rendimiento (KPIs Diarios)")
            c1, c2, c3, c4 = st.columns(4)

            delta_ly_eur = ((fact_ayer / fact_ly) - 1) * 100 if fact_ly > 0 else 0
            c1.metric("Ventas (€)", f"{fact_ayer:,.2f} €", f"{delta_ly_eur:+.1f}% vs LY")
            if fact_ayer >= obj_fact and obj_fact > 0:
                c1.caption(f"✅ Objetivo Superado (+15% LY: {obj_fact:.2f}€)")
            elif obj_fact > 0:
                c1.caption(f"⚠️ Por debajo de Objetivo ({obj_fact:.2f}€)")

            delta_w1_uds = ((uds_ayer / uds_w1) - 1) * 100 if uds_w1 > 0 else 0
            c2.metric("Unidades Vendidas", f"{uds_ayer:,.0f} uds", f"{delta_w1_uds:+.1f}% vs W-1")

            delta_merma_w1 = m_ayer - m_w1
            merma_color = "normal" if delta_merma_w1 <= 0 else "inverse" 
            c3.metric("Merma (Uds)", f"{m_ayer:,.0f} uds", f"{delta_merma_w1:+.0f} uds vs W-1", delta_color=merma_color)

            pct_merma = (m_ayer / uds_ayer) * 100 if uds_ayer > 0 else 0
            if pct_merma <= 1.0:
                c4.metric("% Merma / Venta", f"{pct_merma:.2f}%", "✅ Cumple Obj < 1%")
            else:
                c4.metric("% Merma / Venta", f"{pct_merma:.2f}%", f"❌ Exc. Obj (< 1%)", delta_color="inverse")

            st.divider()

            st.markdown("### 🏆 Ranking de Productos")
            col_rank1, col_rank2 = st.columns(2)

            with col_rank1:
                st.subheader(f"Top Ventas: {fecha_analisis.strftime('%d/%m')}")
                rank_ayer = v_ayer.groupby('Producto')['cantidad_vendida'].sum().reset_index()
                rank_ayer = rank_ayer.sort_values(by='cantidad_vendida', ascending=False).head(10)
                rank_ayer.index += 1
                st.dataframe(rank_ayer.style.format({"cantidad_vendida": "{:,.0f}"}), use_container_width=True)

            with col_rank2:
                st.subheader("Top Ventas: Acumulado Mes (MTD)")
                if not v_mtd.empty:
                    rank_mtd = v_mtd.groupby('Producto')['cantidad_vendida'].sum().reset_index()
                    rank_mtd = rank_mtd.sort_values(by='cantidad_vendida', ascending=False).head(10)
                    rank_mtd.index += 1
                    st.dataframe(rank_mtd.style.format({"cantidad_vendida": "{:,.0f}"}), use_container_width=True)
                else:
                    st.info("No hay ventas en lo que va de mes.")

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
            df

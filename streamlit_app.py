import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
import plotly.express as px
import datetime
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tío Bigotes Pro", layout="wide")

# --- CONEXIÓN MANUAL FORZADA ---
if "connections" not in st.secrets or "supabase" not in st.secrets["connections"]:
    st.error("⚠️ No se encuentran los Secrets. Ve a Settings -> Secrets y pega el bloque [connections.supabase]")
    st.stop()

try:
    # Le pasamos los datos directamente desde los secrets para evitar fallos de auto-detección
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"❌ Error al conectar con Supabase: {e}")
    st.stop()

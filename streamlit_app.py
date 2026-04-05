import csv
import io
import hashlib
import requests
import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection, execute_query
import datetime
import re
import unicodedata
import plotly.express as px
import numpy as np


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="Tío Bigotes Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
div.stButton > button:first-child {
    height: 88px;
    width: 100%;
    font-size: 18px;
    font-weight: 700;
    border-radius: 14px;
    background-color: #ff9800;
    color: white;
    border: none;
    margin-bottom: 12px;
}
div.stButton > button:first-child:hover {
    background-color: #e68a00;
    border: 2px solid #333;
}
.block-container {
    padding-top: 1.1rem;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# CONEXIÓN
# =========================================================

try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"]
    )
except Exception as e:
    st.error(f"Error de conexión a Supabase: {e}")
    st.stop()


# =========================================================
# HELPERS
# =========================================================

def normalizar_nombre_py(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("utf-8")
    t = t.upper().strip()
    t = re.sub(r'^\d+[\.\-\s]*', '', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\.+$', '', t)
    return t.strip()


def df_from_res(res) -> pd.DataFrame:
    return pd.DataFrame(res.data) if getattr(res, "data", None) else pd.DataFrame()


def clear_cache():
    st.cache_data.clear()


def safe_bool(v) -> bool:
    if pd.isna(v):
        return False
    return bool(v)


def safe_int(v, default=0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(v)
    except Exception:
        return default


def safe_float(v, default=0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def safe_date_iso(v):
    try:
        if pd.isna(v):
            return None
        return pd.to_datetime(v).date().isoformat()
    except Exception:
        return None


def rpc_call(name: str, params: dict | None = None):
    def detectar_csv(file_bytes: bytes):
    encoding = "utf-8-sig"
    text = None

    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            text = file_bytes.decode(enc)
            encoding = enc
            break
        except Exception:
            continue

    if text is None:
        raise ValueError("No pude decodificar el archivo CSV.")

    muestra = text[:5000]
    try:
        dialect = csv.Sniffer().sniff(muestra, delimiters=";,|\t,")
        sep = dialect.delimiter
    except Exception:
        sep = ";"

    return text, encoding, sep


def leer_csv_preview(file_bytes: bytes, nrows=200):
    text, encoding, sep = detectar_csv(file_bytes)
    df = pd.read_csv(io.StringIO(text), sep=sep, nrows=nrows)
    return df, encoding, sep


def iter_csv_chunks(file_bytes: bytes, sep: str, encoding: str, chunksize=20000):
    text = file_bytes.decode(encoding)
    buffer = io.StringIO(text)
    for chunk in pd.read_csv(buffer, sep=sep, chunksize=chunksize):
        yield chunk


def cargar_mapeo_guardado():
    res = conn.table("config_importaciones_v2").select("*").eq("import_type", "ventas_diarias").execute()
    df = df_from_res(res)
    if df.empty:
        return {}, None, None

    row = df.iloc[0]
    mapping = row["mapping"] if isinstance(row["mapping"], dict) else {}
    return mapping, row.get("separator"), row.get("encoding")


def rpc_scalar(resp, key=None):
    if isinstance(resp, list):
        if not resp:
            return None
        if key and isinstance(resp[0], dict) and key in resp[0]:
            return resp[0][key]
        return resp[0]
    if isinstance(resp, dict):
        if key and key in resp:
            return resp[key]
        return resp
    return resp


def fetch_existing_by_ticket_uids(ticket_uids):
    if not ticket_uids:
        return {}

    out = {}
    lote = 500

    for i in range(0, len(ticket_uids), lote):
        sub = ticket_uids[i:i+lote]
        resp = rpc_call("rpc_fetch_existing_sales_for_tickets", {
            "p_ticket_uids": sub
        })

        if isinstance(resp, list):
            for r in resp:
                out[r["line_uid"]] = {
                    "id": r["id"],
                    "payload_hash": r["payload_hash"]
                }

    return out


def prepare_rows_chunk(df_chunk, mapping, file_name, start_row_num, ticket_state):
    def val(row, key, default=""):
        src = mapping.get(key)
        if not src or src not in row.index:
            return default
        v = row[src]
        if pd.isna(v):
            return default
        return str(v).strip()

    rows = []
    row_num = start_row_num

    for _, row in df_chunk.iterrows():
        row_num += 1

        fecha_raw = val(row, "fecha")
        hora_raw = val(row, "hora")
        serie_numero_raw = val(row, "serie_numero")
        establecimiento_raw = val(row, "establecimiento")
        caja_raw = val(row, "caja")
        numero_raw = val(row, "numero")
        cliente_raw = val(row, "cliente")
        empleado_raw = val(row, "empleado")
        uds_v_raw = val(row, "uds_v")
        articulo_raw = val(row, "articulo")
        subarticulo_raw = val(row, "subarticulo")
        base_raw = val(row, "base")
        impuestos_raw = val(row, "impuestos")
        dto_total_raw = val(row, "dto_total")
        neto_raw = val(row, "neto")
        column1 = val(row, "column1")

        ticket_uid_raw = " | ".join([
            fecha_raw,
            establecimiento_raw,
            caja_raw,
            serie_numero_raw
        ])

        line_idx = ticket_state.get(ticket_uid_raw, 0) + 1
        ticket_state[ticket_uid_raw] = line_idx

        line_uid = hashlib.md5(f"{ticket_uid_raw}|{line_idx}".encode("utf-8")).hexdigest()

        payload_string = "|".join([
            hora_raw,
            numero_raw,
            cliente_raw,
            empleado_raw,
            articulo_raw,
            subarticulo_raw,
            uds_v_raw,
            base_raw,
            impuestos_raw,
            dto_total_raw,
            neto_raw
        ])
        payload_hash = hashlib.md5(payload_string.encode("utf-8")).hexdigest()

        rows.append({
            "existing_id": None,
            "source_file_name": file_name,
            "source_row_num": row_num,
            "row_num": row_num,
            "column1": column1,
            "fecha_raw": fecha_raw,
            "hora_raw": hora_raw,
            "serie_numero_raw": serie_numero_raw,
            "establecimiento_raw": establecimiento_raw,
            "caja_raw": caja_raw,
            "numero_raw": numero_raw,
            "cliente_raw": cliente_raw,
            "empleado_raw": empleado_raw,
            "uds_v_raw": uds_v_raw,
            "articulo_raw": articulo_raw,
            "subarticulo_raw": subarticulo_raw,
            "base_raw": base_raw,
            "impuestos_raw": impuestos_raw,
            "dto_total_raw": dto_total_raw,
            "neto_raw": neto_raw,
            "ticket_uid_raw": ticket_uid_raw,
            "line_idx_in_ticket": line_idx,
            "line_uid": line_uid,
            "payload_hash": payload_hash,
        })

    return rows, row_num, ticket_state


def analizar_csv_incremental(file_bytes: bytes, sep: str, encoding: str, mapping: dict, file_name: str):
    total_fisicas = 0
    total_unicas = 0
    total_nuevas = 0
    total_modificadas = 0
    total_iguales = 0

    ticket_state = {}
    current_row_num = 0

    for chunk in iter_csv_chunks(file_bytes, sep=sep, encoding=encoding, chunksize=20000):
        total_fisicas += len(chunk)

        rows, current_row_num, ticket_state = prepare_rows_chunk(
            chunk, mapping, file_name, current_row_num, ticket_state
        )

        if not rows:
            continue

        df_rows = pd.DataFrame(rows).drop_duplicates(subset=["line_uid"], keep="last")
        total_unicas += len(df_rows)

        existing_map = fetch_existing_by_ticket_uids(df_rows["ticket_uid_raw"].drop_duplicates().tolist())

        for _, r in df_rows.iterrows():
            old = existing_map.get(r["line_uid"])
            if old is None:
                total_nuevas += 1
            elif old["payload_hash"] != r["payload_hash"]:
                total_modificadas += 1
            else:
                total_iguales += 1

    return {
        "total_fisicas": total_fisicas,
        "total_unicas": total_unicas,
        "nuevas": total_nuevas,
        "modificadas": total_modificadas,
        "iguales": total_iguales,
        "a_subir": total_nuevas + total_modificadas
    }
    """
    Llama a una función Postgres expuesta por Supabase vía REST:
    POST /rest/v1/rpc/<function_name>
    """
    base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
    api_key = st.secrets["connections"]["supabase"]["key"]

    url = f"{base_url}/rest/v1/rpc/{name}"

    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        url,
        headers=headers,
        json=params or {},
        timeout=30,
    )

    if not response.ok:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"RPC {name} falló: {detail}")

    # Algunas RPC devuelven filas, otras null/void
    try:
        return response.json()
    except Exception:
        return None


@st.cache_data(ttl=60)
def cargar_local_id():
    res = conn.table("locales_v2").select("*").eq("codigo", "DIP159").execute()
    df = df_from_res(res)
    if df.empty:
        return None
    return int(df.iloc[0]["id"])


@st.cache_data(ttl=60)
def cargar_dim_productos() -> pd.DataFrame:
    res = conn.table("vw_productos_dim").select("*").execute()
    df = df_from_res(res)

    if not df.empty:
        if "orden_visual" in df.columns:
            df["orden_visual"] = pd.to_numeric(df["orden_visual"], errors="coerce").fillna(100).astype(int)

        for col in ["activo", "es_vendible", "es_producible", "afecta_forecast", "visible_en_control_diario", "visible_en_forecast"]:
            if col in df.columns:
                df[col] = df[col].fillna(False).astype(bool)

    return df


@st.cache_data(ttl=60)
def cargar_empleados_activos() -> pd.DataFrame:
    res = conn.table("empleados_v2").select("*").eq("activo", True).execute()
    return df_from_res(res)


def fetch_paginated(table_name, columns="*", filters=None, order_by="id", page_size=5000) -> pd.DataFrame:
    rows = []
    offset = 0

    while True:
        q = conn.table(table_name).select(columns)

        if filters:
            for f in filters:
                op = f["op"]
                col = f["col"]
                val = f["val"]

                if op == "eq":
                    q = q.eq(col, val)
                elif op == "gte":
                    q = q.gte(col, val)
                elif op == "lte":
                    q = q.lte(col, val)
                elif op == "in":
                    q = q.in_(col, val)

        if order_by:
            q = q.order(order_by)

        res = q.range(offset, offset + page_size - 1).execute()
        data = res.data or []
        rows.extend(data)

        if len(data) < page_size:
            break

        offset += page_size

    return pd.DataFrame(rows)


def filtros_categoria_producto(
    df_dim: pd.DataFrame,
    key_prefix: str,
    solo_activos=True,
    solo_control=False,
    solo_forecast=False
):
    df = df_dim.copy()

    if solo_activos and "activo" in df.columns:
        df = df[df["activo"] == True]

    if solo_control and "visible_en_control_diario" in df.columns:
        df = df[df["visible_en_control_diario"] == True]

    if solo_forecast and "visible_en_forecast" in df.columns:
        df = df[df["visible_en_forecast"] == True]

    categorias = sorted(df["categoria_nombre"].dropna().unique().tolist())

    categorias_sel = st.multiselect(
        "Categoría",
        categorias,
        default=categorias,
        key=f"{key_prefix}_categorias"
    )

    if categorias_sel:
        df = df[df["categoria_nombre"].isin(categorias_sel)]
    else:
        df = df.iloc[0:0]

    productos = sorted(df["producto_nombre"].dropna().unique().tolist())

    productos_sel = st.multiselect(
        "Producto",
        productos,
        default=[],
        key=f"{key_prefix}_productos"
    )

    return categorias_sel, productos_sel


def aplicar_filtros_df(df: pd.DataFrame, df_dim: pd.DataFrame, categorias_sel, productos_sel) -> pd.DataFrame:
    if df.empty:
        return df

    dim_cols = [
        "producto_id", "producto_nombre", "categoria_nombre",
        "activo", "es_producible", "afecta_forecast",
        "visible_en_control_diario", "visible_en_forecast",
        "orden_visual", "uds_equivalentes_empanadas",
        "fecha_inicio_venta", "fecha_fin_venta"
    ]
    dim_cols = [c for c in dim_cols if c in df_dim.columns]

    out = df.merge(df_dim[dim_cols], on="producto_id", how="left")

    if categorias_sel:
        out = out[out["categoria_nombre"].isin(categorias_sel)]

    if productos_sel:
        out = out[out["producto_nombre"].isin(productos_sel)]

    return out


def cargar_ventas_rango(fecha_ini: datetime.date, fecha_fin: datetime.date) -> pd.DataFrame:
    df = fetch_paginated(
        "ventas_staging_v2",
        columns="id,batch_id,raw_id,row_num,fecha,hora,fecha_hora,ticket_uid,producto_id,uds_v,neto,estado_mapeo",
        filters=[
            {"op": "gte", "col": "fecha", "val": str(fecha_ini)},
            {"op": "lte", "col": "fecha", "val": str(fecha_fin)},
        ],
        order_by="fecha",
        page_size=10000
    )

    if not df.empty:
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        df["uds_v"] = pd.to_numeric(df["uds_v"], errors="coerce").fillna(0)
        df["neto"] = pd.to_numeric(df["neto"], errors="coerce").fillna(0)

        if "hora" in df.columns:
            df["hora"] = df["hora"].astype(str).str.slice(0, 8)

    return df


def cargar_control_diario(fecha_sel: datetime.date, local_id: int) -> pd.DataFrame:
    return fetch_paginated(
        "control_diario_v2",
        columns="*",
        filters=[
            {"op": "eq", "col": "local_id", "val": local_id},
            {"op": "eq", "col": "fecha", "val": str(fecha_sel)},
        ],
        order_by="producto_id",
        page_size=1000
    )


def cargar_control_ayer(fecha_ayer: datetime.date, local_id: int) -> pd.DataFrame:
    return fetch_paginated(
        "control_diario_v2",
        columns="producto_id,resto",
        filters=[
            {"op": "eq", "col": "local_id", "val": local_id},
            {"op": "eq", "col": "fecha", "val": str(fecha_ayer)},
        ],
        order_by="producto_id",
        page_size=1000
    )


def cargar_hornadas_fecha(fecha_sel: datetime.date, local_id: int) -> pd.DataFrame:
    return fetch_paginated(
        "hornadas_eventos_v2",
        columns="*",
        filters=[
            {"op": "eq", "col": "local_id", "val": local_id},
            {"op": "eq", "col": "fecha", "val": str(fecha_sel)},
        ],
        order_by="id",
        page_size=1000
    )


def guardar_control_diario(payloads):
    if not payloads:
        return

    for p in payloads:
        rpc_call("rpc_upsert_control_diario", {
            "p_local_id": p["local_id"],
            "p_fecha": p["fecha"],
            "p_producto_id": p["producto_id"],
            "p_empleado_id": p["empleado_id"],
            "p_stock_inicial": p["stock_inicial"],
            "p_horneados": p["horneados"],
            "p_merma": p["merma"],
            "p_resto": p["resto"],
            "p_incidencias": p["incidencias"]
        })


# =========================================================
# ESTADO UI
# =========================================================

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "Home"


def ir_a(p):
    st.session_state.pantalla = p


# =========================================================
# DATOS BASE
# =========================================================

LOCAL_ID = cargar_local_id()
if not LOCAL_ID:
    st.error("No encuentro el local DIP159 en la base de datos.")
    st.stop()

DF_DIM = cargar_dim_productos()


# =========================================================
# HOME
# =========================================================

if st.session_state.pantalla == "Home":
    st.title("🥐 Tío Bigotes - Gestión Integral")
    st.write(f"📍 Diputació 159 | {datetime.date.today().strftime('%d/%m/%Y')}")
    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📦 PRODUCTOS"):
            ir_a("Productos")
        if st.button("👥 EMPLEADOS"):
            ir_a("Empleados")

    with c2:
        if st.button("📋 CONTROL DIARIO"):
            ir_a("Operativa")
        if st.button("📈 HISTORIAL / BI"):
            ir_a("BI")

    with c3:
        if st.button("🧠 FORECAST"):
            ir_a("Forecast")
        if st.button("🧩 PENDIENTES"):
            ir_a("Pendientes")


# =========================================================
# PRODUCTOS
# =========================================================

elif st.session_state.pantalla == "Productos":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📦 Catálogo de Productos")

    res_dim = conn.table("vw_productos_dim").select("*").execute()
    df_prod = df_from_res(res_dim)

    if df_prod.empty:
        st.warning("No hay productos cargados.")
        st.stop()

    col_f1, col_f2, col_f3 = st.columns(3)

    categorias = sorted(df_prod["categoria_nombre"].dropna().unique().tolist())
    cat_sel = col_f1.multiselect("Filtrar por categoría", categorias, default=categorias)

    solo_activos = col_f2.toggle("Solo activos", value=True)
    solo_forecast = col_f3.toggle("Solo visibles en forecast", value=False)

    df_view = df_prod.copy()

    if cat_sel:
        df_view = df_view[df_view["categoria_nombre"].isin(cat_sel)]

    if solo_activos:
        df_view = df_view[df_view["activo"] == True]

    if solo_forecast:
        df_view = df_view[df_view["visible_en_forecast"] == True]

    df_view = df_view.sort_values(["categoria_nombre", "orden_visual", "producto_nombre"])

    columnas_editor = [
        "producto_id",
        "producto_nombre",
        "categoria_nombre",
        "activo",
        "es_producible",
        "afecta_forecast",
        "visible_en_control_diario",
        "visible_en_forecast",
        "orden_visual",
        "uds_equivalentes_empanadas",
        "fecha_inicio_venta",
        "fecha_fin_venta",
        "observaciones"
    ]

    df_edit = df_view[columnas_editor].copy()

    editado = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "producto_id": st.column_config.NumberColumn("ID", disabled=True),
            "producto_nombre": st.column_config.TextColumn("Producto", disabled=True),
            "categoria_nombre": st.column_config.TextColumn("Categoría", disabled=True),
            "activo": st.column_config.CheckboxColumn("Activo"),
            "es_producible": st.column_config.CheckboxColumn("Producible"),
            "afecta_forecast": st.column_config.CheckboxColumn("Afecta Forecast"),
            "visible_en_control_diario": st.column_config.CheckboxColumn("Visible Control"),
            "visible_en_forecast": st.column_config.CheckboxColumn("Visible Forecast"),
            "orden_visual": st.column_config.NumberColumn("Orden", step=1),
            "uds_equivalentes_empanadas": st.column_config.NumberColumn("Eq. Emp", step=1),
            "fecha_inicio_venta": st.column_config.DateColumn("Inicio venta"),
            "fecha_fin_venta": st.column_config.DateColumn("Fin venta"),
            "observaciones": st.column_config.TextColumn("Observaciones")
        }
    )

    if st.button("💾 Guardar cambios de productos"):
        try:
            for _, row in editado.iterrows():
                rpc_call("rpc_actualizar_producto", {
                    "p_id": int(row["producto_id"]),
                    "p_activo": safe_bool(row["activo"]),
                    "p_es_producible": safe_bool(row["es_producible"]),
                    "p_afecta_forecast": safe_bool(row["afecta_forecast"]),
                    "p_visible_en_control_diario": safe_bool(row["visible_en_control_diario"]),
                    "p_visible_en_forecast": safe_bool(row["visible_en_forecast"]),
                    "p_orden_visual": safe_int(row["orden_visual"], 100),
                    "p_uds_equivalentes_empanadas": safe_float(row["uds_equivalentes_empanadas"], 0),
                    "p_fecha_inicio_venta": safe_date_iso(row["fecha_inicio_venta"]),
                    "p_fecha_fin_venta": safe_date_iso(row["fecha_fin_venta"]),
                    "p_observaciones": row["observaciones"] if pd.notnull(row["observaciones"]) else None
                })

            clear_cache()
            st.success("✅ Productos actualizados")
            st.rerun()
        except Exception as e:
            st.error(f"Error guardando productos: {e}")

    st.divider()

    with st.expander("➕ Crear producto nuevo"):
        res_cat = conn.table("categorias_producto_v2").select("id,nombre,codigo").execute()
        df_cat = df_from_res(res_cat)

        if not df_cat.empty:
            with st.form("nuevo_producto_form"):
                nombre_nuevo = st.text_input("Nombre producto")
                categoria_nueva = st.selectbox("Categoría", df_cat["nombre"].tolist())
                activo_nuevo = st.checkbox("Activo", value=True)
                producible_nuevo = st.checkbox("Es producible", value=False)
                forecast_nuevo = st.checkbox("Afecta forecast", value=False)
                visible_control_nuevo = st.checkbox("Visible en control diario", value=False)
                visible_forecast_nuevo = st.checkbox("Visible en forecast", value=False)
                orden_nuevo = st.number_input("Orden visual", min_value=1, step=1, value=100)
                eq_emp_nuevo = st.number_input("Equivalente empanadas", min_value=0.0, step=1.0, value=0.0)
                obs_nuevo = st.text_input("Observaciones")

                guardar_nuevo = st.form_submit_button("Crear producto")

                if guardar_nuevo and nombre_nuevo.strip():
                    try:
                        cat_row = df_cat[df_cat["nombre"] == categoria_nueva].iloc[0]

                        rpc_call("rpc_crear_producto", {
                            "p_nombre": nombre_nuevo.strip(),
                            "p_nombre_normalizado": normalizar_nombre_py(nombre_nuevo.strip()),
                            "p_categoria_id": int(cat_row["id"]),
                            "p_subtipo": str(cat_row["codigo"]).lower(),
                            "p_activo": activo_nuevo,
                            "p_es_vendible": True,
                            "p_es_producible": producible_nuevo,
                            "p_afecta_forecast": forecast_nuevo,
                            "p_visible_en_control_diario": visible_control_nuevo,
                            "p_visible_en_forecast": visible_forecast_nuevo,
                            "p_orden_visual": int(orden_nuevo),
                            "p_uds_equivalentes_empanadas": float(eq_emp_nuevo),
                            "p_observaciones": obs_nuevo if obs_nuevo else None
                        })

                        clear_cache()
                        st.success("✅ Producto creado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando producto: {e}")


# =========================================================
# EMPLEADOS
# =========================================================

elif st.session_state.pantalla == "Empleados":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("👥 Gestión de Empleados")

    with st.expander("➕ Nuevo empleado"):
        with st.form("nuevo_empleado"):
            nombre = st.text_input("Nombre")
            rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor"])
            guardar = st.form_submit_button("Guardar empleado")

            if guardar and nombre.strip():
                try:
                    rpc_call("rpc_crear_empleado", {
                        "p_local_id": LOCAL_ID,
                        "p_codigo_pos": None,
                        "p_nombre": nombre.strip(),
                        "p_rol": rol,
                        "p_fecha_alta": str(datetime.date.today())
                    })
                    clear_cache()
                    st.success("✅ Empleado creado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creando empleado: {e}")

    res_emp = conn.table("empleados_v2").select("*").eq("local_id", LOCAL_ID).order("activo", desc=True).order("nombre").execute()
    df_emp = df_from_res(res_emp)

    if df_emp.empty:
        st.info("No hay empleados.")
    else:
        for _, row in df_emp.iterrows():
            c1, c2, c3 = st.columns([5, 2, 1])
            c1.write(f"**{row['nombre']}**")
            c2.write(f"{row['rol']} | {'Activo' if row['activo'] else 'Inactivo'}")

            if row["activo"]:
                if c3.button("Baja", key=f"baja_emp_{row['id']}"):
                    try:
                        rpc_call("rpc_baja_empleado", {
                            "p_id": int(row["id"]),
                            "p_fecha_baja": str(datetime.date.today())
                        })
                        clear_cache()
                        st.success("✅ Empleado dado de baja")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error dando de baja: {e}")


# =========================================================
# OPERATIVA / CONTROL DIARIO
# =========================================================

elif st.session_state.pantalla == "Operativa":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📋 Hoja de Control Diario")

    col1, col2 = st.columns(2)
    fecha_sel = col1.date_input("Fecha", value=datetime.date.today())

    df_emp = cargar_empleados_activos()
    if df_emp.empty:
        st.error("No hay empleados activos. Crea al menos uno.")
        st.stop()

    emp_nombre = col2.selectbox("Responsable", sorted(df_emp["nombre"].tolist()))
    empleado_id = int(df_emp[df_emp["nombre"] == emp_nombre].iloc[0]["id"])

    st.subheader("Filtro de productos")
    categorias_sel, productos_sel = filtros_categoria_producto(
        DF_DIM,
        key_prefix="operativa",
        solo_activos=True,
        solo_control=True,
        solo_forecast=False
    )

    df_control_dim = DF_DIM.copy()
    df_control_dim = df_control_dim[
        (df_control_dim["activo"] == True) &
        (df_control_dim["visible_en_control_diario"] == True)
    ]

    if categorias_sel:
        df_control_dim = df_control_dim[df_control_dim["categoria_nombre"].isin(categorias_sel)]
    if productos_sel:
        df_control_dim = df_control_dim[df_control_dim["producto_nombre"].isin(productos_sel)]

    df_control_dim = df_control_dim.sort_values(["categoria_nombre", "orden_visual", "producto_nombre"])

    if df_control_dim.empty:
        st.warning("No hay productos visibles en control diario con esos filtros.")
        st.stop()

    df_hoy = cargar_control_diario(fecha_sel, LOCAL_ID)
    df_ayer = cargar_control_ayer(fecha_sel - datetime.timedelta(days=1), LOCAL_ID)

    dict_hoy = {}
    if not df_hoy.empty:
        dict_hoy = {
            int(r["producto_id"]): {
                "stock_inicial": safe_float(r["stock_inicial"]),
                "horneados": safe_float(r["horneados"]),
                "merma": safe_float(r["merma"]),
                "resto": safe_float(r["resto"]),
                "incidencias": r.get("incidencias")
            }
            for _, r in df_hoy.iterrows()
        }

    dict_ayer = {}
    if not df_ayer.empty:
        dict_ayer = {
            int(r["producto_id"]): safe_float(r["resto"])
            for _, r in df_ayer.iterrows()
        }

    filas = []
    for _, p in df_control_dim.iterrows():
        pid = int(p["producto_id"])

        if pid in dict_hoy:
            base = dict_hoy[pid]
            filas.append({
                "producto_id": pid,
                "categoria": p["categoria_nombre"],
                "producto": p["producto_nombre"],
                "stock_inicial": base["stock_inicial"],
                "horneados": base["horneados"],
                "merma": base["merma"],
                "resto": base["resto"],
                "incidencias": base.get("incidencias")
            })
        else:
            filas.append({
                "producto_id": pid,
                "categoria": p["categoria_nombre"],
                "producto": p["producto_nombre"],
                "stock_inicial": dict_ayer.get(pid, 0),
                "horneados": 0,
                "merma": 0,
                "resto": 0,
                "incidencias": None
            })

    df_editor = pd.DataFrame(filas)

    editado = st.data_editor(
        df_editor,
        use_container_width=True,
        hide_index=True,
        column_config={
            "producto_id": st.column_config.NumberColumn("ID", disabled=True),
            "categoria": st.column_config.TextColumn("Categoría", disabled=True),
            "producto": st.column_config.TextColumn("Producto", disabled=True),
            "stock_inicial": st.column_config.NumberColumn("Stock inicial", step=1),
            "horneados": st.column_config.NumberColumn("Horneados", step=1),
            "merma": st.column_config.NumberColumn("Merma", step=1),
            "resto": st.column_config.NumberColumn("Resto", step=1),
            "incidencias": st.column_config.TextColumn("Incidencias")
        }
    )

    st.divider()
    st.subheader("Registrar hornada")

    c_h1, c_h2, c_h3 = st.columns([2, 1, 1])
    with c_h1:
        producto_horno = st.selectbox("Producto", df_control_dim["producto_nombre"].tolist())
    with c_h2:
        cantidad_horno = st.number_input("Cantidad", min_value=1, step=1, value=12)
    with c_h3:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Guardar hornada"):
            try:
                pid = int(df_control_dim[df_control_dim["producto_nombre"] == producto_horno].iloc[0]["producto_id"])
                rpc_call("rpc_crear_hornada", {
                    "p_local_id": LOCAL_ID,
                    "p_fecha": str(fecha_sel),
                    "p_fecha_hora": datetime.datetime.now().isoformat(),
                    "p_producto_id": pid,
                    "p_cantidad": float(cantidad_horno),
                    "p_empleado_id": empleado_id,
                    "p_notas": None
                })
                clear_cache()
                st.success("✅ Hornada registrada")
                st.rerun()
            except Exception as e:
                st.error(f"Error registrando hornada: {e}")

    df_hornadas = cargar_hornadas_fecha(fecha_sel, LOCAL_ID)
    if not df_hornadas.empty:
        df_hornadas["cantidad"] = pd.to_numeric(df_hornadas["cantidad"], errors="coerce").fillna(0)
        df_hornadas = df_hornadas.merge(
            DF_DIM[["producto_id", "producto_nombre"]],
            on="producto_id",
            how="left"
        )
        resumen_h = df_hornadas.groupby("producto_nombre", as_index=False)["cantidad"].sum().sort_values("cantidad", ascending=False)
        st.write("### Hornadas registradas hoy")
        st.dataframe(resumen_h, use_container_width=True, hide_index=True)

    if st.button("💾 Guardar control diario"):
        try:
            payloads = []
            for _, row in editado.iterrows():
                payloads.append({
                    "local_id": LOCAL_ID,
                    "fecha": str(fecha_sel),
                    "producto_id": int(row["producto_id"]),
                    "empleado_id": empleado_id,
                    "stock_inicial": safe_float(row["stock_inicial"]),
                    "horneados": safe_float(row["horneados"]),
                    "merma": safe_float(row["merma"]),
                    "resto": safe_float(row["resto"]),
                    "incidencias": row["incidencias"] if pd.notnull(row["incidencias"]) else None
                })

            guardar_control_diario(payloads)
            clear_cache()
            st.success("✅ Control diario guardado")
        except Exception as e:
            st.error(f"Error guardando control diario: {e}")


# =========================================================
# BI / HISTORIAL
# =========================================================

elif st.session_state.pantalla == "BI":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📈 Historial / Business Intelligence")

    col1, col2 = st.columns(2)
    fecha_ini = col1.date_input("Desde", value=datetime.date.today() - datetime.timedelta(days=30))
    fecha_fin = col2.date_input("Hasta", value=datetime.date.today())

    st.subheader("Filtros")
    categorias_sel, productos_sel = filtros_categoria_producto(
        DF_DIM,
        key_prefix="bi",
        solo_activos=False,
        solo_control=False,
        solo_forecast=False
    )

    with st.spinner("Cargando ventas..."):
        df_sales = cargar_ventas_rango(fecha_ini, fecha_fin)

    if df_sales.empty:
        st.warning("No hay ventas en ese rango.")
        st.stop()

    df_sales = aplicar_filtros_df(df_sales, DF_DIM, categorias_sel, productos_sel)

    if df_sales.empty:
        st.warning("No hay datos tras aplicar filtros.")
        st.stop()

    total_ventas = df_sales["neto"].sum()
    total_uds = df_sales["uds_v"].sum()
    total_tickets = df_sales["ticket_uid"].nunique()
    ticket_medio = total_ventas / total_tickets if total_tickets else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas netas", f"{total_ventas:,.2f} €")
    c2.metric("Unidades", f"{total_uds:,.0f}")
    c3.metric("Tickets", f"{total_tickets:,.0f}")
    c4.metric("Ticket medio", f"{ticket_medio:,.2f} €")

    st.divider()

    df_day = df_sales.groupby("fecha", as_index=False).agg(
        ventas=("neto", "sum"),
        unidades=("uds_v", "sum"),
        tickets=("ticket_uid", "nunique")
    )

    fig_day = px.line(df_day, x="fecha", y="ventas", title="Ventas por día")
    st.plotly_chart(fig_day, use_container_width=True)

    df_prod = df_sales.groupby(["producto_nombre", "categoria_nombre"], as_index=False).agg(
        ventas=("neto", "sum"),
        unidades=("uds_v", "sum")
    ).sort_values("ventas", ascending=False).head(20)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_top = px.bar(
            df_prod,
            x="producto_nombre",
            y="ventas",
            color="categoria_nombre",
            title="Top productos por ventas"
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_g2:
        df_hour = df_sales.copy()
        df_hour["hora_num"] = pd.to_datetime(df_hour["hora"], format="%H:%M:%S", errors="coerce").dt.hour
        df_hour = df_hour.groupby("hora_num", as_index=False).agg(
            ventas=("neto", "sum"),
            unidades=("uds_v", "sum")
        ).sort_values("hora_num")
        fig_hour = px.bar(df_hour, x="hora_num", y="ventas", title="Ventas por hora")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.write("### Detalle por producto")
    st.dataframe(df_prod, use_container_width=True, hide_index=True)


# =========================================================
# FORECAST
# =========================================================

elif st.session_state.pantalla == "Forecast":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🧠 Forecast de Horneado")

    c1, c2, c3 = st.columns(3)
    fecha_pred = c1.date_input("Fecha objetivo", datetime.date.today())
    estrategia = c2.select_slider(
        "Estrategia",
        options=["Defensiva", "Equilibrada", "Agresiva"],
        value="Equilibrada"
    )
    es_festivo = c3.toggle("Festivo / Puente", value=False)

    st.subheader("Filtros")
    categorias_sel, productos_sel = filtros_categoria_producto(
        DF_DIM,
        key_prefix="forecast",
        solo_activos=True,
        solo_control=False,
        solo_forecast=True
    )

    if st.button("🚀 Calcular forecast"):
        df_forecast_dim = DF_DIM.copy()
        df_forecast_dim = df_forecast_dim[
            (df_forecast_dim["activo"] == True) &
            (df_forecast_dim["visible_en_forecast"] == True) &
            (df_forecast_dim["afecta_forecast"] == True)
        ]

        fecha_pred_ts = pd.to_datetime(fecha_pred)

        if "fecha_inicio_venta" in df_forecast_dim.columns:
            df_forecast_dim["fecha_inicio_venta"] = pd.to_datetime(df_forecast_dim["fecha_inicio_venta"], errors="coerce")
            df_forecast_dim = df_forecast_dim[
                df_forecast_dim["fecha_inicio_venta"].isna() |
                (df_forecast_dim["fecha_inicio_venta"] <= fecha_pred_ts)
            ]

        if "fecha_fin_venta" in df_forecast_dim.columns:
            df_forecast_dim["fecha_fin_venta"] = pd.to_datetime(df_forecast_dim["fecha_fin_venta"], errors="coerce")
            df_forecast_dim = df_forecast_dim[
                df_forecast_dim["fecha_fin_venta"].isna() |
                (df_forecast_dim["fecha_fin_venta"] >= fecha_pred_ts)
            ]

        if categorias_sel:
            df_forecast_dim = df_forecast_dim[df_forecast_dim["categoria_nombre"].isin(categorias_sel)]
        if productos_sel:
            df_forecast_dim = df_forecast_dim[df_forecast_dim["producto_nombre"].isin(productos_sel)]

        if df_forecast_dim.empty:
            st.warning("No hay productos válidos para forecast con esos filtros.")
            st.stop()

        fecha_ini_hist = fecha_pred - datetime.timedelta(days=365)

        with st.spinner("Analizando histórico..."):
            df_sales = cargar_ventas_rango(fecha_ini_hist, fecha_pred - datetime.timedelta(days=1))

        if df_sales.empty:
            st.warning("No hay histórico suficiente.")
            st.stop()

        df_sales = df_sales.merge(
            df_forecast_dim[["producto_id", "producto_nombre"]],
            on="producto_id",
            how="inner"
        )

        if df_sales.empty:
            st.warning("No hay ventas históricas para esos productos.")
            st.stop()

        df_daily = df_sales.groupby(["fecha", "producto_id", "producto_nombre"], as_index=False)["uds_v"].sum()
        df_daily["fecha"] = pd.to_datetime(df_daily["fecha"])
        objetivo_dow = fecha_pred.weekday()

        pct_map = {"Defensiva": 50, "Equilibrada": 75, "Agresiva": 88}
        pct = pct_map[estrategia]

        resultados = []

        for _, p in df_forecast_dim.iterrows():
            pid = p["producto_id"]
            nombre = p["producto_nombre"]

            sub = df_daily[df_daily["producto_id"] == pid].copy()
            sub["dow"] = sub["fecha"].dt.weekday
            hist = sub[sub["dow"] == objetivo_dow]["uds_v"]

            if hist.empty:
                base = sub["uds_v"].mean() if not sub.empty else 0
            else:
                base = np.percentile(hist, pct)

            if es_festivo:
                base *= 1.15

            if estrategia == "Agresiva":
                base *= 1.05

            total = int(np.ceil(base))
            if total > 0:
                resultados.append({
                    "Producto": nombre,
                    "Total sugerido": total,
                    "Tanda 1": int(np.ceil(total * 0.7)),
                    "Tanda 2": int(np.floor(total * 0.3))
                })

        if not resultados:
            st.warning("No pude generar forecast.")
            st.stop()

        df_res = pd.DataFrame(resultados).sort_values("Total sugerido", ascending=False)

        st.success(f"✅ Forecast generado | Total sugerido: {df_res['Total sugerido'].sum()} uds")
        st.dataframe(df_res, use_container_width=True, hide_index=True)

        txt = f"*PLAN DE HORNEADO - {fecha_pred.strftime('%d/%m/%Y')}*\n"
        txt += f"Estrategia: {estrategia} | Festivo: {'Sí' if es_festivo else 'No'}\n"
        txt += "-" * 25 + "\n"

        for _, r in df_res.iterrows():
            txt += f"• {r['Producto']}: {r['Tanda 1']} + {r['Tanda 2']} = *{r['Total sugerido']}*\n"

        st.text_area("Texto para WhatsApp", txt, height=300)


# =========================================================
# PENDIENTES
# =========================================================

elif st.session_state.pantalla == "Pendientes":
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🧩 Artículos pendientes de mapear")

    res_pend = conn.table("articulos_pendientes_v2").select("*").eq("estado", "pendiente").order("veces_detectado", desc=True).execute()
    df_pend = df_from_res(res_pend)

    if df_pend.empty:
        st.success("✅ No quedan pendientes.")
        st.stop()

    st.dataframe(
        df_pend[["articulo_raw_ejemplo", "alias_normalizado", "veces_detectado", "primera_fecha", "ultima_fecha"]],
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    st.subheader("Resolver un pendiente")

    alias_sel = st.selectbox("Alias pendiente", df_pend["alias_normalizado"].tolist())

    df_match = df_pend[df_pend["alias_normalizado"] == alias_sel].iloc[0]
    st.write(f"**Ejemplo raw:** {df_match['articulo_raw_ejemplo']}")
    st.write(f"**Veces detectado:** {df_match['veces_detectado']}")

    nombres_producto = sorted(DF_DIM["producto_nombre"].dropna().unique().tolist())
    producto_destino = st.selectbox("Mapear a producto existente", nombres_producto)

    c1, c2 = st.columns(2)

    if c1.button("✅ Resolver pendiente"):
        try:
            pid = int(DF_DIM[DF_DIM["producto_nombre"] == producto_destino].iloc[0]["producto_id"])

            rpc_call("rpc_resolver_pendiente", {
                "p_alias_normalizado": alias_sel,
                "p_alias_raw": df_match["articulo_raw_ejemplo"],
                "p_producto_id": pid
            })

            clear_cache()
            st.success("✅ Pendiente resuelto")
            st.rerun()
        except Exception as e:
            st.error(f"Error resolviendo pendiente: {e}")

    if c2.button("🚫 Marcar como descartado"):
        try:
            rpc_call("rpc_descartar_pendiente", {
                "p_alias_normalizado": alias_sel,
                "p_nota": "Descartado manualmente desde Streamlit"
            })

            clear_cache()
            st.success("✅ Pendiente descartado")
            st.rerun()
        except Exception as e:
            st.error(f"Error descartando pendiente: {e}")

import datetime
import csv
import hashlib
import io
import re
import secrets
import string
import time
import unicodedata
import urllib.parse
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from st_supabase_connection import SupabaseConnection


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="Tío Bigotes Pro",
    page_icon="🥟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
/* ── Paleta Tío Bigotes ── */
:root {
    --tb-azul: #4A9BD9;
    --tb-azul-hover: #3A7FB8;
    --tb-azul-light: #E8F4FD;
    --tb-dark: #1A1A2E;
    --tb-gris: #F7F8FA;
    --tb-texto: #2C3E50;
    --tb-verde: #27AE60;
    --tb-rojo: #E74C3C;
}

/* ── Layout general ── */
.block-container {
    padding-top: 1rem;
    max-width: 1200px;
}

/* ── Botones de navegación Home ── */
div[data-testid="stVerticalBlock"] > div.home-nav div.stButton > button {
    height: 88px;
    width: 100%;
    font-size: 17px;
    font-weight: 600;
    border-radius: 12px;
    background: linear-gradient(135deg, #4A9BD9 0%, #3A7FB8 100%);
    color: white;
    border: none;
    margin-bottom: 10px;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(74, 155, 217, 0.3);
}
div[data-testid="stVerticalBlock"] > div.home-nav div.stButton > button:hover {
    background: linear-gradient(135deg, #3A7FB8 0%, #2E6A9E 100%);
    box-shadow: 0 4px 16px rgba(74, 155, 217, 0.4);
    transform: translateY(-1px);
}

/* ── Header con fondo oscuro ── */
.tb-header {
    background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
    color: white;
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
}
.tb-header h1 {
    color: white !important;
    font-size: 1.8rem;
    margin: 0;
}
.tb-header .tb-subtitle {
    color: #4A9BD9;
    font-size: 0.95rem;
    margin-top: 4px;
}
.tb-header .tb-user {
    color: #B0C4DE;
    font-size: 0.85rem;
    text-align: right;
}

/* ── Cards de métricas ── */
div[data-testid="stMetric"] {
    background: #F7F8FA;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 12px 16px;
    border-left: 4px solid #4A9BD9;
}
div[data-testid="stMetric"] label {
    color: #64748B !important;
    font-size: 0.8rem !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #1A1A2E !important;
    font-weight: 700 !important;
}

/* ── Botones de acción (guardar, crear, etc.) ── */
button[kind="primary"], .stFormSubmitButton > button {
    background: linear-gradient(135deg, #4A9BD9 0%, #3A7FB8 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    background: linear-gradient(135deg, #3A7FB8 0%, #2E6A9E 100%) !important;
}

/* ── Botones secundarios / VOLVER ── */
button[kind="secondary"] {
    border: 2px solid #4A9BD9 !important;
    color: #4A9BD9 !important;
    border-radius: 8px !important;
    background: #EBF4FB !important;
}

/* ── Data editor ── */
div[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    overflow: hidden;
}

/* ── Expander ── */
div[data-testid="stExpander"] {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    background: #FAFBFC;
}

/* ── Tabs y dividers ── */
hr {
    border-color: #E2E8F0 !important;
}

/* ── Login centrado ── */
.login-container {
    max-width: 420px;
    margin: 3rem auto;
    padding: 2rem;
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    border-top: 4px solid #4A9BD9;
}
.login-logo {
    text-align: center;
    font-size: 3rem;
    margin-bottom: 0.5rem;
}
.login-title {
    text-align: center;
    color: #1A1A2E;
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.login-subtitle {
    text-align: center;
    color: #64748B;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* ── Sección header de cada pantalla ── */
.page-header {
    background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 10px;
}
.page-header h2 {
    color: white !important;
    margin: 0 !important;
    font-size: 1.4rem;
}

/* ── Toast/alerts ── */
div[data-testid="stAlert"] {
    border-radius: 10px;
}
</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# CONEXIÓN
# =========================================================

try:
    conn = st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"],
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
    t = re.sub(r"^\d+[\.\-\s]*", "", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\.+$", "", t)
    return t.strip()



def df_from_res(res: Any) -> pd.DataFrame:
    return pd.DataFrame(res.data) if getattr(res, "data", None) else pd.DataFrame()



def clear_cache() -> None:
    st.cache_data.clear()



def _is_na(v: Any) -> bool:
    try:
        return pd.isna(v)
    except (ValueError, TypeError):
        return False


def safe_bool(v: Any) -> bool:
    if _is_na(v):
        return False
    return bool(v)



def safe_int(v: Any, default: int = 0) -> int:
    try:
        if _is_na(v):
            return default
        return int(v)
    except Exception:
        return default



def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if _is_na(v):
            return default
        return float(v)
    except Exception:
        return default



def safe_date_iso(v: Any) -> Optional[str]:
    try:
        if _is_na(v):
            return None
        return pd.to_datetime(v).date().isoformat()
    except Exception:
        return None



def rpc_call(name: str, params: Optional[Dict[str, Any]] = None, retries: int = 3) -> Any:
    """
    Llama a una función Postgres expuesta por Supabase vía REST:
    POST /rest/v1/rpc/<function_name>
    Reintenta automáticamente en errores transitorios (502, gateway, etc.).
    """
    base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
    api_key = st.secrets["connections"]["supabase"]["key"]

    url = f"{base_url}/rest/v1/rpc/{name}"

    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_exc: Optional[Exception] = None

    for attempt in range(retries):
        try:
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
                exc = RuntimeError(f"RPC {name} falló: {detail}")
                if attempt < retries - 1 and _is_transient_supabase_error(exc):
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise exc

            try:
                return response.json()
            except Exception:
                return None
        except requests.exceptions.ConnectionError as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise

    if last_exc is not None:
        raise last_exc
    return None



def detectar_csv(file_bytes: bytes) -> Tuple[str, str, str]:
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
        dialect = csv.Sniffer().sniff(muestra, delimiters=";,\t|")
        sep = dialect.delimiter
    except Exception:
        sep = ";"

    return text, encoding, sep



def leer_csv_preview(file_bytes: bytes, nrows: int = 200) -> Tuple[pd.DataFrame, str, str]:
    text, encoding, sep = detectar_csv(file_bytes)
    df = pd.read_csv(io.StringIO(text), sep=sep, nrows=nrows)
    return df, encoding, sep



def iter_csv_chunks(
    file_bytes: bytes, sep: str, encoding: str, chunksize: int = 20000
) -> Iterator[pd.DataFrame]:
    text = file_bytes.decode(encoding)
    buffer = io.StringIO(text)
    for chunk in pd.read_csv(buffer, sep=sep, chunksize=chunksize):
        yield chunk



def cargar_mapeo_guardado() -> Tuple[Dict[str, str], Optional[str], Optional[str]]:
    res = conn.table("config_importaciones_v2").select("*").eq("import_type", "ventas_diarias").execute()
    df = df_from_res(res)
    if df.empty:
        return {}, None, None

    row = df.iloc[0]
    mapping = row["mapping"] if isinstance(row["mapping"], dict) else {}
    return mapping, row.get("separator"), row.get("encoding")



def rpc_scalar(resp: Any, key: Optional[str] = None) -> Any:
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



def _is_transient_supabase_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    needles = [
        "502",
        "bad gateway",
        "cloudflare",
        "json could not be generated",
        "gateway",
        "tempor",
    ]
    return any(n in msg for n in needles)



def _query_existing_line_uids_chunk(sub: List[str], _depth: int = 0) -> List[Dict[str, Any]]:
    """
    Hace consultas pequeñas y, si Supabase devuelve 502/transient error,
    reintenta y divide el bloque en trozos aún más pequeños.
    Máximo 4 niveles de recursión para evitar bucles infinitos.
    """
    if not sub:
        return []

    last_exc: Optional[Exception] = None

    for attempt in range(3):
        try:
            res = (
                conn.table("ventas_raw_v2")
                .select("id,line_uid,payload_hash")
                .in_("line_uid", sub)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            last_exc = exc
            if attempt < 2 and _is_transient_supabase_error(exc):
                time.sleep(0.8 * (attempt + 1))
                continue
            break

    if len(sub) > 10 and _depth < 4:
        mid = len(sub) // 2
        return (
            _query_existing_line_uids_chunk(sub[:mid], _depth + 1)
            + _query_existing_line_uids_chunk(sub[mid:], _depth + 1)
        )

    if last_exc is not None:
        raise last_exc
    return []



def fetch_existing_by_line_uids(line_uids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Busca únicamente las líneas exactas que podrían existir ya en ventas_raw_v2.
    Usa bloques pequeños, reintentos y división automática del lote si Supabase
    devuelve errores 502 o similares.
    """
    if not line_uids:
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    lote = 40
    unique_line_uids = list(dict.fromkeys(line_uids))

    for i in range(0, len(unique_line_uids), lote):
        sub = unique_line_uids[i : i + lote]
        rows = _query_existing_line_uids_chunk(sub)

        for r in rows:
            out[r["line_uid"]] = {
                "id": r["id"],
                "payload_hash": r.get("payload_hash"),
            }

    return out



def prepare_rows_chunk(
    df_chunk: pd.DataFrame,
    mapping: Dict[str, str],
    file_name: str,
    start_row_num: int,
    ticket_state: Dict[str, int],
) -> Tuple[List[Dict[str, Any]], int, Dict[str, int]]:
    def val(row: pd.Series, key: str, default: str = "") -> str:
        src = mapping.get(key)
        if not src or src not in row.index:
            return default
        v = row[src]
        if pd.isna(v):
            return default
        return str(v).strip()

    rows: List[Dict[str, Any]] = []
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

        ticket_uid_raw = " | ".join(
            [fecha_raw, establecimiento_raw, caja_raw, serie_numero_raw]
        )

        line_idx = ticket_state.get(ticket_uid_raw, 0) + 1
        ticket_state[ticket_uid_raw] = line_idx

        line_uid = hashlib.md5(f"{ticket_uid_raw}|{line_idx}".encode("utf-8")).hexdigest()

        payload_string = "|".join(
            [
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
                neto_raw,
            ]
        )
        payload_hash = hashlib.md5(payload_string.encode("utf-8")).hexdigest()

        rows.append(
            {
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
            }
        )

    return rows, row_num, ticket_state



def analizar_csv_incremental(
    file_bytes: bytes,
    sep: str,
    encoding: str,
    mapping: Dict[str, str],
    file_name: str,
) -> Dict[str, int]:
    total_fisicas = 0
    total_unicas = 0
    total_nuevas = 0
    total_modificadas = 0
    total_iguales = 0

    ticket_state: Dict[str, int] = {}
    current_row_num = 0

    for chunk in iter_csv_chunks(file_bytes, sep=sep, encoding=encoding, chunksize=1000):
        total_fisicas += len(chunk)

        rows, current_row_num, ticket_state = prepare_rows_chunk(
            chunk, mapping, file_name, current_row_num, ticket_state
        )

        if not rows:
            continue

        df_rows = pd.DataFrame(rows).drop_duplicates(subset=["line_uid"], keep="last")
        total_unicas += len(df_rows)

        existing_map = fetch_existing_by_line_uids(df_rows["line_uid"].tolist())

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
        "a_subir": total_nuevas + total_modificadas,
    }



def reset_analisis_csv_si_cambia_archivo(file_bytes: bytes, file_name: str) -> None:
    file_sig = hashlib.md5(file_bytes).hexdigest()
    current_sig = f"{file_name}|{file_sig}"
    previous_sig = st.session_state.get("csv_upload_signature")

    if previous_sig != current_sig:
        st.session_state["csv_upload_signature"] = current_sig
        st.session_state.pop("analisis_subida_ventas", None)


@st.cache_data(ttl=60)
def cargar_local_id() -> Optional[int]:
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
            df["orden_visual"] = (
                pd.to_numeric(df["orden_visual"], errors="coerce").fillna(100).astype(int)
            )

        for col in [
            "activo",
            "es_vendible",
            "es_producible",
            "afecta_forecast",
            "visible_en_control_diario",
            "visible_en_forecast",
        ]:
            if col in df.columns:
                df[col] = df[col].fillna(False).astype(bool)

    return df


@st.cache_data(ttl=60)
def cargar_empleados_activos(local_id: int) -> pd.DataFrame:
    res = (
        conn.table("empleados_v2")
        .select("*")
        .eq("activo", True)
        .eq("local_id", local_id)
        .execute()
    )
    return df_from_res(res)



def fetch_paginated(
    table_name: str,
    columns: str = "*",
    filters: Optional[List[Dict[str, Any]]] = None,
    order_by: str = "id",
    page_size: int = 1000,
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    offset = 0
    _max_retries = 3

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

        data = None
        for _attempt in range(_max_retries):
            try:
                res = q.range(offset, offset + page_size - 1).execute()
                data = res.data or []
                break
            except Exception as exc:
                if _attempt < _max_retries - 1:
                    time.sleep(1 * (_attempt + 1))
                    continue
                detail = ""
                for attr in ["message", "details", "hint", "code"]:
                    val = getattr(exc, attr, None)
                    if val:
                        detail += f" | {attr}: {val}"
                st.error(
                    f"Error en consulta a '{table_name}' (offset={offset}, page_size={page_size}): "
                    f"{type(exc).__name__}: {exc}{detail}"
                )
                st.stop()

        rows.extend(data)

        if len(data) < page_size:
            break

        offset += page_size

        # Small pause every 10 pages to avoid connection exhaustion
        if (offset // page_size) % 10 == 0:
            time.sleep(0.5)

    return pd.DataFrame(rows)



def filtros_categoria_producto(
    df_dim: pd.DataFrame,
    key_prefix: str,
    solo_activos: bool = True,
    solo_control: bool = False,
    solo_forecast: bool = False,
) -> Tuple[List[str], List[str]]:
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
        key=f"{key_prefix}_categorias",
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
        key=f"{key_prefix}_productos",
    )

    return categorias_sel, productos_sel



def aplicar_filtros_df(
    df: pd.DataFrame,
    df_dim: pd.DataFrame,
    categorias_sel: List[str],
    productos_sel: List[str],
) -> pd.DataFrame:
    if df.empty:
        return df

    dim_cols = [
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
    ]
    dim_cols = [c for c in dim_cols if c in df_dim.columns]
    # Evitar columnas duplicadas al hacer merge
    cols_to_add = [c for c in dim_cols if c not in df.columns or c == "producto_id"]

    _dim_dedup = df_dim[cols_to_add].drop_duplicates(subset=["producto_id"])
    out = df.merge(_dim_dedup, on="producto_id", how="left")

    if categorias_sel:
        out = out[out["categoria_nombre"].isin(categorias_sel)]

    if productos_sel:
        out = out[out["producto_nombre"].isin(productos_sel)]

    return out



def cargar_ventas_rango(
    fecha_ini: datetime.date,
    fecha_fin: datetime.date,
    local_id: int,
) -> pd.DataFrame:
    # Split into 7-day windows to avoid connection drops on large ranges
    _all_frames: List[pd.DataFrame] = []
    _chunk_start = fecha_ini

    while _chunk_start <= fecha_fin:
        _chunk_end = min(_chunk_start + datetime.timedelta(days=6), fecha_fin)

        _chunk_df = fetch_paginated(
            "ventas_staging_v2",
            columns="id,batch_id,raw_id,row_num,fecha,hora,fecha_hora,ticket_uid,producto_id,uds_v,neto,estado_mapeo",
            filters=[
                {"op": "gte", "col": "fecha", "val": str(_chunk_start)},
                {"op": "lte", "col": "fecha", "val": str(_chunk_end)},
            ],
            order_by="fecha",
            page_size=1000,
        )
        if not _chunk_df.empty:
            _all_frames.append(_chunk_df)

        _chunk_start = _chunk_end + datetime.timedelta(days=1)
        if _chunk_start <= fecha_fin:
            time.sleep(0.3)

    if not _all_frames:
        return pd.DataFrame()

    df = pd.concat(_all_frames, ignore_index=True)

    # Normalize BEFORE dedup so identical rows with slightly different formats match
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
    df["uds_v"] = pd.to_numeric(df["uds_v"], errors="coerce").fillna(0)
    df["neto"] = pd.to_numeric(df["neto"], errors="coerce").fillna(0)
    if "hora" in df.columns:
        df["hora"] = df["hora"].astype(str).str.slice(0, 8)

    # Deduplicate: same CSV imported multiple times creates rows with different IDs
    # Use ticket_uid + row_num as primary dedup key (unique per CSV line)
    if "ticket_uid" in df.columns and "row_num" in df.columns:
        df = df.drop_duplicates(subset=["ticket_uid", "row_num"])
    else:
        _dedup_cols = ["fecha", "hora", "ticket_uid", "producto_id", "uds_v", "neto"]
        _dedup_cols = [c for c in _dedup_cols if c in df.columns]
        if _dedup_cols:
            df = df.drop_duplicates(subset=_dedup_cols)

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
        page_size=1000,
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
        page_size=1000,
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
        page_size=1000,
    )



def guardar_control_diario(payloads: List[Dict[str, Any]]) -> None:
    if not payloads:
        return

    for p in payloads:
        rpc_call(
            "rpc_upsert_control_diario",
            {
                "p_local_id": p["local_id"],
                "p_fecha": p["fecha"],
                "p_producto_id": p["producto_id"],
                "p_empleado_id": p["empleado_id"],
                "p_stock_inicial": p["stock_inicial"],
                "p_horneados": p["horneados"],
                "p_merma": p["merma"],
                "p_resto": p["resto"],
                "p_incidencias": p["incidencias"],
            },
        )


# =========================================================
# AUTENTICACIÓN
# =========================================================

TODAS_LAS_PANTALLAS = [
    "Productos",
    "Empleados",
    "Operativa",
    "BI",
    "Forecast",
    "Pendientes",
    "CargaVentas",
    "Auditoria",
]

PANTALLA_LABELS = {
    "Productos": "Productos",
    "Empleados": "Empleados",
    "Operativa": "Control Diario",
    "BI": "Historial / BI",
    "Forecast": "Forecast",
    "Pendientes": "Pendientes",
    "CargaVentas": "Subir CSV Ventas",
    "Auditoria": "Auditoría",
}


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def generar_password_temporal() -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(10))


def generar_whatsapp_link(telefono: str, nombre: str, email: str, password: str) -> str:
    msg = (
        f"Hola {nombre}! Tu cuenta en Tío Bigotes ha sido creada.\n\n"
        f"Email: {email}\n"
        f"Contraseña temporal: {password}\n\n"
        f"Deberás cambiarla en tu primer inicio de sesión."
    )
    phone = re.sub(r"[^\d+]", "", telefono)
    if not phone.startswith("+"):
        phone = f"+{phone}"
    return f"https://wa.me/{phone.lstrip('+')}?text={urllib.parse.quote(msg)}"


def registrar_actividad(accion: str, seccion: str, detalle: Optional[Dict[str, Any]] = None) -> None:
    """Registra una acción en el log de auditoría (fire-and-forget)."""
    user = st.session_state.get("auth_user")
    try:
        rpc_call(
            "rpc_registrar_actividad",
            {
                "p_user_id": user["id"] if user else None,
                "p_user_name": user["nombre"] if user else None,
                "p_user_email": user["email"] if user else None,
                "p_accion": accion,
                "p_seccion": seccion,
                "p_detalle": detalle or {},
            },
        )
    except Exception:
        pass  # No bloquear la app por fallos de auditoría


def get_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("auth_user")


def is_superadmin() -> bool:
    user = get_user()
    return user is not None and user.get("rol") == "superadmin"


def user_has_access(pantalla: str) -> bool:
    user = get_user()
    if not user:
        return False
    if user.get("rol") == "superadmin":
        return True
    permisos = user.get("permisos") or []
    return pantalla in permisos


def cerrar_sesion() -> None:
    registrar_actividad("logout", "Auth")
    st.session_state.pop("auth_user", None)
    st.session_state.pantalla = "Login"


def pantalla_login() -> None:
    _lc, _login_col, _rc = st.columns([1, 1.5, 1])
    with _login_col:
        st.markdown(
            '<div class="login-logo">🥟</div>'
            '<div class="login-title">Tío Bigotes</div>'
            '<div class="login-subtitle">Auténticas Empanadas Argentinas</div>',
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)

        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
        if st.button("🔑 Olvidé mi contraseña", use_container_width=True):
            st.session_state.pantalla = "RecuperarPassword"
            st.rerun()

        if submit and email.strip() and password:
            try:
                resp = rpc_call(
                    "rpc_verificar_login",
                    {"p_email": email.strip().lower(), "p_password_hash": hash_password(password)},
                )
                result = resp if isinstance(resp, dict) else (resp[0] if isinstance(resp, list) and resp else {})

                if result.get("ok"):
                    st.session_state["auth_user"] = {
                        "id": result["id"],
                        "nombre": result["nombre"],
                        "email": result["email"],
                        "telefono": result.get("telefono"),
                        "rol": result["rol"],
                        "must_change_password": result.get("must_change_password", False),
                        "permisos": result.get("permisos") or [],
                        "local_id": result.get("local_id"),
                    }
                    registrar_actividad("login", "Auth", {"email": email.strip().lower()})
                    if result.get("must_change_password"):
                        st.session_state.pantalla = "CambiarPassword"
                    else:
                        st.session_state.pantalla = "Home"
                    st.rerun()
                else:
                    st.error(result.get("error", "Error de autenticación"))
            except Exception as e:
                st.error(f"Error conectando: {e}")


def pantalla_cambiar_password(forzado: bool = False) -> None:
    user = get_user()
    if not user:
        st.session_state.pantalla = "Login"
        st.rerun()
        return

    st.title("🔐 Cambiar contraseña")
    if forzado:
        st.warning("Debes cambiar tu contraseña antes de continuar.")

    with st.form("cambiar_pwd_form"):
        old_pwd = st.text_input("Contraseña actual", type="password")
        new_pwd = st.text_input("Nueva contraseña", type="password")
        confirm_pwd = st.text_input("Confirmar nueva contraseña", type="password")
        submit = st.form_submit_button("Cambiar contraseña")

    if submit:
        if not old_pwd or not new_pwd:
            st.error("Completa todos los campos.")
        elif new_pwd != confirm_pwd:
            st.error("Las contraseñas no coinciden.")
        elif len(new_pwd) < 6:
            st.error("La contraseña debe tener al menos 6 caracteres.")
        else:
            try:
                resp = rpc_call(
                    "rpc_cambiar_password",
                    {
                        "p_user_id": user["id"],
                        "p_old_hash": hash_password(old_pwd),
                        "p_new_hash": hash_password(new_pwd),
                    },
                )
                result = resp if isinstance(resp, dict) else (resp[0] if isinstance(resp, list) and resp else {})

                if result.get("ok"):
                    registrar_actividad("cambio_password", "Auth")
                    st.session_state["auth_user"]["must_change_password"] = False
                    st.session_state.pantalla = "Home"
                    st.rerun()
                else:
                    st.error(result.get("error", "Error al cambiar contraseña"))
            except Exception as e:
                st.error(f"Error: {e}")


def pantalla_recuperar_password() -> None:
    st.title("🔑 Recuperar contraseña")
    st.info("Introduce tu email. Si existe, te mostraremos un enlace de WhatsApp para contactar al administrador.")

    with st.form("recuperar_form"):
        email = st.text_input("Email registrado")
        submit = st.form_submit_button("Solicitar recuperación")

    if st.button("⬅️ Volver al login"):
        st.session_state.pantalla = "Login"
        st.rerun()

    if submit and email.strip():
        try:
            res = (
                conn.table("empleados_v2")
                .select("id,nombre,telefono")
                .eq("email", email.strip().lower())
                .eq("activo", True)
                .execute()
            )
            df = df_from_res(res)

            if df.empty:
                st.error("No se encontró un usuario activo con ese email.")
            else:
                # Buscar al superadmin para enviarle mensaje
                res_admin = (
                    conn.table("empleados_v2")
                    .select("nombre,telefono")
                    .eq("rol", "superadmin")
                    .eq("activo", True)
                    .limit(1)
                    .execute()
                )
                df_admin = df_from_res(res_admin)

                user_name = df.iloc[0]["nombre"]

                if not df_admin.empty and df_admin.iloc[0].get("telefono"):
                    admin_phone = df_admin.iloc[0]["telefono"]
                    admin_name = df_admin.iloc[0]["nombre"]
                    msg = (
                        f"Hola {admin_name}, soy {user_name} ({email.strip()}).\n"
                        f"He olvidado mi contraseña de Tío Bigotes. "
                        f"¿Podrías resetearla por favor?"
                    )
                    phone = re.sub(r"[^\d+]", "", admin_phone)
                    if not phone.startswith("+"):
                        phone = f"+{phone}"
                    link = f"https://wa.me/{phone.lstrip('+')}?text={urllib.parse.quote(msg)}"

                    st.success(f"Contacta al administrador ({admin_name}) por WhatsApp para que resetee tu contraseña:")
                    st.markdown(f"[Enviar WhatsApp al administrador]({link})")
                else:
                    st.warning("No se encontró un administrador con WhatsApp configurado. Contacta a tu encargado directamente.")
        except Exception as e:
            st.error(f"Error: {e}")


# =========================================================
# ESTADO UI
# =========================================================

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "Login"



def ir_a(p: str) -> None:
    if p not in ("Login", "Home", "CambiarPassword", "RecuperarPassword"):
        registrar_actividad("navegar", p)
    st.session_state.pantalla = p


# =========================================================
# GATE DE AUTENTICACIÓN
# =========================================================

# Pantallas públicas (no requieren login)
if st.session_state.pantalla == "Login":
    pantalla_login()
    st.stop()

if st.session_state.pantalla == "RecuperarPassword":
    pantalla_recuperar_password()
    st.stop()

# A partir de aquí, requiere login
if not get_user():
    st.session_state.pantalla = "Login"
    st.rerun()

# Forzar cambio de contraseña
if get_user().get("must_change_password") and st.session_state.pantalla != "CambiarPassword":
    st.session_state.pantalla = "CambiarPassword"

if st.session_state.pantalla == "CambiarPassword":
    pantalla_cambiar_password(forzado=get_user().get("must_change_password", False))
    st.stop()


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
    _user = get_user()
    st.markdown(
        f"""<div class="tb-header">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h1>🥟 Tío Bigotes</h1>
                    <div class="tb-subtitle">📍 Diputació 159 &nbsp;|&nbsp; {datetime.date.today().strftime('%d/%m/%Y')}</div>
                </div>
                <div class="tb-user">
                    👤 {_user['nombre']} &nbsp;•&nbsp; {_user['rol']}
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
    _btn_l, _btn_r, _ = st.columns([1, 1, 4])
    with _btn_l:
        if st.button("🔑 Cambiar contraseña", use_container_width=True):
            st.session_state.pantalla = "CambiarPassword"
            st.rerun()
    with _btn_r:
        if st.button("🔒 Cerrar sesión", use_container_width=True):
            cerrar_sesion()
            st.rerun()

    _btn_config = {
        "Productos":   ("📦 PRODUCTOS",      "c1"),
        "Empleados":   ("👥 EMPLEADOS",       "c1"),
        "Operativa":   ("📋 CONTROL DIARIO",  "c2"),
        "BI":          ("📈 HISTORIAL / BI",  "c2"),
        "Forecast":    ("🧠 FORECAST",        "c3"),
        "Pendientes":  ("🧩 PENDIENTES",      "c3"),
        "CargaVentas": ("📥 SUBIR CSV VENTAS","c3"),
        "Auditoria":   ("📝 AUDITORÍA",       "c1"),
    }

    c1, c2, c3 = st.columns(3)
    _cols = {"c1": c1, "c2": c2, "c3": c3}

    for pantalla_key, (label, col_key) in _btn_config.items():
        if user_has_access(pantalla_key):
            with _cols[col_key]:
                if st.button(label):
                    ir_a(pantalla_key)


# =========================================================
# PRODUCTOS
# =========================================================

elif st.session_state.pantalla == "Productos":
    if not user_has_access("Productos"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
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
        "observaciones",
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
            "observaciones": st.column_config.TextColumn("Observaciones"),
        },
    )

    if st.button("💾 Guardar cambios de productos"):
        _save_ok = False
        try:
            # Solo enviar filas que el usuario realmente cambió
            df_changed = editado.loc[
                ~editado.apply(lambda r: r.equals(df_edit.loc[r.name]), axis=1)
            ] if not df_edit.empty else editado

            if df_changed.empty:
                st.info("No hay cambios que guardar.")
            else:
                for _, row in df_changed.iterrows():
                    rpc_call(
                        "rpc_actualizar_producto",
                        {
                            "p_id": int(row["producto_id"]),
                            "p_activo": safe_bool(row["activo"]),
                            "p_es_producible": safe_bool(row["es_producible"]),
                            "p_afecta_forecast": safe_bool(row["afecta_forecast"]),
                            "p_visible_en_control_diario": safe_bool(row["visible_en_control_diario"]),
                            "p_visible_en_forecast": safe_bool(row["visible_en_forecast"]),
                            "p_orden_visual": safe_int(row["orden_visual"], 100),
                            "p_uds_equivalentes_empanadas": safe_float(
                                row["uds_equivalentes_empanadas"], 0
                            ),
                            "p_fecha_inicio_venta": safe_date_iso(row["fecha_inicio_venta"]),
                            "p_fecha_fin_venta": safe_date_iso(row["fecha_fin_venta"]),
                            "p_observaciones": row["observaciones"]
                            if pd.notnull(row["observaciones"])
                            else None,
                        },
                    )

                registrar_actividad(
                    "editar_productos", "Productos",
                    {"productos_editados": len(df_changed)},
                )
                clear_cache()
                _save_ok = True
        except Exception as e:
            st.error(f"Error guardando productos: {e}")
        if _save_ok:
            st.rerun()

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
                eq_emp_nuevo = st.number_input(
                    "Equivalente empanadas", min_value=0.0, step=1.0, value=0.0
                )
                obs_nuevo = st.text_input("Observaciones")

                guardar_nuevo = st.form_submit_button("Crear producto")

                _create_ok = False
                if guardar_nuevo and nombre_nuevo.strip():
                    try:
                        cat_row = df_cat[df_cat["nombre"] == categoria_nueva].iloc[0]

                        rpc_call(
                            "rpc_crear_producto",
                            {
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
                                "p_observaciones": obs_nuevo if obs_nuevo else None,
                            },
                        )

                        registrar_actividad(
                            "crear_producto", "Productos",
                            {"nombre": nombre_nuevo.strip(), "categoria": categoria_nueva},
                        )
                        clear_cache()
                        _create_ok = True
                    except Exception as e:
                        st.error(f"Error creando producto: {e}")
                if _create_ok:
                    st.rerun()


# =========================================================
# EMPLEADOS
# =========================================================

elif st.session_state.pantalla == "Empleados":
    if not user_has_access("Empleados"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("👥 Gestión de Empleados")

    # Solo superadmin puede crear usuarios
    if is_superadmin():
        with st.expander("➕ Nuevo empleado"):
            with st.form("nuevo_empleado"):
                nombre = st.text_input("Nombre completo")
                email_nuevo = st.text_input("Email")
                telefono_nuevo = st.text_input("Teléfono móvil (con prefijo país, ej: +34600123456)")
                rol = st.selectbox("Rol", ["dependiente", "encargado", "supervisor", "superadmin"])

                st.write("**Permisos de acceso:**")
                _permisos_sel = {}
                _perm_cols = st.columns(3)
                for i, (pkey, plabel) in enumerate(PANTALLA_LABELS.items()):
                    with _perm_cols[i % 3]:
                        _permisos_sel[pkey] = st.checkbox(plabel, value=False, key=f"perm_new_{pkey}")

                guardar = st.form_submit_button("Crear empleado")

                _emp_ok = False
                _wa_link = None
                if guardar and nombre.strip() and email_nuevo.strip():
                    temp_pwd = generar_password_temporal()
                    permisos_list = [k for k, v in _permisos_sel.items() if v]

                    # Superadmin siempre tiene todos los permisos
                    if rol == "superadmin":
                        permisos_list = list(PANTALLA_LABELS.keys())

                    try:
                        resp = rpc_call(
                            "rpc_crear_empleado_v2",
                            {
                                "p_local_id": LOCAL_ID,
                                "p_nombre": nombre.strip(),
                                "p_email": email_nuevo.strip().lower(),
                                "p_telefono": telefono_nuevo.strip(),
                                "p_rol": rol,
                                "p_password_hash": hash_password(temp_pwd),
                                "p_permisos": permisos_list,
                                "p_fecha_alta": str(datetime.date.today()),
                            },
                        )
                        result = resp if isinstance(resp, dict) else (resp[0] if isinstance(resp, list) and resp else {})

                        if result.get("ok"):
                            registrar_actividad(
                                "crear_empleado", "Empleados",
                                {"nombre": nombre.strip(), "email": email_nuevo.strip().lower(), "rol": rol},
                            )
                            clear_cache()
                            if telefono_nuevo.strip():
                                _wa_link = generar_whatsapp_link(
                                    telefono_nuevo.strip(), nombre.strip(),
                                    email_nuevo.strip().lower(), temp_pwd,
                                )
                            _emp_ok = True
                        else:
                            st.error(result.get("error", "Error creando empleado"))
                    except Exception as e:
                        st.error(f"Error creando empleado: {e}")

                if _emp_ok:
                    st.success(f"Empleado creado. Contraseña temporal: **{temp_pwd}**")
                    if _wa_link:
                        st.markdown(f"[Enviar credenciales por WhatsApp]({_wa_link})")
                    st.info("El empleado deberá cambiar su contraseña en el primer login.")

    # Lista de empleados
    res_emp = (
        conn.table("empleados_v2")
        .select("id,nombre,email,telefono,rol,activo,permisos")
        .eq("local_id", LOCAL_ID)
        .order("activo", desc=True)
        .order("nombre")
        .execute()
    )
    df_emp = df_from_res(res_emp)

    if df_emp.empty:
        st.info("No hay empleados.")
    else:
        for _, row in df_emp.iterrows():
            c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
            c1.write(f"**{row['nombre']}**")
            c1.caption(f"{row.get('email', '')} | {row.get('telefono', '')}")
            c2.write(f"{row['rol']} | {'Activo' if row['activo'] else 'Inactivo'}")

            if is_superadmin() and row["activo"]:
                if c3.button("Permisos", key=f"perm_emp_{row['id']}"):
                    st.session_state[f"_edit_perm_{row['id']}"] = True

                if c4.button("Baja", key=f"baja_emp_{row['id']}"):
                    _baja_ok = False
                    try:
                        rpc_call(
                            "rpc_baja_empleado",
                            {
                                "p_id": int(row["id"]),
                                "p_fecha_baja": str(datetime.date.today()),
                            },
                        )
                        registrar_actividad(
                            "baja_empleado", "Empleados",
                            {"empleado_id": int(row["id"]), "nombre": row["nombre"]},
                        )
                        clear_cache()
                        _baja_ok = True
                    except Exception as e:
                        st.error(f"Error dando de baja: {e}")
                    if _baja_ok:
                        st.rerun()

            # Panel editar permisos inline
            if is_superadmin() and st.session_state.get(f"_edit_perm_{row['id']}"):
                current_perms = row.get("permisos") or []
                st.write(f"**Editar permisos de {row['nombre']}:**")
                _ep_cols = st.columns(4)
                _new_perms = {}
                for j, (pk, pl) in enumerate(PANTALLA_LABELS.items()):
                    with _ep_cols[j % 4]:
                        _new_perms[pk] = st.checkbox(
                            pl, value=(pk in current_perms),
                            key=f"ep_{row['id']}_{pk}",
                        )

                _ep_btn_cols = st.columns(3)
                if _ep_btn_cols[0].button("Guardar permisos", key=f"save_perm_{row['id']}"):
                    new_list = [k for k, v in _new_perms.items() if v]
                    _perm_ok = False
                    try:
                        rpc_call("rpc_actualizar_permisos", {"p_user_id": int(row["id"]), "p_permisos": new_list})
                        registrar_actividad(
                            "cambiar_permisos", "Empleados",
                            {"empleado_id": int(row["id"]), "nombre": row["nombre"], "permisos": new_list},
                        )
                        clear_cache()
                        _perm_ok = True
                    except Exception as e:
                        st.error(f"Error: {e}")
                    if _perm_ok:
                        st.session_state.pop(f"_edit_perm_{row['id']}", None)
                        st.rerun()

                if _ep_btn_cols[1].button("Resetear contraseña", key=f"reset_pwd_{row['id']}"):
                    new_pwd = generar_password_temporal()
                    _rst_ok = False
                    try:
                        rpc_call("rpc_reset_password", {"p_user_id": int(row["id"]), "p_new_hash": hash_password(new_pwd)})
                        registrar_actividad(
                            "reset_password", "Empleados",
                            {"empleado_id": int(row["id"]), "nombre": row["nombre"]},
                        )
                        _rst_ok = True
                    except Exception as e:
                        st.error(f"Error: {e}")
                    if _rst_ok:
                        st.success(f"Nueva contraseña temporal para {row['nombre']}: **{new_pwd}**")
                        if row.get("telefono"):
                            wa_link = generar_whatsapp_link(
                                row["telefono"], row["nombre"],
                                row.get("email", ""), new_pwd,
                            )
                            st.markdown(f"[Enviar por WhatsApp]({wa_link})")

                if _ep_btn_cols[2].button("Cancelar", key=f"cancel_perm_{row['id']}"):
                    st.session_state.pop(f"_edit_perm_{row['id']}", None)
                    st.rerun()

                st.divider()


# =========================================================
# OPERATIVA / CONTROL DIARIO
# =========================================================

elif st.session_state.pantalla == "Operativa":
    if not user_has_access("Operativa"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📋 Hoja de Control Diario")

    col1, col2 = st.columns(2)
    fecha_sel = col1.date_input("Fecha", value=datetime.date.today())

    df_emp = cargar_empleados_activos(LOCAL_ID)
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
        solo_forecast=False,
    )

    df_control_dim = DF_DIM.copy()
    df_control_dim = df_control_dim[
        (df_control_dim["activo"] == True)
        & (df_control_dim["visible_en_control_diario"] == True)
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

    dict_hoy: Dict[int, Dict[str, Any]] = {}
    if not df_hoy.empty:
        dict_hoy = {
            int(r["producto_id"]): {
                "stock_inicial": safe_float(r["stock_inicial"]),
                "horneados": safe_float(r["horneados"]),
                "merma": safe_float(r["merma"]),
                "resto": safe_float(r["resto"]),
                "incidencias": r.get("incidencias"),
            }
            for _, r in df_hoy.iterrows()
        }

    dict_ayer: Dict[int, float] = {}
    if not df_ayer.empty:
        dict_ayer = {
            int(r["producto_id"]): safe_float(r["resto"]) for _, r in df_ayer.iterrows()
        }

    filas: List[Dict[str, Any]] = []
    for _, p in df_control_dim.iterrows():
        pid = int(p["producto_id"])

        if pid in dict_hoy:
            base = dict_hoy[pid]
            filas.append(
                {
                    "producto_id": pid,
                    "categoria": p["categoria_nombre"],
                    "producto": p["producto_nombre"],
                    "stock_inicial": base["stock_inicial"],
                    "horneados": base["horneados"],
                    "merma": base["merma"],
                    "resto": base["resto"],
                    "incidencias": base.get("incidencias"),
                }
            )
        else:
            filas.append(
                {
                    "producto_id": pid,
                    "categoria": p["categoria_nombre"],
                    "producto": p["producto_nombre"],
                    "stock_inicial": dict_ayer.get(pid, 0),
                    "horneados": 0,
                    "merma": 0,
                    "resto": 0,
                    "incidencias": None,
                }
            )

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
            "incidencias": st.column_config.TextColumn("Incidencias"),
        },
    )

    st.divider()
    st.subheader("Registrar hornada")

    c_h1, c_h2, c_h3 = st.columns([2, 1, 1])
    with c_h1:
        producto_horno = st.selectbox("Producto", df_control_dim["producto_nombre"].tolist())
    with c_h2:
        cantidad_horno = st.number_input("Cantidad", min_value=1, step=1, value=12)
    with c_h3:
        st.write("")  # spacer
        if st.button("➕ Guardar hornada", use_container_width=True):
            _hornada_ok = False
            try:
                pid = int(
                    df_control_dim[df_control_dim["producto_nombre"] == producto_horno].iloc[0][
                        "producto_id"
                    ]
                )
                rpc_call(
                    "rpc_crear_hornada",
                    {
                        "p_local_id": LOCAL_ID,
                        "p_fecha": str(fecha_sel),
                        "p_fecha_hora": datetime.datetime.now().isoformat(),
                        "p_producto_id": pid,
                        "p_cantidad": float(cantidad_horno),
                        "p_empleado_id": empleado_id,
                        "p_notas": None,
                    },
                )
                registrar_actividad(
                    "registrar_hornada", "Operativa",
                    {"producto": producto_horno, "cantidad": int(cantidad_horno), "fecha": str(fecha_sel)},
                )
                clear_cache()
                _hornada_ok = True
            except Exception as e:
                st.error(f"Error registrando hornada: {e}")
            if _hornada_ok:
                st.rerun()

    df_hornadas = cargar_hornadas_fecha(fecha_sel, LOCAL_ID)
    if not df_hornadas.empty:
        df_hornadas["cantidad"] = pd.to_numeric(df_hornadas["cantidad"], errors="coerce").fillna(0)
        df_hornadas = df_hornadas.merge(
            DF_DIM[["producto_id", "producto_nombre"]],
            on="producto_id",
            how="left",
        )
        resumen_h = (
            df_hornadas.groupby("producto_nombre", as_index=False)["cantidad"]
            .sum()
            .sort_values("cantidad", ascending=False)
        )
        st.write("### Hornadas registradas hoy")
        st.dataframe(resumen_h, use_container_width=True, hide_index=True)

    if st.button("💾 Guardar control diario"):
        try:
            payloads: List[Dict[str, Any]] = []
            for _, row in editado.iterrows():
                payloads.append(
                    {
                        "local_id": LOCAL_ID,
                        "fecha": str(fecha_sel),
                        "producto_id": int(row["producto_id"]),
                        "empleado_id": empleado_id,
                        "stock_inicial": safe_float(row["stock_inicial"]),
                        "horneados": safe_float(row["horneados"]),
                        "merma": safe_float(row["merma"]),
                        "resto": safe_float(row["resto"]),
                        "incidencias": row["incidencias"] if pd.notnull(row["incidencias"]) else None,
                    }
                )

            guardar_control_diario(payloads)
            registrar_actividad(
                "guardar_control_diario", "Operativa",
                {"fecha": str(fecha_sel), "productos": len(payloads)},
            )
            clear_cache()
            st.success("✅ Control diario guardado")
        except Exception as e:
            st.error(f"Error guardando control diario: {e}")


# =========================================================
# BI / HISTORIAL
# =========================================================

elif st.session_state.pantalla == "BI":
    if not user_has_access("BI"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
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
        solo_forecast=False,
    )

    with st.spinner("Cargando ventas..."):
        df_sales = cargar_ventas_rango(fecha_ini, fecha_fin, LOCAL_ID)

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
        tickets=("ticket_uid", "nunique"),
    )

    fig_day = px.line(df_day, x="fecha", y="ventas", title="Ventas por día")
    st.plotly_chart(fig_day, use_container_width=True)

    df_prod = (
        df_sales.groupby(["producto_nombre", "categoria_nombre"], as_index=False)
        .agg(ventas=("neto", "sum"), unidades=("uds_v", "sum"))
        .sort_values("ventas", ascending=False)
        .head(20)
    )

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        fig_top = px.bar(
            df_prod,
            x="producto_nombre",
            y="ventas",
            color="categoria_nombre",
            title="Top productos por ventas",
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_g2:
        df_hour = df_sales.copy()
        df_hour["hora_num"] = pd.to_datetime(
            df_hour["hora"], format="%H:%M:%S", errors="coerce"
        ).dt.hour
        df_hour = (
            df_hour.groupby("hora_num", as_index=False)
            .agg(ventas=("neto", "sum"), unidades=("uds_v", "sum"))
            .sort_values("hora_num")
        )
        fig_hour = px.bar(df_hour, x="hora_num", y="ventas", title="Ventas por hora")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.write("### Detalle por producto")
    st.dataframe(df_prod, use_container_width=True, hide_index=True)

    # ── Análisis de Rentabilidad Horaria ──
    st.divider()
    st.write("### 💰 Análisis de Rentabilidad Horaria")
    st.caption("Análisis del ingreso neto por día de la semana y franja horaria para optimizar horarios de apertura.")

    df_rent = df_sales.copy()
    df_rent["hora_num"] = pd.to_datetime(
        df_rent["hora"], format="%H:%M:%S", errors="coerce"
    ).dt.hour
    df_rent["fecha_dt"] = pd.to_datetime(df_rent["fecha"])
    df_rent["dia_semana_num"] = df_rent["fecha_dt"].dt.dayofweek  # 0=lun ... 6=dom
    _dia_nombres = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    df_rent["dia_semana"] = df_rent["dia_semana_num"].map(_dia_nombres)

    if not df_rent.empty and "hora_num" in df_rent.columns:
        # Contar semanas únicas por día de la semana para promediar
        _semanas_por_dia = df_rent.groupby("dia_semana_num")["fecha_dt"].apply(
            lambda x: x.dt.isocalendar().week.nunique()
        ).to_dict()

        # Agrupar por día y hora
        df_dh = (
            df_rent.groupby(["dia_semana_num", "dia_semana", "hora_num"], as_index=False)
            .agg(venta_total=("neto", "sum"), unidades_total=("uds_v", "sum"), tickets=("ticket_uid", "nunique"))
        )

        # Calcular promedios semanales
        df_dh["semanas"] = df_dh["dia_semana_num"].map(_semanas_por_dia)
        df_dh["venta_media"] = (df_dh["venta_total"] / df_dh["semanas"]).round(2)
        df_dh["tickets_media"] = (df_dh["tickets"] / df_dh["semanas"]).round(1)

        # Parámetros de coste
        _rent_c1, _rent_c2, _rent_c3 = st.columns(3)
        with _rent_c1:
            salario_total = st.number_input("Salario mensual total (€)", value=5700.0, step=100.0, key="rent_salario")
        with _rent_c2:
            n_empleados = st.number_input("Empleados", value=3, min_value=1, step=1, key="rent_empleados")
        with _rent_c3:
            horas_semana_emp = st.number_input("Horas/semana por empleado", value=36.0, step=1.0, key="rent_horas")

        # Coste por hora de apertura (todas las personas presentes)
        horas_mes_totales = n_empleados * horas_semana_emp * 4.33
        coste_hora = salario_total / horas_mes_totales if horas_mes_totales > 0 else 0

        st.info(f"**Coste laboral por hora de apertura:** {coste_hora:.2f}€/h "
                f"({n_empleados} personas × {horas_semana_emp}h/sem × 4.33 sem/mes = {horas_mes_totales:.0f}h/mes)")

        # Marcar rentabilidad
        df_dh["coste_hora"] = coste_hora
        df_dh["beneficio_neto"] = df_dh["venta_media"] - coste_hora
        df_dh["rentable"] = df_dh["beneficio_neto"] > 0

        # Heatmap: venta media por día y hora
        _pivot_venta = df_dh.pivot_table(
            index="hora_num", columns="dia_semana", values="venta_media", aggfunc="sum"
        )
        # Reordenar columnas por día de semana
        _orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        _pivot_venta = _pivot_venta[[d for d in _orden_dias if d in _pivot_venta.columns]]

        fig_hm = px.imshow(
            _pivot_venta,
            labels=dict(x="Día", y="Hora", color="€ media/h"),
            title="Venta media por hora y día de la semana (€)",
            color_continuous_scale="RdYlGn",
            aspect="auto",
        )
        fig_hm.update_yaxes(dtick=1)
        st.plotly_chart(fig_hm, use_container_width=True)

        # Heatmap de beneficio neto (venta - coste laboral)
        _pivot_benef = df_dh.pivot_table(
            index="hora_num", columns="dia_semana", values="beneficio_neto", aggfunc="sum"
        )
        _pivot_benef = _pivot_benef[[d for d in _orden_dias if d in _pivot_benef.columns]]

        fig_benef = px.imshow(
            _pivot_benef,
            labels=dict(x="Día", y="Hora", color="€ beneficio/h"),
            title="Beneficio neto por hora (venta - coste laboral)",
            color_continuous_scale="RdYlGn",
            aspect="auto",
            zmin=-coste_hora,
        )
        fig_benef.update_yaxes(dtick=1)
        st.plotly_chart(fig_benef, use_container_width=True)

        # Recomendación de horarios
        st.write("### 📋 Recomendación de horarios")

        _horario_actual = {
            0: (8, 23),  # Lunes
            1: (8, 23),  # Martes
            2: (8, 23),  # Miércoles
            3: (8, 23),  # Jueves
            4: (8, 24),  # Viernes
            5: (9, 23),  # Sábado
            6: (9, 23),  # Domingo
        }

        _recomendaciones = []
        _ahorro_total = 0.0
        _perdida_total = 0.0

        for dia_num in range(7):
            dia_nombre = _dia_nombres[dia_num]
            df_dia = df_dh[df_dh["dia_semana_num"] == dia_num].copy()

            if df_dia.empty:
                _recomendaciones.append({
                    "Día": dia_nombre,
                    "Horario actual": "Sin datos",
                    "Horario recomendado": "Sin datos",
                    "Horas actuales": 0,
                    "Horas recomendadas": 0,
                    "Ahorro estimado (€/sem)": 0,
                })
                continue

            h_actual_ini, h_actual_fin = _horario_actual.get(dia_num, (8, 23))

            # Horas rentables (beneficio neto > 0)
            df_rentable = df_dia[df_dia["beneficio_neto"] > 0].sort_values("hora_num")

            if df_rentable.empty:
                rec_ini, rec_fin = h_actual_ini, h_actual_ini + 4  # mínimo 4h
            else:
                rec_ini = int(df_rentable["hora_num"].min())
                rec_fin = int(df_rentable["hora_num"].max()) + 1

                # No abrir antes de las 8 ni cerrar después de las 24
                rec_ini = max(rec_ini, 8)
                rec_fin = min(rec_fin, 24)

                # Mínimo 8h de apertura
                if (rec_fin - rec_ini) < 8:
                    # Expandir hacia las horas con más venta
                    while (rec_fin - rec_ini) < 8:
                        if rec_ini > 8:
                            rec_ini -= 1
                        elif rec_fin < 24:
                            rec_fin += 1
                        else:
                            break

            horas_actual = h_actual_fin - h_actual_ini
            horas_rec = rec_fin - rec_ini

            # Calcular ventas perdidas en horas recortadas
            horas_cortadas = set(range(h_actual_ini, h_actual_fin)) - set(range(rec_ini, rec_fin))
            venta_perdida = df_dia[df_dia["hora_num"].isin(horas_cortadas)]["venta_media"].sum()
            ahorro = len(horas_cortadas) * coste_hora - venta_perdida

            _ahorro_total += max(ahorro, 0)
            _perdida_total += venta_perdida

            _recomendaciones.append({
                "Día": dia_nombre,
                "Horario actual": f"{h_actual_ini}:30 - {h_actual_fin}:30",
                "Horario recomendado": f"{rec_ini}:00 - {rec_fin}:00",
                "Horas actuales": horas_actual,
                "Horas recomendadas": horas_rec,
                "Ahorro coste (€/sem)": round(len(horas_cortadas) * coste_hora, 2),
                "Venta perdida (€/sem)": round(venta_perdida, 2),
                "Beneficio neto (€/sem)": round(max(ahorro, 0), 2),
            })

        df_rec = pd.DataFrame(_recomendaciones)
        st.dataframe(df_rec, use_container_width=True, hide_index=True)

        _horas_actual_sem = sum(r["Horas actuales"] for r in _recomendaciones)
        _horas_rec_sem = sum(r["Horas recomendadas"] for r in _recomendaciones)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Horas/semana actual", f"{_horas_actual_sem}h")
        m2.metric("Horas/semana recomendadas", f"{_horas_rec_sem}h", delta=f"{_horas_rec_sem - _horas_actual_sem}h")
        m3.metric("Ahorro mensual estimado", f"{_ahorro_total * 4.33:.0f}€")
        m4.metric("Coste hora apertura", f"{coste_hora:.2f}€/h")

        # Detalle: tabla de venta media por hora y día
        st.write("### 📊 Tabla detallada: venta media por hora (€)")
        _pivot_detail = df_dh.pivot_table(
            index="hora_num", columns="dia_semana",
            values=["venta_media", "tickets_media"],
            aggfunc="sum",
        )
        _pivot_display = df_dh.pivot_table(
            index="hora_num", columns="dia_semana", values="venta_media", aggfunc="sum"
        ).fillna(0).round(2)
        _pivot_display = _pivot_display[[d for d in _orden_dias if d in _pivot_display.columns]]
        _pivot_display.index.name = "Hora"

        # Colorear filas por debajo del coste
        def _color_row(val):
            if val < coste_hora and val > 0:
                return "background-color: #FEE2E2"
            elif val >= coste_hora:
                return "background-color: #DCFCE7"
            return ""

        st.dataframe(
            _pivot_display.style.map(_color_row),
            use_container_width=True,
        )
        st.caption(f"🟢 Verde = venta > coste hora ({coste_hora:.2f}€) | 🔴 Rojo = venta < coste hora")


# =========================================================
# FORECAST
# =========================================================

elif st.session_state.pantalla == "Forecast":
    if not user_has_access("Forecast"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🧠 Forecast de Horneado")

    c1, c2, c3 = st.columns(3)
    fecha_pred = c1.date_input("Fecha objetivo", datetime.date.today())
    estrategia = c2.select_slider(
        "Estrategia",
        options=["Defensiva", "Equilibrada", "Agresiva"],
        value="Equilibrada",
    )
    es_festivo = c3.toggle("Festivo / Puente", value=False)

    st.subheader("Filtros")
    categorias_sel, productos_sel = filtros_categoria_producto(
        DF_DIM,
        key_prefix="forecast",
        solo_activos=True,
        solo_control=False,
        solo_forecast=True,
    )

    if st.button("🚀 Calcular forecast"):
        df_forecast_dim = DF_DIM.copy()
        df_forecast_dim = df_forecast_dim[
            (df_forecast_dim["activo"] == True)
            & (df_forecast_dim["visible_en_forecast"] == True)
            & (df_forecast_dim["afecta_forecast"] == True)
        ]

        fecha_pred_ts = pd.to_datetime(fecha_pred)

        if "fecha_inicio_venta" in df_forecast_dim.columns:
            df_forecast_dim["fecha_inicio_venta"] = pd.to_datetime(
                df_forecast_dim["fecha_inicio_venta"], errors="coerce"
            )
            df_forecast_dim = df_forecast_dim[
                df_forecast_dim["fecha_inicio_venta"].isna()
                | (df_forecast_dim["fecha_inicio_venta"] <= fecha_pred_ts)
            ]

        if "fecha_fin_venta" in df_forecast_dim.columns:
            df_forecast_dim["fecha_fin_venta"] = pd.to_datetime(
                df_forecast_dim["fecha_fin_venta"], errors="coerce"
            )
            df_forecast_dim = df_forecast_dim[
                df_forecast_dim["fecha_fin_venta"].isna()
                | (df_forecast_dim["fecha_fin_venta"] >= fecha_pred_ts)
            ]

        if categorias_sel:
            df_forecast_dim = df_forecast_dim[df_forecast_dim["categoria_nombre"].isin(categorias_sel)]
        if productos_sel:
            df_forecast_dim = df_forecast_dim[df_forecast_dim["producto_nombre"].isin(productos_sel)]

        if df_forecast_dim.empty:
            st.warning("No hay productos válidos para forecast con esos filtros.")
            st.stop()

        # Use 90 days of history (more relevant than 365)
        fecha_ini_hist = fecha_pred - datetime.timedelta(days=90)

        with st.spinner("Analizando histórico (últimos 90 días)..."):
            df_sales = cargar_ventas_rango(
                fecha_ini_hist,
                fecha_pred - datetime.timedelta(days=1),
                LOCAL_ID,
            )

        if df_sales.empty:
            st.warning("No hay histórico suficiente.")
            st.stop()

        df_sales = df_sales.merge(
            df_forecast_dim[["producto_id", "producto_nombre"]],
            on="producto_id",
            how="inner",
        )

        if df_sales.empty:
            st.warning("No hay ventas históricas para esos productos.")
            st.stop()

        df_daily = df_sales.groupby(["fecha", "producto_id", "producto_nombre"], as_index=False)[
            "uds_v"
        ].sum()
        df_daily["fecha"] = pd.to_datetime(df_daily["fecha"])
        objetivo_dow = fecha_pred.weekday()

        pct_map = {"Defensiva": 40, "Equilibrada": 60, "Agresiva": 80}
        pct = pct_map[estrategia]

        resultados: List[Dict[str, Any]] = []

        for _, p in df_forecast_dim.iterrows():
            pid = p["producto_id"]
            nombre = p["producto_nombre"]

            sub = df_daily[df_daily["producto_id"] == pid].copy()
            sub["dow"] = sub["fecha"].dt.weekday
            hist_same_dow = sub[sub["dow"] == objetivo_dow].copy()

            if hist_same_dow.empty:
                # Fallback: use all days
                if not sub.empty:
                    base = float(sub["uds_v"].median())
                else:
                    base = 0
            else:
                # Weight recent weeks more: last 4 weeks × 2, older × 1
                _cutoff = pd.Timestamp(fecha_pred - datetime.timedelta(days=28))
                recent = hist_same_dow[hist_same_dow["fecha"] >= _cutoff]["uds_v"]
                older = hist_same_dow[hist_same_dow["fecha"] < _cutoff]["uds_v"]

                if not recent.empty and not older.empty:
                    # Weighted: 70% recent avg, 30% older percentile
                    base = 0.7 * float(recent.mean()) + 0.3 * float(np.percentile(older, pct))
                elif not recent.empty:
                    base = float(recent.mean())
                else:
                    base = float(np.percentile(older, pct))

            if es_festivo:
                base *= 1.15

            total = int(np.ceil(base))
            if total > 0:
                resultados.append(
                    {
                        "Producto": nombre,
                        "Total sugerido": total,
                        "Tanda 1": int(np.ceil(total * 0.7)),
                        "Tanda 2": int(np.floor(total * 0.3)),
                    }
                )

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
            txt += (
                f"• {r['Producto']}: {r['Tanda 1']} + {r['Tanda 2']} = *{r['Total sugerido']}*\n"
            )

        st.text_area("Texto para WhatsApp", txt, height=300)


# =========================================================
# PENDIENTES
# =========================================================

elif st.session_state.pantalla == "Pendientes":
    if not user_has_access("Pendientes"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🧩 Artículos pendientes de mapear")

    res_pend = (
        conn.table("articulos_pendientes_v2")
        .select("*")
        .eq("estado", "pendiente")
        .order("veces_detectado", desc=True)
        .execute()
    )
    df_pend = df_from_res(res_pend)

    if df_pend.empty:
        st.success("✅ No quedan pendientes.")
        st.stop()

    st.dataframe(
        df_pend[
            [
                "articulo_raw_ejemplo",
                "alias_normalizado",
                "veces_detectado",
                "primera_fecha",
                "ultima_fecha",
            ]
        ],
        use_container_width=True,
        hide_index=True,
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
        _resolver_ok = False
        try:
            pid = int(DF_DIM[DF_DIM["producto_nombre"] == producto_destino].iloc[0]["producto_id"])

            rpc_call(
                "rpc_resolver_pendiente",
                {
                    "p_alias_normalizado": alias_sel,
                    "p_alias_raw": df_match["articulo_raw_ejemplo"],
                    "p_producto_id": pid,
                },
            )
            registrar_actividad(
                "resolver_pendiente", "Pendientes",
                {"alias": alias_sel, "producto_destino": producto_destino},
            )

            clear_cache()
            _resolver_ok = True
        except Exception as e:
            st.error(f"Error resolviendo pendiente: {e}")
        if _resolver_ok:
            st.rerun()

    if c2.button("🚫 Marcar como descartado"):
        _descartar_ok = False
        try:
            rpc_call(
                "rpc_descartar_pendiente",
                {
                    "p_alias_normalizado": alias_sel,
                    "p_nota": "Descartado manualmente desde Streamlit",
                },
            )
            registrar_actividad(
                "descartar_pendiente", "Pendientes",
                {"alias": alias_sel},
            )

            clear_cache()
            _descartar_ok = True
        except Exception as e:
            st.error(f"Error descartando pendiente: {e}")
        if _descartar_ok:
            st.rerun()


# =========================================================
# CARGA VENTAS CSV
# =========================================================

elif st.session_state.pantalla == "CargaVentas":
    if not user_has_access("CargaVentas"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📥 Subida incremental de CSV de ventas")

    st.info(
        "Guarda el mapeo de columnas y, en cada nueva subida, "
        "solo inserta líneas nuevas o sobrescribe líneas modificadas."
    )

    archivo = st.file_uploader("Sube el CSV de ventas", type=["csv"])

    if archivo is not None:
        file_bytes = archivo.getvalue()
        reset_analisis_csv_si_cambia_archivo(file_bytes, archivo.name)

        try:
            df_preview, encoding_detectado, sep_detectado = leer_csv_preview(file_bytes, nrows=200)
            st.success(f"CSV leído | Separador: '{sep_detectado}' | Encoding: {encoding_detectado}")
        except Exception as e:
            st.error(f"No pude leer el CSV: {e}")
            st.stop()

        mapping_guardado, _, _ = cargar_mapeo_guardado()
        columnas = list(df_preview.columns)

        st.write("### Preview")
        st.dataframe(df_preview.head(20), use_container_width=True)

        st.write("### Mapeo de columnas")
        campos = {
            "column1": "Column1 (opcional)",
            "fecha": "Fecha",
            "hora": "Hora",
            "serie_numero": "Serie / Número",
            "establecimiento": "Establecimiento",
            "caja": "Caja",
            "numero": "Número empleado POS (opcional)",
            "cliente": "Cliente (opcional)",
            "empleado": "Empleado (opcional)",
            "uds_v": "Uds.V",
            "articulo": "Artículo",
            "subarticulo": "Subartículo (opcional)",
            "base": "Base",
            "impuestos": "Impuestos",
            "dto_total": "Dto",
            "neto": "Total Neto",
        }

        cols = st.columns(3)
        mapping: Dict[str, str] = {}

        for i, (key, label) in enumerate(campos.items()):
            default_value = mapping_guardado.get(key)
            options = [""] + columnas
            default_index = options.index(default_value) if default_value in options else 0

            with cols[i % 3]:
                mapping[key] = st.selectbox(
                    label,
                    options,
                    index=default_index,
                    key=f"csv_map_{key}",
                )

        obligatorios = [
            "fecha",
            "hora",
            "serie_numero",
            "establecimiento",
            "caja",
            "uds_v",
            "articulo",
            "base",
            "impuestos",
            "dto_total",
            "neto",
        ]
        mapeo_valido = all(mapping.get(k) for k in obligatorios)

        c1, c2 = st.columns(2)

        if c1.button("💾 Guardar mapeo"):
            try:
                rpc_call(
                    "rpc_save_import_mapping",
                    {
                        "p_import_type": "ventas_diarias",
                        "p_mapping": mapping,
                        "p_separator": sep_detectado,
                        "p_encoding": encoding_detectado,
                    },
                )
                registrar_actividad("guardar_mapeo", "CargaVentas")
                st.success("✅ Mapeo guardado")
            except Exception as e:
                st.error(f"Error guardando mapeo: {e}")

        if not mapeo_valido:
            st.warning("Completa todos los campos obligatorios.")
            st.stop()

        if c2.button("🔍 Analizar subida"):
            try:
                resumen = analizar_csv_incremental(
                    file_bytes=file_bytes,
                    sep=sep_detectado,
                    encoding=encoding_detectado,
                    mapping=mapping,
                    file_name=archivo.name,
                )

                st.session_state["analisis_subida_ventas"] = {
                    "mapping": mapping,
                    "sep": sep_detectado,
                    "encoding": encoding_detectado,
                    "file_name": archivo.name,
                    "resumen": resumen,
                }

                st.success("✅ Análisis completado")
            except Exception as e:
                st.error(f"Error analizando subida: {e}")

        analisis = st.session_state.get("analisis_subida_ventas")

        if analisis:
            resumen = analisis["resumen"]

            st.write("### Resultado del análisis")
            a1, a2, a3, a4, a5, a6 = st.columns(6)
            a1.metric("Líneas físicas CSV", f"{resumen['total_fisicas']:,}")
            a2.metric("Líneas únicas CSV", f"{resumen['total_unicas']:,}")
            a3.metric("Nuevas", f"{resumen['nuevas']:,}")
            a4.metric("Modificadas", f"{resumen['modificadas']:,}")
            a5.metric("Sin cambios", f"{resumen['iguales']:,}")
            a6.metric("Se subirán", f"{resumen['a_subir']:,}")

            if st.button("🚀 Subir ventas"):
                try:
                    rpc_call(
                        "rpc_save_import_mapping",
                        {
                            "p_import_type": "ventas_diarias",
                            "p_mapping": analisis["mapping"],
                            "p_separator": analisis["sep"],
                            "p_encoding": analisis["encoding"],
                        },
                    )

                    batch_resp = rpc_call(
                        "rpc_crear_import_batch",
                        {
                            "p_local_id": LOCAL_ID,
                            "p_nombre_archivo": analisis["file_name"],
                            "p_tipo_import": "ventas_diarias",
                        },
                    )
                    batch_id = int(rpc_scalar(batch_resp))

                    total_fisicas = 0
                    total_unicas = 0
                    total_insertadas = 0
                    total_actualizadas = 0
                    total_iguales = 0
                    total_subidas = 0

                    ticket_state: Dict[str, int] = {}
                    current_row_num = 0
                    all_line_uids_from_file: List[str] = []

                    with st.spinner("Subiendo..."):
                        for chunk in iter_csv_chunks(
                            file_bytes,
                            sep=analisis["sep"],
                            encoding=analisis["encoding"],
                            chunksize=1000,
                        ):
                            total_fisicas += len(chunk)

                            rows, current_row_num, ticket_state = prepare_rows_chunk(
                                chunk,
                                analisis["mapping"],
                                analisis["file_name"],
                                current_row_num,
                                ticket_state,
                            )

                            if not rows:
                                continue

                            df_rows = pd.DataFrame(rows).drop_duplicates(
                                subset=["line_uid"], keep="last"
                            )
                            total_unicas += len(df_rows)

                            existing_map = fetch_existing_by_line_uids(df_rows["line_uid"].tolist())

                            rows_to_write: List[Dict[str, Any]] = []

                            for _, r in df_rows.iterrows():
                                all_line_uids_from_file.append(r["line_uid"])
                                old = existing_map.get(r["line_uid"])

                                if old is None:
                                    total_insertadas += 1
                                    rows_to_write.append(r.to_dict())
                                elif old["payload_hash"] != r["payload_hash"]:
                                    d = r.to_dict()
                                    d["existing_id"] = old["id"]
                                    total_actualizadas += 1
                                    rows_to_write.append(d)
                                else:
                                    total_iguales += 1

                            if rows_to_write:
                                written_ids: List[int] = []
                                _upsert_batch_size = 250
                                for _ub_i in range(0, len(rows_to_write), _upsert_batch_size):
                                    _ub_slice = rows_to_write[_ub_i : _ub_i + _upsert_batch_size]
                                    resp = rpc_call(
                                        "rpc_upsert_ventas_raw_batch",
                                        {"p_batch_id": batch_id, "p_rows": _ub_slice},
                                    )

                                    if isinstance(resp, dict):
                                        written_ids.extend(resp.get("written_ids", []))
                                    elif isinstance(resp, list) and resp:
                                        first = resp[0]
                                        if isinstance(first, dict):
                                            written_ids.extend(first.get("written_ids", []))

                                total_subidas += len(rows_to_write)

                                if written_ids:
                                    lote = 1000
                                    for i in range(0, len(written_ids), lote):
                                        rpc_call(
                                            "rpc_sync_staging_by_raw_ids",
                                            {"p_raw_ids": written_ids[i : i + lote]},
                                        )

                    unique_line_uids = list(set(all_line_uids_from_file))
                    verificados = len(fetch_existing_by_line_uids(unique_line_uids))

                    filas_error = len(unique_line_uids) - verificados
                    estado = "ok" if filas_error == 0 else "error_parcial"

                    rpc_call(
                        "rpc_finalizar_import_batch",
                        {
                            "p_batch_id": batch_id,
                            "p_filas_totales": len(unique_line_uids),
                            "p_filas_ok": verificados,
                            "p_filas_error": filas_error,
                            "p_estado": estado,
                        },
                    )

                    registrar_actividad(
                        "subir_ventas_csv", "CargaVentas",
                        {
                            "archivo": analisis["file_name"],
                            "insertadas": total_insertadas,
                            "actualizadas": total_actualizadas,
                            "sin_cambios": total_iguales,
                            "estado": estado,
                        },
                    )

                    st.success("✅ Subida completada")

                    r1, r2, r3, r4, r5, r6 = st.columns(6)
                    r1.metric("Líneas únicas CSV", f"{len(unique_line_uids):,}")
                    r2.metric("Insertadas", f"{total_insertadas:,}")
                    r3.metric("Actualizadas", f"{total_actualizadas:,}")
                    r4.metric("Sin cambios", f"{total_iguales:,}")
                    r5.metric("Subidas reales", f"{total_subidas:,}")
                    r6.metric("Verificadas en BD", f"{verificados:,}")

                    if filas_error == 0:
                        st.success(
                            "✅ Verificación correcta: la base contiene exactamente las líneas esperadas."
                        )
                    else:
                        st.error(
                            f"❌ Verificación incompleta: faltan {filas_error} líneas por confirmar."
                        )

                    clear_cache()
                    st.session_state.pop("analisis_subida_ventas", None)

                except Exception as e:
                    st.error(f"Error en la subida: {e}")


# =========================================================
# AUDITORÍA
# =========================================================

elif st.session_state.pantalla == "Auditoria":
    if not is_superadmin():
        st.error("Solo el superadmin puede ver la auditoría.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📝 Registro de Auditoría")

    _au_c1, _au_c2, _au_c3 = st.columns(3)
    with _au_c1:
        au_desde = st.date_input("Desde", value=datetime.date.today() - datetime.timedelta(days=7), key="au_desde")
    with _au_c2:
        au_hasta = st.date_input("Hasta", value=datetime.date.today(), key="au_hasta")
    with _au_c3:
        au_seccion = st.selectbox(
            "Sección",
            ["Todas"] + list(PANTALLA_LABELS.values()) + ["Auth"],
            key="au_seccion",
        )

    # Map display label back to internal key
    _seccion_filter = None
    if au_seccion != "Todas":
        # Check if it's an internal key already (like "Auth")
        if au_seccion in (list(PANTALLA_LABELS.keys()) + ["Auth"]):
            _seccion_filter = au_seccion
        else:
            # Reverse lookup from label to key
            _rev = {v: k for k, v in PANTALLA_LABELS.items()}
            _seccion_filter = _rev.get(au_seccion, au_seccion)

    try:
        _au_params: Dict[str, Any] = {
            "p_limit": 200,
            "p_offset": 0,
            "p_desde": f"{au_desde}T00:00:00Z",
            "p_hasta": f"{au_hasta}T23:59:59Z",
        }
        if _seccion_filter:
            _au_params["p_seccion"] = _seccion_filter

        _au_resp = rpc_call("rpc_obtener_audit_log", _au_params)

        if isinstance(_au_resp, list) and _au_resp:
            # Handle nested response
            if isinstance(_au_resp[0], list):
                _au_data = _au_resp[0]
            else:
                _au_data = _au_resp
        else:
            _au_data = []

        if _au_data:
            df_audit = pd.DataFrame(_au_data)
            df_audit["ts"] = pd.to_datetime(df_audit["ts"]).dt.strftime("%d/%m/%Y %H:%M:%S")
            df_audit = df_audit.rename(columns={
                "ts": "Fecha/Hora",
                "user_name": "Usuario",
                "user_email": "Email",
                "accion": "Acción",
                "seccion": "Sección",
                "detalle": "Detalle",
            })
            cols_show = ["Fecha/Hora", "Usuario", "Email", "Acción", "Sección", "Detalle"]
            cols_show = [c for c in cols_show if c in df_audit.columns]

            st.dataframe(df_audit[cols_show], use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(df_audit)} registros")
        else:
            st.info("No hay registros de auditoría para los filtros seleccionados.")

    except Exception as e:
        st.error(f"Error cargando auditoría: {e}")

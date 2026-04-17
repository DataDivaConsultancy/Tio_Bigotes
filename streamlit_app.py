# -*- coding: utf-8 -*-
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

st.set_page_config(
    page_title="Tío Bigotes Pro",
    page_icon="TB",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_VERSION = "Compras-v2 · 2026-04-16"


# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

st.set_page_config(
    page_title="Tío Bigotes Pro",
    page_icon="🥟",
    layout="wide",
    initial_sidebar_state="collapsed",
)

APP_VERSION = "Compras-v2 · 2026-04-16"

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
}
</style>
""", unsafe_allow_html=True)

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


def compras_v2_ready() -> bool:
    try:
        conn.table("proveedores_v2").select("id").limit(1).execute()
        return True
    except Exception:
        return False



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


DIAS_SEMANA = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}


def normalizar_header_csv(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("utf-8")
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return re.sub(r"_+", "_", t).strip("_")


def parse_dia_semana(value: Any) -> Optional[int]:
    if _is_na(value):
        return None

    txt = str(value).strip()
    if not txt:
        return None

    if txt.isdigit():
        num = int(txt)
        return num if 1 <= num <= 7 else None

    normalized = normalizar_header_csv(txt)
    aliases = {
        "lunes": 1,
        "martes": 2,
        "miercoles": 3,
        "miércoles": 3,
        "jueves": 4,
        "viernes": 5,
        "sabado": 6,
        "sábado": 6,
        "domingo": 7,
    }
    return aliases.get(normalized)


def parse_decimal_or_none(v: Any) -> Optional[float]:
    if _is_na(v):
        return None
    t = str(v).strip().replace(",", ".")
    if not t:
        return None
    try:
        return float(t)
    except Exception:
        return None


def cargar_productos_compra() -> pd.DataFrame:
    try:
        res = (
            conn.table("productos_compra_v2")
            .select("*,proveedores_v2(id,nombre_comercial)")
            .order("nombre")
            .execute()
        )
        return df_from_res(res)
    except Exception:
        return pd.DataFrame()


def cargar_proveedores_compra() -> pd.DataFrame:
    try:
        res = conn.table("proveedores_v2").select("*").order("nombre_comercial").execute()
        return df_from_res(res)
    except Exception:
        return pd.DataFrame()


def upsert_proveedor_compra(row: Dict[str, Any], proveedor_id: Optional[int] = None) -> None:
    forma_pago = str(row.get("forma_pago") or "").strip()
    formas_validas = {"SEPA", "Transferencia", "T. Credito", "Efectivo"}
    if forma_pago and forma_pago not in formas_validas:
        raise ValueError("Forma de pago inválida.")

    payload = {
        "nombre_comercial": str(row.get("nombre_comercial") or "").strip(),
        "razon_social": str(row.get("razon_social") or "").strip(),
        "cif": str(row.get("cif") or "").strip() or None,
        "domicilio": str(row.get("domicilio") or "").strip() or None,
        "persona_contacto": str(row.get("persona_contacto") or "").strip() or None,
        "telefono_contacto": str(row.get("telefono_contacto") or "").strip() or None,
        "mail_contacto": str(row.get("mail_contacto") or "").strip() or None,
        "forma_pago": forma_pago or None,
        "plazo_pago": str(row.get("plazo_pago") or "").strip() or None,
        "notas": str(row.get("notas") or "").strip() or None,
        "activo": safe_bool(row.get("activo")),
    }

    if not payload["nombre_comercial"] or not payload["razon_social"]:
        raise ValueError("Nombre comercial y razón social son obligatorios.")

    table = conn.table("proveedores_v2")
    if proveedor_id:
        table.update(payload).eq("id", int(proveedor_id)).execute()
    else:
        table.insert(payload).execute()


def cargar_locales_compra() -> pd.DataFrame:
    try:
        res = conn.table("locales_compra_v2").select("*").order("nombre").execute()
        return df_from_res(res)
    except Exception:
        return pd.DataFrame()


def upsert_local_compra(row: Dict[str, Any], local_id: Optional[int] = None) -> None:
    payload = {
        "nombre": str(row.get("nombre") or "").strip(),
        "direccion": str(row.get("direccion") or "").strip() or None,
        "telefono": str(row.get("telefono") or "").strip() or None,
        "transporte": str(row.get("transporte") or "").strip() or None,
        "activo": safe_bool(row.get("activo")),
    }
    if not payload["nombre"]:
        raise ValueError("El nombre del local es obligatorio.")

    table = conn.table("locales_compra_v2")
    if local_id:
        table.update(payload).eq("id", int(local_id)).execute()
    else:
        table.insert(payload).execute()


def cargar_stock_compra() -> pd.DataFrame:
    try:
        res = conn.table("vw_stock_actual").select("*").order("stock_actual").execute()
        return df_from_res(res)
    except Exception:
        return pd.DataFrame()


def upsert_stock_compra(row: Dict[str, Any]) -> None:
    local_id = safe_int(row.get("local_id"), 0)
    producto_id = safe_int(row.get("producto_id"), 0)
    if not local_id or not producto_id:
        raise ValueError("Local y producto son obligatorios.")

    payload = {
        "producto_compra_id": producto_id,
        "local_id": local_id,
        "tipo": str(row.get("tipo") or "ajuste_positivo"),
        "cantidad": abs(safe_float(row.get("cantidad"), 0)),
        "motivo": str(row.get("motivo") or "").strip() or None,
        "fecha": str(row.get("fecha") or datetime.date.today()),
        "usuario_id": get_user()["id"] if get_user() else None,
        "local_destino_id": safe_int(row.get("local_destino_id"), 0) or None,
    }
    conn.table("stock_movimientos_v2").insert(payload).execute()


def _weekday_from_text(t: str) -> Optional[int]:
    if not t:
        return None
    n = normalizar_header_csv(t.split(",")[0])
    m = {
        "lunes": 1,
        "martes": 2,
        "miercoles": 3,
        "jueves": 4,
        "viernes": 5,
        "sabado": 6,
        "domingo": 7,
    }
    return m.get(n)


def calcular_lead_time_dias(dia_pedido: Optional[str], dia_entrega: Optional[str]) -> int:
    d1 = _weekday_from_text(dia_pedido or "")
    d2 = _weekday_from_text(dia_entrega or "")
    if not d1 or not d2:
        return 2
    return ((d2 - d1) % 7) + 1


def preparar_csv_productos_compra(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    rename_map = {c: normalizar_header_csv(c) for c in df.columns}
    df = df.rename(columns=rename_map)

    aliases = {
        "codigo_referencia_de_proveedor": "cod_proveedor",
        "codigo_referencia_proveedor": "cod_proveedor",
        "ref_proveedor": "cod_proveedor",
        "codigo_referencia_nuestro": "cod_interno",
        "ref_nuestro": "cod_interno",
        "nombre_de_producto": "nombre",
        "unidad_de_medida": "unidad_medida",
        "unidad_de_medida_minima_de_compra": "unidad_minima_compra",
        "dia_de_pedido": "dia_pedido",
        "dia_pedido_numero": "dia_pedido",
        "dia_de_entrega": "dia_entrega",
        "dia_entrega_numero": "dia_entrega",
        "tipo_de_iva": "tipo_iva",
    }
    df = df.rename(columns={c: aliases.get(c, c) for c in df.columns})

    expected_cols = [
        "cod_proveedor",
        "cod_interno",
        "nombre",
        "medidas",
        "color",
        "unidad_medida",
        "unidad_minima_compra",
        "dia_pedido",
        "dia_entrega",
        "proveedor",
        "precio",
        "tipo_iva",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    return df[expected_cols]


def upsert_producto_compra(row: Dict[str, Any], product_id: Optional[int] = None) -> None:
    payload = {
        "cod_proveedor": str(row.get("cod_proveedor") or "").strip() or None,
        "cod_interno": str(row.get("cod_interno") or "").strip() or None,
        "nombre": str(row.get("nombre") or "").strip(),
        "medidas": str(row.get("medidas") or "").strip() or None,
        "color": str(row.get("color") or "").strip() or None,
        "unidad_medida": str(row.get("unidad_medida") or "").strip() or None,
        "unidad_minima_compra": parse_decimal_or_none(row.get("unidad_minima_compra")),
        "dia_pedido": str(row.get("dia_pedido") or "").strip() or None,
        "dia_entrega": str(row.get("dia_entrega") or "").strip() or None,
        "proveedor_id": safe_int(row.get("proveedor_id"), 0) or None,
        "precio": parse_decimal_or_none(row.get("precio")),
        "tipo_iva": str(row.get("tipo_iva") or "").strip() or None,
        "forma_pago": str(row.get("forma_pago") or "").strip() or None,
        "plazo_pago": str(row.get("plazo_pago") or "").strip() or None,
        "producto_venta_id": safe_int(row.get("producto_venta_id"), 0) or None,
        "stock_minimo": parse_decimal_or_none(row.get("stock_minimo")) or 0,
        "activo": safe_bool(row.get("activo")),
    }

    if not payload["nombre"]:
        raise ValueError("El nombre del producto es obligatorio.")

    table = conn.table("productos_compra_v2")
    if product_id:
        table.update(payload).eq("id", int(product_id)).execute()
    else:
        table.insert(payload).execute()


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
def _guardar_control_diario_batch(payloads):
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
    "Proveedores",
    "ProductosCompra",
    "Locales",
    "Stock",
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
    "Proveedores": "Proveedores",
    "ProductosCompra": "Productos Compra",
    "Locales": "Locales",
    "Stock": "Stock",
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
    rol = str(user.get("rol") if user else "").strip().lower()
    return user is not None and rol == "superadmin"


def user_has_access(pantalla: str) -> bool:
    user = get_user()
    if not user:
        return False
    if user.get("rol") == "superadmin":
    rol = str(user.get("rol") or "").strip().lower()
    if rol == "superadmin":
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
        sst.markdown(
    '<div class="login-logo">&#x1F95F;</div>'
    '<div class="login-title">Tío Bigotes</div>'
    '<div class="login-subtitle">Auténticas Empanadas Argentinas</div>',
    unsafe_allow_html=True,
)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar", use_container_width=True)

        st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
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
    _compras_ready = compras_v2_ready()
   st.markdown(
    f"""<div class="tb-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h1>&#x1F95F; Tío Bigotes</h1>
                <div class="tb-subtitle">DIP159 &nbsp;|&nbsp; {datetime.date.today().strftime('%d/%m/%Y')}</div>
            </div>
            <div class="tb-user">
                User: {_user['nombre']} &nbsp;|&nbsp; {_user['rol']}
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)
    _btn_l, _btn_r, _ = st.columns([1, 1, 4])
    st.caption(f"Versión app: {APP_VERSION}")
    if not _compras_ready:
        st.warning("Módulo Compras v2 no inicializado en esta base. Ejecuta `sql_migration_compras_productos.sql`.")
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
        "Proveedores": ("🏭 PROVEEDORES",   "c1"),
        "ProductosCompra": ("🛒 PRODUCTOS COMPRA", "c1"),
        "Locales": ("🏪 LOCALES", "c2"),
        "Stock": ("📦 STOCK", "c2"),
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



def _supabase_get(table, params="", select="*"):
    """Helper GET genérico para tablas Supabase REST API."""
    try:
        base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
        api_key = st.secrets["connections"]["supabase"]["key"]
        headers = {"apikey": api_key, "Authorization": f"Bearer {api_key}"}
        url = f"{base_url}/rest/v1/{table}?select={select}"
        if params:
            url += f"&{params}"
        resp = requests.get(url, headers=headers, timeout=15)
        return resp.json() if resp.ok else []
    except Exception:
        return []


# =========================================================
# MÓDULO DE COMPRAS
# =========================================================

elif st.session_state.pantalla == "Proveedores":
    if not user_has_access("Proveedores"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🏭 Proveedores")

    if "prov_modo" not in st.session_state:
        st.session_state.prov_modo = "lista"
    if "prov_edit_id" not in st.session_state:
        st.session_state.prov_edit_id = None

    FORMAS_PAGO = ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"]

    col_a, _ = st.columns([1, 5])
    with col_a:
        if st.button("➕ Nuevo proveedor", use_container_width=True):
            st.session_state.prov_modo = "nuevo"
            st.session_state.prov_edit_id = None
            st.rerun()

    if st.session_state.prov_modo in ("nuevo", "editar"):
        es_edicion = st.session_state.prov_modo == "editar"
        st.subheader("✏️ Editar proveedor" if es_edicion else "➕ Nuevo proveedor")
        datos = {}
        if es_edicion and st.session_state.prov_edit_id:
            rows = _supabase_get("proveedores_v2", f"id=eq.{st.session_state.prov_edit_id}")
            if rows:
                datos = rows[0]

        with st.form("form_proveedor", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                nombre_comercial = st.text_input("Nombre comercial *", value=datos.get("nombre_comercial", ""))
                cif = st.text_input("CIF", value=datos.get("cif", ""))
                persona_contacto = st.text_input("Persona de contacto", value=datos.get("persona_contacto", ""))
                mail_contacto = st.text_input("Email contacto", value=datos.get("mail_contacto", ""))
                forma_pago = st.selectbox("Forma de pago", FORMAS_PAGO,
                    index=FORMAS_PAGO.index(datos.get("forma_pago", "")) if datos.get("forma_pago", "") in FORMAS_PAGO else 0)
            with c2:
                razon_social = st.text_input("Razón social", value=datos.get("razon_social", ""))
                domicilio = st.text_input("Domicilio", value=datos.get("domicilio", ""))
                telefono_contacto = st.text_input("Teléfono contacto", value=datos.get("telefono_contacto", ""))
                mail_pedidos = st.text_input("📧 Email para pedidos", value=datos.get("mail_pedidos", ""),
                    help="Email donde se envían los pedidos de compra")
                plazo_pago = st.text_input("Plazo de pago", value=datos.get("plazo_pago", ""),
                    placeholder="Ej: 30 días, contado")
            notas = st.text_area("Notas", value=datos.get("notas", ""), height=80)
            col_s, col_c = st.columns([1, 3])
            with col_s:
                submitted = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_c:
                cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

        if cancelar:
            st.session_state.prov_modo = "lista"
            st.session_state.prov_edit_id = None
            st.rerun()
        if submitted:
            if not nombre_comercial.strip():
                st.error("El nombre comercial es obligatorio.")
            else:
                params = {
                    "p_nombre_comercial": nombre_comercial.strip(),
                    "p_razon_social": razon_social.strip() or None,
                    "p_cif": cif.strip() or None,
                    "p_domicilio": domicilio.strip() or None,
                    "p_persona_contacto": persona_contacto.strip() or None,
                    "p_telefono_contacto": telefono_contacto.strip() or None,
                    "p_mail_contacto": mail_contacto.strip() or None,
                    "p_mail_pedidos": mail_pedidos.strip() or None,
                    "p_forma_pago": forma_pago if forma_pago else None,
                    "p_plazo_pago": plazo_pago.strip() or None,
                    "p_notas": notas.strip() or None,
                }
                try:
                    if es_edicion:
                        params["p_id"] = st.session_state.prov_edit_id
                        res = rpc_call("rpc_actualizar_proveedor", params)
                    else:
                        res = rpc_call("rpc_crear_proveedor", params)
                    resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
                    if resultado.get("ok"):
                        st.success("Proveedor guardado correctamente.")
                        registrar_actividad("crear_proveedor" if not es_edicion else "editar_proveedor", "Proveedores", {"nombre": nombre_comercial})
                        st.session_state.prov_modo = "lista"
                        st.session_state.prov_edit_id = None
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    else:
        # Listado de proveedores
        proveedores = _supabase_get("proveedores_v2", "activo=eq.true&order=nombre_comercial.asc")
        if not proveedores:
            st.info("No hay proveedores registrados. Usa '➕ Nuevo proveedor' para añadir uno.")
        else:
            buscar = st.text_input("🔍 Buscar proveedor", placeholder="Nombre, CIF, contacto...")
            if buscar:
                buscar_l = buscar.lower()
                proveedores = [p for p in proveedores if buscar_l in (p.get("nombre_comercial") or "").lower() or buscar_l in (p.get("cif") or "").lower() or buscar_l in (p.get("persona_contacto") or "").lower()]
            st.caption(f"{len(proveedores)} proveedores activos")
            df_prov = pd.DataFrame(proveedores)
            cols_show = ["nombre_comercial", "cif", "persona_contacto", "telefono_contacto", "mail_pedidos", "forma_pago", "plazo_pago"]
            cols_show = [c for c in cols_show if c in df_prov.columns]
            st.dataframe(df_prov[cols_show].rename(columns={"nombre_comercial": "Nombre", "cif": "CIF", "persona_contacto": "Contacto", "telefono_contacto": "Teléfono", "mail_pedidos": "Email pedidos", "forma_pago": "Forma pago", "plazo_pago": "Plazo pago"}), use_container_width=True, hide_index=True)

            nombres_prov = {p["id"]: p["nombre_comercial"] for p in proveedores}
            opciones_prov = [""] + [f"{v} (ID:{k})" for k, v in nombres_prov.items()]
            sel_prov = st.selectbox("Seleccionar proveedor para editar", opciones_prov)
            if sel_prov:
                prov_id = int(sel_prov.split("ID:")[1].rstrip(")"))
                c_e, c_d = st.columns(2)
                with c_e:
                    if st.button("✏️ Editar", use_container_width=True, key="btn_edit_prov"):
                        st.session_state.prov_modo = "editar"
                        st.session_state.prov_edit_id = prov_id
                        st.rerun()
                with c_d:
                    if st.button("🗑️ Desactivar", use_container_width=True, key="btn_desact_prov"):
                        rpc_call("rpc_actualizar_proveedor", {"p_id": prov_id, "p_activo": False})
                        registrar_actividad("desactivar_proveedor", "Proveedores", {"id": prov_id})
                        st.success("Proveedor desactivado.")
                        time.sleep(0.5)
                        st.rerun()


elif st.session_state.pantalla == "ProductosCompra":
    if not user_has_access("ProductosCompra"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🛒 Productos de Compra")

    if "pc_modo" not in st.session_state:
        st.session_state.pc_modo = "lista"
    if "pc_edit_id" not in st.session_state:
        st.session_state.pc_edit_id = None

    TIPOS_IVA = ["", "General 21%", "Reducido 10%", "Superreducido 4%", "Exento 0%"]
    FORMAS_PAGO_PC = ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"]
    UNIDADES = ["", "kg", "unidad", "litro", "caja", "bolsa", "paquete", "metro"]

    tab_lista, tab_csv = st.tabs(["📋 Listado", "📥 Importar CSV"])

    with tab_lista:
        col_a, _ = st.columns([1, 5])
        with col_a:
            if st.button("➕ Nuevo producto", use_container_width=True, key="btn_nuevo_pc"):
                st.session_state.pc_modo = "nuevo"
                st.session_state.pc_edit_id = None
                st.rerun()

        proveedores_sel = _supabase_get("proveedores_v2", "activo=eq.true&order=nombre_comercial.asc", "id,nombre_comercial,forma_pago,plazo_pago")
        prov_opciones = ["(Sin proveedor)"] + [p["nombre_comercial"] for p in proveedores_sel]
        prov_ids = [None] + [p["id"] for p in proveedores_sel]
        prov_map = {p["id"]: p["nombre_comercial"] for p in proveedores_sel}

        if st.session_state.pc_modo in ("nuevo", "editar"):
            es_ed = st.session_state.pc_modo == "editar"
            st.subheader("✏️ Editar producto" if es_ed else "➕ Nuevo producto de compra")
            datos_pc = {}
            if es_ed and st.session_state.pc_edit_id:
                rows_pc = _supabase_get("productos_compra_v2", f"id=eq.{st.session_state.pc_edit_id}")
                if rows_pc:
                    datos_pc = rows_pc[0]
            prov_idx = 0
            if datos_pc.get("proveedor_id"):
                for ii, pid in enumerate(prov_ids):
                    if pid == datos_pc["proveedor_id"]:
                        prov_idx = ii
                        break
            with st.form("form_producto_compra", clear_on_submit=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    pc_nombre = st.text_input("Nombre *", value=datos_pc.get("nombre", ""))
                    pc_cod_interno = st.text_input("Código interno", value=datos_pc.get("cod_interno", ""))
                    pc_proveedor = st.selectbox("Proveedor", prov_opciones, index=prov_idx)
                    pc_precio = st.number_input("Precio", value=float(datos_pc.get("precio") or 0), min_value=0.0, step=0.01, format="%.2f")
                    pc_tipo_iva = st.selectbox("Tipo IVA", TIPOS_IVA, index=TIPOS_IVA.index(datos_pc.get("tipo_iva", "")) if datos_pc.get("tipo_iva", "") in TIPOS_IVA else 0)
                with c2:
                    pc_cod_prov = st.text_input("Código proveedor", value=datos_pc.get("cod_proveedor", ""))
                    pc_medidas = st.text_input("Medidas", value=datos_pc.get("medidas", ""))
                    pc_color = st.text_input("Color", value=datos_pc.get("color", ""))
                    pc_unidad = st.selectbox("Unidad de medida", UNIDADES, index=UNIDADES.index(datos_pc.get("unidad_medida", "")) if datos_pc.get("unidad_medida", "") in UNIDADES else 0)
                    pc_umin = st.number_input("Unidad mínima compra", value=float(datos_pc.get("unidad_minima_compra") or 0), min_value=0.0, step=1.0)
                with c3:
                    pc_dia_ped = st.text_input("Día(s) pedido", value=datos_pc.get("dia_pedido", ""), placeholder="Lunes,Miércoles")
                    pc_dia_ent = st.text_input("Día(s) entrega", value=datos_pc.get("dia_entrega", ""), placeholder="Martes,Jueves")
                    pc_fpago = st.selectbox("Forma pago (producto)", FORMAS_PAGO_PC, index=FORMAS_PAGO_PC.index(datos_pc.get("forma_pago", "")) if datos_pc.get("forma_pago", "") in FORMAS_PAGO_PC else 0, help="Vacío = hereda del proveedor")
                    pc_plpago = st.text_input("Plazo pago (producto)", value=datos_pc.get("plazo_pago", ""), help="Vacío = hereda del proveedor")
                    pc_stmin = st.number_input("Stock mínimo alerta", value=float(datos_pc.get("stock_minimo") or 0), min_value=0.0, step=1.0)
                col_s2, col_c2 = st.columns([1, 3])
                with col_s2:
                    pc_sub = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
                with col_c2:
                    pc_can = st.form_submit_button("❌ Cancelar", use_container_width=True)

            if pc_can:
                st.session_state.pc_modo = "lista"
                st.session_state.pc_edit_id = None
                st.rerun()
            if pc_sub:
                if not pc_nombre.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    prov_id_s = prov_ids[prov_opciones.index(pc_proveedor)] if pc_proveedor != "(Sin proveedor)" else None
                    params_pc = {
                        "p_nombre": pc_nombre.strip(), "p_proveedor_id": prov_id_s,
                        "p_cod_proveedor": pc_cod_prov.strip() or None, "p_cod_interno": pc_cod_interno.strip() or None,
                        "p_medidas": pc_medidas.strip() or None, "p_color": pc_color.strip() or None,
                        "p_unidad_medida": pc_unidad or None, "p_unidad_minima_compra": pc_umin if pc_umin > 0 else None,
                        "p_dia_pedido": pc_dia_ped.strip() or None, "p_dia_entrega": pc_dia_ent.strip() or None,
                        "p_precio": pc_precio if pc_precio > 0 else None, "p_tipo_iva": pc_tipo_iva or None,
                        "p_forma_pago": pc_fpago or None, "p_plazo_pago": pc_plpago.strip() or None,
                        "p_stock_minimo": pc_stmin if pc_stmin > 0 else 0,
                    }
                    try:
                        if es_ed:
                            params_pc["p_id"] = st.session_state.pc_edit_id
                            res_pc = rpc_call("rpc_actualizar_producto_compra", params_pc)
                        else:
                            res_pc = rpc_call("rpc_crear_producto_compra", params_pc)
                        r_pc = res_pc if isinstance(res_pc, dict) else (res_pc[0] if isinstance(res_pc, list) and res_pc else {})
                        if r_pc.get("ok"):
                            st.success("Producto guardado." if not es_ed else "Producto actualizado.")
                            registrar_actividad("crear_producto_compra" if not es_ed else "editar_producto_compra", "ProductosCompra", {"nombre": pc_nombre})
                            st.session_state.pc_modo = "lista"
                            st.session_state.pc_edit_id = None
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Error: {r_pc.get('error', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        else:
            # Listado productos compra
            productos_pc = _supabase_get("productos_compra_v2", "activo=eq.true&order=nombre.asc",
                "id,cod_interno,nombre,proveedor_id,precio,unidad_medida,dia_pedido,dia_entrega,forma_pago,plazo_pago,stock_minimo")
            for p in productos_pc:
                p["proveedor"] = prov_map.get(p.get("proveedor_id"), "—")
            f1, f2 = st.columns(2)
            with f1:
                buscar_pc = st.text_input("🔍 Buscar producto", placeholder="Nombre, código...", key="buscar_pc")
            with f2:
                filtro_prov_pc = st.selectbox("Filtrar proveedor", ["Todos"] + list(prov_map.values()), key="filtro_prov_pc")
            if buscar_pc:
                bl = buscar_pc.lower()
                productos_pc = [p for p in productos_pc if bl in (p.get("nombre") or "").lower() or bl in (p.get("cod_interno") or "").lower()]
            if filtro_prov_pc != "Todos":
                productos_pc = [p for p in productos_pc if p.get("proveedor") == filtro_prov_pc]
            if not productos_pc:
                st.info("No hay productos de compra.")
            else:
                st.caption(f"{len(productos_pc)} productos")
                df_pc = pd.DataFrame(productos_pc)
                cs = ["cod_interno", "nombre", "proveedor", "precio", "unidad_medida", "dia_pedido", "dia_entrega", "forma_pago", "plazo_pago"]
                cs = [c for c in cs if c in df_pc.columns]
                st.dataframe(df_pc[cs].rename(columns={"cod_interno": "Código", "nombre": "Nombre", "proveedor": "Proveedor", "precio": "Precio", "unidad_medida": "Unidad", "dia_pedido": "Día pedido", "dia_entrega": "Día entrega", "forma_pago": "Forma pago", "plazo_pago": "Plazo pago"}), use_container_width=True, hide_index=True)
                nms_pc = {p["id"]: f"{p.get('cod_interno', '')} - {p['nombre']}" for p in productos_pc}
                ops_pc = [""] + [f"{v} (ID:{k})" for k, v in nms_pc.items()]
                sel_pc = st.selectbox("Seleccionar producto para editar", ops_pc, key="sel_edit_pc")
                if sel_pc:
                    pcid = int(sel_pc.split("ID:")[1].rstrip(")"))
                    ce, cd = st.columns(2)
                    with ce:
                        if st.button("✏️ Editar", use_container_width=True, key="btn_edit_pc"):
                            st.session_state.pc_modo = "editar"
                            st.session_state.pc_edit_id = pcid
                            st.rerun()
                    with cd:
                        if st.button("🗑️ Desactivar", use_container_width=True, key="btn_desact_pc"):
                            rpc_call("rpc_actualizar_producto_compra", {"p_id": pcid, "p_activo": False})
                            st.success("Producto desactivado.")
                            time.sleep(0.5)
                            st.rerun()

    with tab_csv:
        st.subheader("📥 Importar productos desde CSV")
        st.markdown("**Formato CSV** (separador `;` o `,`): cod_proveedor, cod_interno, nombre, medidas, color, unidad_medida, unidad_minima_compra, dia_pedido, dia_entrega, proveedor, precio, tipo_iva")
        archivo_csv = st.file_uploader("Seleccionar CSV", type=["csv"], key="csv_pc_upload")
        if archivo_csv:
            try:
                contenido_csv = archivo_csv.read().decode("utf-8")
                sep_csv = ";" if ";" in contenido_csv.split("\n")[0] else ","
                df_csv = pd.read_csv(io.StringIO(contenido_csv), sep=sep_csv, dtype=str).fillna("")
                st.write(f"**{len(df_csv)} filas detectadas**")
                st.dataframe(df_csv.head(10), use_container_width=True, hide_index=True)
                if st.button("🚀 Importar productos", type="primary", key="btn_importar_csv"):
                    import json as _json
                    rows_j = []
                    for _, row_c in df_csv.iterrows():
                        rd = {}
                        for col_c in df_csv.columns:
                            val_c = str(row_c[col_c]).strip()
                            rd[col_c.strip().lower()] = val_c if val_c else None
                        rows_j.append(rd)
                    try:
                        res_csv = rpc_call("rpc_upsert_productos_compra_batch", {"p_rows": _json.dumps(rows_j)})
                        r_csv = res_csv if isinstance(res_csv, dict) else (res_csv[0] if isinstance(res_csv, list) and res_csv else {})
                        if r_csv.get("ok"):
                            st.success(f"Importación completada: {r_csv.get('procesados', 0)} productos.")
                            registrar_actividad("importar_csv", "ProductosCompra", {"filas": len(rows_j)})
                        else:
                            st.error(f"Error: {r_csv.get('error', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error en importación: {e}")
            except Exception as e:
                st.error(f"Error leyendo CSV: {e}")


elif st.session_state.pantalla == "Locales":
    if not user_has_access("Locales"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🏪 Locales")

    if "loc_modo" not in st.session_state:
        st.session_state.loc_modo = "lista"
    if "loc_edit_id" not in st.session_state:
        st.session_state.loc_edit_id = None

    col_al, _ = st.columns([1, 5])
    with col_al:
        if st.button("➕ Nuevo local", use_container_width=True):
            st.session_state.loc_modo = "nuevo"
            st.session_state.loc_edit_id = None
            st.rerun()

    if st.session_state.loc_modo in ("nuevo", "editar"):
        es_ed_l = st.session_state.loc_modo == "editar"
        st.subheader("✏️ Editar local" if es_ed_l else "➕ Nuevo local")
        datos_l = {}
        if es_ed_l and st.session_state.loc_edit_id:
            rows_l = _supabase_get("locales_compra_v2", f"id=eq.{st.session_state.loc_edit_id}")
            if rows_l:
                datos_l = rows_l[0]
        with st.form("form_local", clear_on_submit=False):
            cl1, cl2 = st.columns(2)
            with cl1:
                loc_nombre = st.text_input("Nombre del local *", value=datos_l.get("nombre", ""))
                loc_direccion = st.text_input("Dirección", value=datos_l.get("direccion", ""))
            with cl2:
                loc_telefono = st.text_input("Teléfono", value=datos_l.get("telefono", ""))
                loc_transporte = st.text_input("Transporte", value=datos_l.get("transporte", ""), placeholder="Furgoneta propia, Mensajería...")
            col_sl, col_cl = st.columns([1, 3])
            with col_sl:
                loc_sub = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
            with col_cl:
                loc_can = st.form_submit_button("❌ Cancelar", use_container_width=True)
        if loc_can:
            st.session_state.loc_modo = "lista"
            st.session_state.loc_edit_id = None
            st.rerun()
        if loc_sub:
            if not loc_nombre.strip():
                st.error("El nombre es obligatorio.")
            else:
                params_l = {"p_nombre": loc_nombre.strip(), "p_direccion": loc_direccion.strip() or None, "p_telefono": loc_telefono.strip() or None, "p_transporte": loc_transporte.strip() or None}
                try:
                    if es_ed_l:
                        params_l["p_id"] = st.session_state.loc_edit_id
                        res_l = rpc_call("rpc_actualizar_local_compra", params_l)
                    else:
                        res_l = rpc_call("rpc_crear_local_compra", params_l)
                    r_l = res_l if isinstance(res_l, dict) else (res_l[0] if isinstance(res_l, list) and res_l else {})
                    if r_l.get("ok"):
                        st.success("Local guardado.")
                        registrar_actividad("crear_local" if not es_ed_l else "editar_local", "Locales", {"nombre": loc_nombre})
                        st.session_state.loc_modo = "lista"
                        st.session_state.loc_edit_id = None
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Error: {r_l.get('error', 'Error desconocido')}")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        locales_list = _supabase_get("locales_compra_v2", "activo=eq.true&order=nombre.asc")
        if not locales_list:
            st.info("No hay locales registrados.")
        else:
            st.caption(f"{len(locales_list)} locales activos")
            df_loc = pd.DataFrame(locales_list)
            cl_s = [c for c in ["nombre", "direccion", "telefono", "transporte"] if c in df_loc.columns]
            st.dataframe(df_loc[cl_s].rename(columns={"nombre": "Nombre", "direccion": "Dirección", "telefono": "Teléfono", "transporte": "Transporte"}), use_container_width=True, hide_index=True)
            nms_l = {l["id"]: l["nombre"] for l in locales_list}
            ops_l = [""] + [f"{v} (ID:{k})" for k, v in nms_l.items()]
            sel_l = st.selectbox("Seleccionar local para editar", ops_l)
            if sel_l:
                lid = int(sel_l.split("ID:")[1].rstrip(")"))
                cel, cdl = st.columns(2)
                with cel:
                    if st.button("✏️ Editar", use_container_width=True, key="btn_edit_loc"):
                        st.session_state.loc_modo = "editar"
                        st.session_state.loc_edit_id = lid
                        st.rerun()
                with cdl:
                    if st.button("🗑️ Desactivar", use_container_width=True, key="btn_desact_loc"):
                        rpc_call("rpc_actualizar_local_compra", {"p_id": lid, "p_activo": False})
                        st.success("Local desactivado.")
                        time.sleep(0.5)
                        st.rerun()


elif st.session_state.pantalla == "Stock":
    if not user_has_access("Stock"):
        st.error("No tienes acceso a esta sección.")
        st.stop()
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📦 Gestión de Stock")

    stock_data = _supabase_get("vw_stock_actual", "order=producto_nombre.asc")
    locales_data = _supabase_get("locales_compra_v2", "activo=eq.true&order=nombre.asc")
    prods_data = _supabase_get("productos_compra_v2", "activo=eq.true&order=nombre.asc", "id,nombre,cod_interno,proveedor_id,unidad_medida,dia_pedido,dia_entrega,producto_venta_id")

    stk_tabs = st.tabs(["📊 Por producto", "🏭 Por proveedor", "📈 Stock vs Sell-out", "🔮 Previsión semanal", "🔄 Traspasos", "✅ Regularización", "📜 Historial"])

    # ── Tab 1: Stock por producto ──
    with stk_tabs[0]:
        st.subheader("Stock actual por producto")
        if not stock_data:
            st.info("No hay movimientos de stock registrados.")
        else:
            local_nms = ["Todos"] + [l["nombre"] for l in locales_data]
            local_filt = st.selectbox("📍 Local", local_nms, key="stk_local_prod")
            stk_view = stock_data if local_filt == "Todos" else [s for s in stock_data if s.get("local_nombre") == local_filt]
            alertas = [s for s in stk_view if float(s.get("stock_actual", 0)) <= float(s.get("stock_minimo", 0)) and float(s.get("stock_minimo", 0)) > 0]
            if alertas:
                with st.expander(f"⚠️ {len(alertas)} productos bajo stock mínimo", expanded=True):
                    for a in alertas:
                        st.warning(f"**{a['producto_nombre']}** — Stock: {a['stock_actual']} {a.get('unidad_medida','')} (Mín: {a['stock_minimo']})")
            tot_refs = len(set(s["producto_compra_id"] for s in stk_view))
            tot_uds = sum(float(s.get("stock_actual", 0)) for s in stk_view)
            tot_val = sum(float(s.get("stock_actual", 0)) * float(s.get("precio") or 0) for s in stk_view)
            m1s, m2s, m3s, m4s = st.columns(4)
            m1s.metric("Referencias", f"{tot_refs}")
            m2s.metric("Unidades totales", f"{tot_uds:,.0f}")
            m3s.metric("Valor estimado", f"{tot_val:,.2f} €")
            m4s.metric("Alertas", f"{len(alertas)}")
            df_stk = pd.DataFrame(stk_view)
            stk_cols = [c for c in ["producto_nombre", "cod_interno", "local_nombre", "stock_actual", "stock_minimo", "unidad_medida", "proveedor_nombre", "ultimo_movimiento"] if c in df_stk.columns]
            st.dataframe(df_stk[stk_cols].rename(columns={"producto_nombre": "Producto", "cod_interno": "Código", "local_nombre": "Local", "stock_actual": "Stock", "stock_minimo": "Mínimo", "unidad_medida": "Unidad", "proveedor_nombre": "Proveedor", "ultimo_movimiento": "Últ. movimiento"}), use_container_width=True, hide_index=True)

            # Registrar movimiento rápido
            st.divider()
            st.subheader("📥 Registrar movimiento")
            if prods_data and locales_data:
                with st.form("form_mov_rapido", clear_on_submit=True):
                    cm1, cm2, cm3 = st.columns(3)
                    with cm1:
                        mv_prod_ops = [f"{p.get('cod_interno', '')} - {p['nombre']}" for p in prods_data]
                        mv_prod = st.selectbox("Producto", mv_prod_ops, key="mv_prod")
                        mv_tipo = st.selectbox("Tipo", ["entrada", "salida", "merma"], key="mv_tipo")
                    with cm2:
                        mv_loc_ops = [l["nombre"] for l in locales_data]
                        mv_loc = st.selectbox("Local", mv_loc_ops, key="mv_loc")
                        mv_cant = st.number_input("Cantidad", min_value=0.01, step=1.0, key="mv_cant")
                    with cm3:
                        mv_motivo = st.text_input("Motivo", key="mv_motivo", placeholder="Recepción pedido, Merma...")
                        mv_fecha = st.date_input("Fecha", value=datetime.date.today(), key="mv_fecha")
                    mv_sub = st.form_submit_button("✅ Registrar movimiento", type="primary", use_container_width=True)
                if mv_sub:
                    mv_pid = prods_data[mv_prod_ops.index(mv_prod)]["id"]
                    mv_lid = locales_data[mv_loc_ops.index(mv_loc)]["id"]
                    mv_user = get_user()
                    try:
                        res_mv = rpc_call("rpc_registrar_movimiento_stock", {"p_producto_compra_id": mv_pid, "p_local_id": mv_lid, "p_tipo": mv_tipo, "p_cantidad": float(mv_cant), "p_motivo": mv_motivo.strip() or None, "p_fecha": mv_fecha.isoformat(), "p_usuario_id": mv_user["id"] if mv_user else None})
                        r_mv = res_mv if isinstance(res_mv, dict) else (res_mv[0] if isinstance(res_mv, list) and res_mv else {})
                        if r_mv.get("ok"):
                            st.success(f"Movimiento registrado: {mv_tipo} de {mv_cant} uds.")
                            registrar_actividad("registrar_movimiento", "Stock", {"tipo": mv_tipo, "cantidad": float(mv_cant)})
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Error: {r_mv.get('error', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Tab 2: Por proveedor ──
    with stk_tabs[1]:
        st.subheader("Stock por proveedor")
        if not stock_data:
            st.info("Sin datos de stock.")
        else:
            por_prov = {}
            for s in stock_data:
                pnm = s.get("proveedor_nombre") or "Sin proveedor"
                if pnm not in por_prov:
                    por_prov[pnm] = {"refs": 0, "uds": 0, "val": 0}
                por_prov[pnm]["refs"] += 1
                por_prov[pnm]["uds"] += float(s.get("stock_actual", 0))
                por_prov[pnm]["val"] += float(s.get("stock_actual", 0)) * float(s.get("precio") or 0)
            rows_pp = [{"Proveedor": k, "Referencias": v["refs"], "Unidades": f"{v['uds']:,.0f}", "Valor (€)": f"{v['val']:,.2f}"} for k, v in sorted(por_prov.items())]
            st.dataframe(pd.DataFrame(rows_pp), use_container_width=True, hide_index=True)

    # ── Tab 3: Stock vs Sell-out ──
    with stk_tabs[2]:
        st.subheader("Stock vs Sell-out")
        vinculados = [s for s in stock_data if s.get("producto_venta_id")] if stock_data else []
        if not vinculados:
            st.info("No hay productos de compra vinculados a productos de venta (producto_venta_id).")
        else:
            fecha_fin_so = datetime.date.today()
            fecha_ini_so = fecha_fin_so - datetime.timedelta(days=30)
            rows_so = []
            for sv in vinculados:
                vid = sv["producto_venta_id"]
                try:
                    ventas_so = _supabase_get("ventas_raw_v2", f"producto_id=eq.{vid}&fecha=gte.{fecha_ini_so.isoformat()}&fecha=lte.{fecha_fin_so.isoformat()}", "uds_vendidas")
                    tot_v = sum(float(v.get("uds_vendidas", 0)) for v in ventas_so) if ventas_so else 0
                    med_d = tot_v / 30 if tot_v > 0 else 0
                    stk_a = float(sv.get("stock_actual", 0))
                    dias_c = int(stk_a / med_d) if med_d > 0 else 999
                    rows_so.append({"Producto": sv["producto_nombre"], "Stock": f"{stk_a:,.0f}", "Venta/día": f"{med_d:,.1f}", "Días cobertura": dias_c if dias_c < 999 else "∞", "Estado": "🔴 Crítico" if dias_c <= 2 else "🟡 Bajo" if dias_c <= 5 else "🟢 OK"})
                except Exception:
                    pass
            if rows_so:
                st.dataframe(pd.DataFrame(rows_so), use_container_width=True, hide_index=True)
            else:
                st.info("No se pudieron calcular datos de sell-out.")

    # ── Tab 4: Previsión semanal (alarma inteligente) ──
    with stk_tabs[3]:
        st.subheader("🔮 Previsión semanal — Alarma inteligente")
        st.caption("Punto de reorden = venta media diaria × lead time (día pedido → día entrega + 1 día seguridad)")
        DIAS_SEM = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
        hoy_prev = datetime.date.today()
        rows_al = []
        for sp in (stock_data or []):
            vid_p = sp.get("producto_venta_id")
            dp_str = sp.get("dia_pedido", "")
            de_str = sp.get("dia_entrega", "")
            if not vid_p or not dp_str or not de_str:
                continue
            dp_1 = dp_str.split(",")[0].strip()
            de_1 = de_str.split(",")[0].strip()
            dp_n = DIAS_SEM.get(dp_1)
            de_n = DIAS_SEM.get(de_1)
            if dp_n is None or de_n is None:
                continue
            lt = (de_n - dp_n) % 7
            if lt == 0:
                lt = 7
            lt += 1
            try:
                fi_p = hoy_prev - datetime.timedelta(days=30)
                v_p = _supabase_get("ventas_raw_v2", f"producto_id=eq.{vid_p}&fecha=gte.{fi_p.isoformat()}&fecha=lte.{hoy_prev.isoformat()}", "uds_vendidas")
                tv_p = sum(float(v.get("uds_vendidas", 0)) for v in v_p) if v_p else 0
                vm_p = tv_p / 30 if tv_p > 0 else 0
            except Exception:
                vm_p = 0
            sa_p = float(sp.get("stock_actual", 0))
            pr_p = vm_p * lt
            nec_p = max(0, pr_p - sa_p)
            if nec_p > 0 or sa_p <= pr_p:
                rows_al.append({"Producto": sp["producto_nombre"], "Stock": f"{sa_p:,.0f}", "Venta/día": f"{vm_p:,.1f}", "Lead time": f"{lt}d", "Pto reorden": f"{pr_p:,.0f}", "Pedir": f"{int(np.ceil(nec_p)):,}", "Día pedido": dp_str, "Proveedor": sp.get("proveedor_nombre", "—"), "Urg": "🔴" if sa_p <= vm_p else "🟡" if sa_p <= pr_p else "🟢"})
        if rows_al:
            urg_ord = {"🔴": 0, "🟡": 1, "🟢": 2}
            rows_al.sort(key=lambda r: urg_ord.get(r["Urg"], 3))
            st.dataframe(pd.DataFrame(rows_al), use_container_width=True, hide_index=True)
            nc = sum(1 for r in rows_al if r["Urg"] == "🔴")
            nb = sum(1 for r in rows_al if r["Urg"] == "🟡")
            ma1, ma2, ma3 = st.columns(3)
            ma1.metric("Críticos", f"{nc}")
            ma2.metric("Bajo mínimo", f"{nb}")
            ma3.metric("Total a pedir", f"{len(rows_al)}")
        else:
            st.success("Todos los productos tienen stock suficiente.")

    # ── Tab 5: Traspasos ──
    with stk_tabs[4]:
        st.subheader("🔄 Traspaso entre locales")
        if not prods_data or len(locales_data) < 2:
            st.info("Necesitas al menos 2 locales y 1 producto para traspasos.")
        else:
            with st.form("form_traspaso", clear_on_submit=True):
                ct1, ct2 = st.columns(2)
                with ct1:
                    tr_prod_ops = [f"{p.get('cod_interno', '')} - {p['nombre']}" for p in prods_data]
                    tr_prod = st.selectbox("Producto", tr_prod_ops, key="tr_prod")
                    tr_origen = st.selectbox("Local origen", [l["nombre"] for l in locales_data], key="tr_orig")
                with ct2:
                    tr_cant = st.number_input("Cantidad", min_value=0.01, step=1.0, key="tr_cant")
                    tr_destino = st.selectbox("Local destino", [l["nombre"] for l in locales_data], key="tr_dest")
                tr_motivo = st.text_input("Motivo", key="tr_mot", placeholder="Reposición, Evento especial...")
                tr_sub = st.form_submit_button("🔄 Ejecutar traspaso", type="primary", use_container_width=True)
            if tr_sub:
                if tr_origen == tr_destino:
                    st.error("Origen y destino no pueden ser el mismo.")
                else:
                    tr_pid = prods_data[tr_prod_ops.index(tr_prod)]["id"]
                    tr_oid = locales_data[[l["nombre"] for l in locales_data].index(tr_origen)]["id"]
                    tr_did = locales_data[[l["nombre"] for l in locales_data].index(tr_destino)]["id"]
                    tr_user = get_user()
                    try:
                        res_tr = rpc_call("rpc_traspaso_stock", {"p_producto_compra_id": tr_pid, "p_local_origen_id": tr_oid, "p_local_destino_id": tr_did, "p_cantidad": float(tr_cant), "p_motivo": tr_motivo.strip() or None, "p_fecha": datetime.date.today().isoformat(), "p_usuario_id": tr_user["id"] if tr_user else None})
                        r_tr = res_tr if isinstance(res_tr, dict) else (res_tr[0] if isinstance(res_tr, list) and res_tr else {})
                        if r_tr.get("ok"):
                            st.success(f"Traspaso completado: {tr_cant} uds de {tr_origen} → {tr_destino}")
                            registrar_actividad("traspaso_stock", "Stock", {"origen": tr_origen, "destino": tr_destino, "cantidad": float(tr_cant)})
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Error: {r_tr.get('error', 'Error desconocido')}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            st.divider()
            st.caption("Últimos traspasos")
            trasp_hist = _supabase_get("stock_movimientos_v2", "tipo=eq.traspaso_salida&order=created_at.desc&limit=20", "id,producto_compra_id,local_id,local_destino_id,cantidad,motivo,fecha")
            if trasp_hist:
                pr_map = {p["id"]: p["nombre"] for p in prods_data}
                lo_map = {l["id"]: l["nombre"] for l in locales_data}
                rows_tr = [{"Fecha": t.get("fecha",""), "Producto": pr_map.get(t.get("producto_compra_id"),"?"), "Origen": lo_map.get(t.get("local_id"),"?"), "Destino": lo_map.get(t.get("local_destino_id"),"?"), "Cantidad": t.get("cantidad",0), "Motivo": t.get("motivo","")} for t in trasp_hist]
                st.dataframe(pd.DataFrame(rows_tr), use_container_width=True, hide_index=True)
            else:
                st.info("No hay traspasos registrados.")

    # ── Tab 6: Regularización ──
    with stk_tabs[5]:
        st.subheader("✅ Regularización de stock (Inventario)")
        st.caption("Introduce conteo real. El sistema calcula diferencias y crea ajustes.")
        if not locales_data:
            st.info("No hay locales registrados.")
        else:
            reg_local = st.selectbox("📍 Local a regularizar", [l["nombre"] for l in locales_data], key="reg_local")
            reg_lid = locales_data[[l["nombre"] for l in locales_data].index(reg_local)]["id"]
            stk_reg = [s for s in (stock_data or []) if s.get("local_id") == reg_lid]
            if not stk_reg:
                st.info("No hay stock registrado en este local.")
            else:
                st.write(f"**{len(stk_reg)} productos con stock en {reg_local}**")
                with st.form("form_regularizacion"):
                    conteos = {}
                    for sr in stk_reg:
                        sr_pid = sr["producto_compra_id"]
                        sr_nom = sr["producto_nombre"]
                        sr_stk = float(sr.get("stock_actual", 0))
                        sr_ud = sr.get("unidad_medida", "uds")
                        cr1, cr2, cr3 = st.columns([3, 1, 1])
                        with cr1:
                            st.write(f"**{sr_nom}** (sistema: {sr_stk:,.0f} {sr_ud})")
                        with cr2:
                            conteos[sr_pid] = st.number_input(f"Conteo", value=float(sr_stk), step=1.0, key=f"reg_{sr_pid}", label_visibility="collapsed")
                        with cr3:
                            dif = conteos[sr_pid] - sr_stk
                            if dif != 0:
                                col_d = "red" if dif < 0 else "green"
                                st.markdown(f"<span style='color:{col_d};font-weight:bold'>{dif:+,.0f}</span>", unsafe_allow_html=True)
                            else:
                                st.write("—")
                    reg_motivo = st.text_input("Motivo", value="Inventario físico", key="reg_motivo")
                    reg_sub = st.form_submit_button("✅ Aplicar regularización", type="primary", use_container_width=True)
                if reg_sub:
                    import json as _json2
                    ajustes = []
                    for sr in stk_reg:
                        sr_pid = sr["producto_compra_id"]
                        ct = conteos.get(sr_pid, float(sr.get("stock_actual", 0)))
                        if ct != float(sr.get("stock_actual", 0)):
                            ajustes.append({"producto_compra_id": sr_pid, "local_id": reg_lid, "conteo_real": ct, "motivo": reg_motivo})
                    if not ajustes:
                        st.info("No hay diferencias que ajustar.")
                    else:
                        reg_user = get_user()
                        try:
                            res_rg = rpc_call("rpc_regularizar_stock", {"p_ajustes": _json2.dumps(ajustes), "p_usuario_id": reg_user["id"] if reg_user else None})
                            r_rg = res_rg if isinstance(res_rg, dict) else (res_rg[0] if isinstance(res_rg, list) and res_rg else {})
                            if r_rg.get("ok"):
                                st.success(f"Regularización completada: {r_rg.get('ajustes_aplicados', 0)} ajustes.")
                                registrar_actividad("regularizacion", "Stock", {"local": reg_local, "ajustes": r_rg.get('ajustes_aplicados', 0)})
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(f"Error: {r_rg.get('error', 'Error desconocido')}")
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ── Tab 7: Historial ──
    with stk_tabs[6]:
        st.subheader("📜 Historial de movimientos")
        hf1, hf2, hf3 = st.columns(3)
        with hf1:
            h_desde = st.date_input("Desde", value=datetime.date.today() - datetime.timedelta(days=30), key="hist_desde")
        with hf2:
            h_hasta = st.date_input("Hasta", value=datetime.date.today(), key="hist_hasta")
        with hf3:
            h_tipos = ["Todos", "entrada", "salida", "merma", "ajuste_positivo", "ajuste_negativo", "traspaso_entrada", "traspaso_salida", "venta_auto"]
            h_tipo = st.selectbox("Tipo", h_tipos, key="hist_tipo")
        h_params = f"fecha=gte.{h_desde.isoformat()}&fecha=lte.{h_hasta.isoformat()}&order=created_at.desc&limit=500"
        if h_tipo != "Todos":
            h_params += f"&tipo=eq.{h_tipo}"
        movs = _supabase_get("stock_movimientos_v2", h_params, "id,producto_compra_id,local_id,tipo,cantidad,motivo,fecha,created_at")
        if not movs:
            st.info("No hay movimientos en el período seleccionado.")
        else:
            pr_m = {p["id"]: p["nombre"] for p in prods_data}
            lo_m = {l["id"]: l["nombre"] for l in locales_data}
            TIPO_E = {"entrada": "📥", "salida": "📤", "merma": "🗑️", "ajuste_positivo": "➕", "ajuste_negativo": "➖", "traspaso_entrada": "🔄📥", "traspaso_salida": "🔄📤", "venta_auto": "💰"}
            rows_h = [{"Fecha": m.get("fecha",""), "Tipo": f"{TIPO_E.get(m.get('tipo',''),'')} {m.get('tipo','')}", "Producto": pr_m.get(m.get("producto_compra_id"),"?"), "Local": lo_m.get(m.get("local_id"),"?"), "Cantidad": m.get("cantidad",0), "Motivo": m.get("motivo","")} for m in movs]
            st.caption(f"{len(rows_h)} movimientos")
            st.dataframe(pd.DataFrame(rows_h), use_container_width=True, hide_index=True)
            st.divider()
            st.caption("Resumen por tipo")
            resumen_h = {}
            for m in movs:
                t = m.get("tipo", "?")
                resumen_h[t] = resumen_h.get(t, 0) + float(m.get("cantidad", 0))
            st.dataframe(pd.DataFrame([{"Tipo": k, "Total": f"{v:,.0f}"} for k, v in sorted(resumen_h.items())]), use_container_width=True, hide_index=True)

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

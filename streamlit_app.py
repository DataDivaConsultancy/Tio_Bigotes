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
@@ -224,50 +226,58 @@ except Exception as e:

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



@@ -367,50 +377,311 @@ def detectar_csv(file_bytes: bytes) -> Tuple[str, str, str]:
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
@@ -959,61 +1230,71 @@ def guardar_control_diario(payloads: List[Dict[str, Any]]) -> None:
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
    "Compras",
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
    "Compras": "Compras",
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
@@ -1027,60 +1308,68 @@ def generar_whatsapp_link(telefono: str, nombre: str, email: str, password: str)
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

    # Compatibilidad: usuarios creados antes del módulo de Compras
    # pueden no tener el permiso "Compras" pero sí "Productos".
    if pantalla == "Compras":
        return ("Compras" in permisos) or ("Productos" in permisos)

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
@@ -1264,104 +1553,126 @@ if get_user().get("must_change_password") and st.session_state.pantalla != "Camb
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
   st.markdown(
    f"""<div class="tb-header">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h1>&#x1F95F; Tío Bigotes</h1>
                <div class="tb-subtitle">DIP159 &nbsp;|&nbsp; {datetime.date.today().strftime('%d/%m/%Y')}</div>
            </div>
            <div class="tb-user">
                User: {_user['nombre']} &nbsp;•&nbsp; {_user['rol']}
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)
    _btn_l, _btn_r, _ = st.columns([1, 1, 4])
    st.caption(f"Versión app: {APP_VERSION}")
    if not _compras_ready:
        st.warning("Módulo Compras v2 no inicializado en esta base. Ejecuta `sql_migration_compras_productos.sql`.")
    _btn_l, _btn_r, _btn_compras, _ = st.columns([1, 1, 1, 3])
    with _btn_l:
        if st.button("🔑 Cambiar contraseña", use_container_width=True):
            st.session_state.pantalla = "CambiarPassword"
            st.rerun()
    with _btn_r:
        if st.button("🔒 Cerrar sesión", use_container_width=True):
            cerrar_sesion()
            st.rerun()
    with _btn_compras:
        if st.button("🛒 Ir a Compras", use_container_width=True):
            ir_a("Compras")

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
        can_see = user_has_access(pantalla_key)
        # "Compras" se muestra siempre a usuarios autenticados para evitar
        # bloqueos por permisos legacy no sincronizados.
        if pantalla_key in ("Compras", "Proveedores", "ProductosCompra", "Locales", "Stock"):
            can_see = True

        if can_see:
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
    _p_back, _p_buy = st.columns([1, 1])
    with _p_back:
        st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    with _p_buy:
        if st.button("🛒 IR A COMPRAS"):
            ir_a("Compras")
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

@@ -1491,50 +1802,278 @@ elif st.session_state.pantalla == "Productos":
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
# COMPRAS
# =========================================================

elif st.session_state.pantalla in ("Compras", "Proveedores", "ProductosCompra", "Locales", "Stock"):
    pantalla_compra = st.session_state.pantalla
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header(f"🛒 Módulo de Compras · {pantalla_compra}")

    df_proveedores = cargar_proveedores_compra()
    df_productos_compra = cargar_productos_compra()
    df_locales_compra = cargar_locales_compra()

    if pantalla_compra in ("Compras", "Proveedores"):
        st.subheader("🏭 Proveedores")
        st.dataframe(df_proveedores, use_container_width=True, hide_index=True)
        with st.form("form_proveedor_compra"):
            c1, c2 = st.columns(2)
            payload = {
                "nombre_comercial": c1.text_input("Nombre Comercial *"),
                "razon_social": c2.text_input("Razón Social"),
                "cif": c1.text_input("CIF"),
                "domicilio": c2.text_input("Domicilio"),
                "persona_contacto": c1.text_input("Persona Contacto"),
                "telefono_contacto": c2.text_input("Teléfono Contacto"),
                "mail_contacto": c1.text_input("Mail Contacto"),
                "forma_pago": c2.selectbox("Forma de Pago", ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"]),
                "plazo_pago": c1.text_input("Plazo de Pago", value="30 días"),
                "notas": c2.text_input("Notas"),
                "activo": True,
            }
            if st.form_submit_button("Guardar proveedor"):
                upsert_proveedor_compra(payload)
                st.success("Proveedor guardado")
                st.rerun()

    if pantalla_compra in ("Compras", "Locales"):
        st.subheader("🏪 Locales")
        st.dataframe(df_locales_compra, use_container_width=True, hide_index=True)
        with st.form("form_local_compra"):
            c1, c2 = st.columns(2)
            payload_local = {
                "nombre": c1.text_input("Nombre local *"),
                "direccion": c2.text_input("Dirección"),
                "telefono": c1.text_input("Teléfono"),
                "transporte": c2.text_input("Transporte"),
                "activo": True,
            }
            if st.form_submit_button("Guardar local"):
                upsert_local_compra(payload_local)
                st.success("Local guardado")
                st.rerun()

    if pantalla_compra in ("Compras", "ProductosCompra"):
        st.subheader("📦 Productos Compra")
        if not df_productos_compra.empty:
            st.dataframe(df_productos_compra, use_container_width=True, hide_index=True)

        proveedores_dict = {int(r["id"]): str(r.get("nombre_comercial") or "") for _, r in df_proveedores.iterrows()} if not df_proveedores.empty else {}
        proveedores_meta = {int(r["id"]): r.to_dict() for _, r in df_proveedores.iterrows()} if not df_proveedores.empty else {}
        with st.form("form_producto_compra"):
            c1, c2 = st.columns(2)
            proveedor_sel = c1.selectbox("Proveedor", options=[None] + sorted(proveedores_dict.keys()), format_func=lambda x: "—" if x is None else proveedores_dict[x])
            forma_pago_default = ""
            plazo_pago_default = ""
            if proveedor_sel and proveedor_sel in proveedores_meta:
                forma_pago_default = str(proveedores_meta[proveedor_sel].get("forma_pago") or "")
                plazo_pago_default = str(proveedores_meta[proveedor_sel].get("plazo_pago") or "")
            payload_prod = {
                "cod_proveedor": c1.text_input("Cód. proveedor"),
                "cod_interno": c2.text_input("Cód. interno *"),
                "nombre": st.text_input("Nombre *"),
                "medidas": c1.text_input("Medidas"),
                "color": c2.text_input("Color"),
                "unidad_medida": c1.text_input("Unidad medida"),
                "unidad_minima_compra": c2.number_input("Unidad mínima compra", min_value=0.0, step=0.5, value=0.0),
                "dia_pedido": c1.text_input("Día pedido"),
                "dia_entrega": c2.text_input("Día entrega"),
                "proveedor_id": proveedor_sel,
                "precio": c2.number_input("Precio", min_value=0.0, step=0.1, value=0.0),
                "tipo_iva": c1.selectbox("Tipo IVA", ["General 21%", "Reducido 10%", "Superreducido 4%", "Exento 0%"]),
                "forma_pago": c2.selectbox(
                    "Forma pago (heredada editable)",
                    ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"],
                    index=(["", "SEPA", "Transferencia", "T. Credito", "Efectivo"].index(forma_pago_default) if forma_pago_default in ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"] else 0),
                ),
                "plazo_pago": c1.text_input("Plazo pago (heredado editable)", value=plazo_pago_default),
                "stock_minimo": c2.number_input("Stock mínimo", min_value=0.0, step=1.0, value=0.0),
                "activo": True,
            }
            if st.form_submit_button("Guardar producto"):
                upsert_producto_compra(payload_prod)
                st.success("Producto guardado")
                st.rerun()

        st.caption("Importación CSV de Productos Compra")
        archivo_compra = st.file_uploader("Sube CSV", type=["csv"], key="csv_prod_compra_v2")
        if archivo_compra is not None and st.button("Importar CSV Productos Compra"):
            file_bytes = archivo_compra.getvalue()
            df_all, _, sep_detectado = leer_csv_preview(file_bytes, nrows=50000)
            df_to_import = preparar_csv_productos_compra(df_all)
            proveedores_map = {}
            if not df_proveedores.empty:
                for _, p in df_proveedores.iterrows():
                    n = str(p.get("nombre_comercial") or "").strip().lower()
                    if n:
                        proveedores_map[n] = p.to_dict()
            for _, row in df_to_import.iterrows():
                row_d = row.to_dict()
                prov_n = str(row_d.get("proveedor") or "").strip().lower()
                if prov_n in proveedores_map:
                    row_d["proveedor_id"] = int(proveedores_map[prov_n]["id"])
                    row_d["forma_pago"] = proveedores_map[prov_n].get("forma_pago")
                    row_d["plazo_pago"] = proveedores_map[prov_n].get("plazo_pago")
                row_d["activo"] = True
                upsert_producto_compra(row_d)
            st.success("Importación completada")
            st.rerun()

    if pantalla_compra in ("Compras", "Stock"):
        st.subheader("📊 Stock")
        df_stock = cargar_stock_compra()
        if not df_stock.empty and not df_productos_compra.empty:
            merge_cols = ["id", "dia_pedido", "dia_entrega", "stock_minimo"]
            df_meta = df_productos_compra[[c for c in merge_cols if c in df_productos_compra.columns]].copy()
            df_meta = df_meta.rename(columns={"id": "producto_compra_id", "stock_minimo": "stock_minimo_cfg"})
            df_stock = df_stock.merge(df_meta, on="producto_compra_id", how="left")
            df_stock["lead_time_dias"] = df_stock.apply(
                lambda r: calcular_lead_time_dias(r.get("dia_pedido"), r.get("dia_entrega")),
                axis=1,
            )
            df_stock["venta_media_dia_est"] = df_stock["stock_minimo_cfg"].fillna(0).apply(
                lambda x: max(float(x) / 7.0, 0.1)
            )
            df_stock["consumo_lead_time"] = df_stock["venta_media_dia_est"] * df_stock["lead_time_dias"]
            df_stock["stock_seguridad"] = df_stock.apply(
                lambda r: max(float(r.get("stock_minimo_cfg") or 0), float(r.get("venta_media_dia_est") or 0)),
                axis=1,
            )
            df_stock["punto_reorden"] = df_stock["consumo_lead_time"] + df_stock["stock_seguridad"]

            def _estado(r: pd.Series) -> str:
                s = float(r.get("stock_actual") or 0)
                if s <= float(r.get("consumo_lead_time") or 0) * 0.5:
                    return "🔴 CRÍTICO"
                if s <= float(r.get("punto_reorden") or 0):
                    return "⚠ PEDIR"
                return "✅ OK"

            df_stock["estado"] = df_stock.apply(_estado, axis=1)

        tab_prod, tab_trasp, tab_reg = st.tabs(["Por producto", "Traspasos", "Regularización"])

        with tab_prod:
            st.dataframe(df_stock, use_container_width=True, hide_index=True)

        if not df_productos_compra.empty and not df_locales_compra.empty:
            productos_dict = {int(r["id"]): str(r.get("nombre") or "") for _, r in df_productos_compra.iterrows()}
            locales_dict = {int(r["id"]): str(r.get("nombre") or "") for _, r in df_locales_compra.iterrows()}
            with tab_trasp:
                with st.form("form_traspaso_stock"):
                    c1, c2, c3 = st.columns(3)
                    producto_id = c1.selectbox("Producto", sorted(productos_dict.keys()), format_func=lambda x: productos_dict[x])
                    local_origen = c2.selectbox("Local origen", sorted(locales_dict.keys()), format_func=lambda x: locales_dict[x])
                    local_destino = c3.selectbox("Local destino", sorted(locales_dict.keys()), format_func=lambda x: locales_dict[x])
                    cantidad = c1.number_input("Cantidad", min_value=0.0, step=0.5, value=0.0)
                    fecha = c2.date_input("Fecha", value=datetime.date.today())
                    motivo = c3.text_input("Motivo", value="Traspaso interno")
                    if st.form_submit_button("Confirmar traspaso"):
                        upsert_stock_compra(
                            {
                                "producto_id": producto_id,
                                "local_id": local_origen,
                                "tipo": "traspaso_salida",
                                "cantidad": cantidad,
                                "fecha": str(fecha),
                                "motivo": f"{motivo} (salida)",
                                "local_destino_id": local_destino,
                            }
                        )
                        upsert_stock_compra(
                            {
                                "producto_id": producto_id,
                                "local_id": local_destino,
                                "tipo": "traspaso_entrada",
                                "cantidad": cantidad,
                                "fecha": str(fecha),
                                "motivo": f"{motivo} (entrada)",
                                "local_destino_id": local_destino,
                            }
                        )
                        st.success("Traspaso registrado (salida + entrada).")
                        st.rerun()

            with tab_reg:
                with st.form("form_regularizacion_stock"):
                    c1, c2, c3 = st.columns(3)
                    producto_id = c1.selectbox("Producto ", sorted(productos_dict.keys()), key="reg_prod", format_func=lambda x: productos_dict[x])
                    local_id = c2.selectbox("Local ", sorted(locales_dict.keys()), key="reg_local", format_func=lambda x: locales_dict[x])
                    conteo_real = c3.number_input("Conteo real", min_value=0.0, step=0.5, value=0.0)
                    motivo = c1.text_input("Motivo ajuste", value="Regularización inventario")
                    fecha = c2.date_input("Fecha ajuste", value=datetime.date.today())
                    if st.form_submit_button("Aplicar regularización"):
                        stock_sistema = 0.0
                        if not df_stock.empty:
                            m = df_stock[
                                (df_stock["producto_compra_id"] == producto_id) & (df_stock["local_id"] == local_id)
                            ]
                            if not m.empty:
                                stock_sistema = float(m.iloc[0].get("stock_actual") or 0)
                        diff = conteo_real - stock_sistema
                        if abs(diff) < 1e-9:
                            st.info("Sin diferencias, no se registró movimiento.")
                        else:
                            upsert_stock_compra(
                                {
                                    "producto_id": producto_id,
                                    "local_id": local_id,
                                    "tipo": "ajuste_positivo" if diff > 0 else "ajuste_negativo",
                                    "cantidad": abs(diff),
                                    "fecha": str(fecha),
                                    "motivo": motivo,
                                }
                            )
                            st.success(f"Regularización aplicada: {'+' if diff > 0 else ''}{diff:.2f}")
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

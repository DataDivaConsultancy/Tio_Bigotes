# ============================================================
# MÓDULO DE COMPRAS — Tío Bigotes
# Código Python para insertar en streamlit_app.py
# 4 pantallas: Proveedores, ProductosCompra, Locales, Stock
# ============================================================
#
# INSTRUCCIONES DE INTEGRACIÓN:
#
# 1. Añadir a TODAS_LAS_PANTALLAS:
#    "Proveedores", "ProductosCompra", "Locales", "Stock"
#
# 2. Añadir a PANTALLA_LABELS:
#    "Proveedores": "Proveedores",
#    "ProductosCompra": "Productos Compra",
#    "Locales": "Locales",
#    "Stock": "Gestión de Stock",
#
# 3. Añadir botones en Home (_btn_config):
#    "Proveedores":    ("🏭 PROVEEDORES",       "c1"),
#    "ProductosCompra":("🛒 PRODUCTOS COMPRA",   "c2"),
#    "Locales":        ("🏪 LOCALES",            "c3"),
#    "Stock":          ("📦 STOCK",              "c1"),
#
# 4. Añadir elif bloques en el dispatch (ver final de archivo)
# ============================================================


# ════════════════════════════════════════════════════════════
# ██  PANTALLA: PROVEEDORES                                ██
# ════════════════════════════════════════════════════════════

def pantalla_proveedores():
    """Gestión de proveedores: listado, alta, edición, desactivación."""
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🏭 Proveedores")

    # ── Estado de sesión para formulario ──
    if "prov_modo" not in st.session_state:
        st.session_state.prov_modo = "lista"  # lista | nuevo | editar
    if "prov_edit_id" not in st.session_state:
        st.session_state.prov_edit_id = None

    # ── Botones de acción ──
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("➕ Nuevo proveedor", use_container_width=True):
            st.session_state.prov_modo = "nuevo"
            st.session_state.prov_edit_id = None
            st.rerun()

    # ── Formulario (nuevo o editar) ──
    if st.session_state.prov_modo in ("nuevo", "editar"):
        _formulario_proveedor()
        return

    # ── Listado ──
    _listado_proveedores()


def _formulario_proveedor():
    """Formulario para crear o editar un proveedor."""
    es_edicion = st.session_state.prov_modo == "editar"
    titulo = "✏️ Editar proveedor" if es_edicion else "➕ Nuevo proveedor"
    st.subheader(titulo)

    # Cargar datos actuales si es edición
    datos = {}
    if es_edicion and st.session_state.prov_edit_id:
        try:
            res = rpc_call("rpc_crear_proveedor", {})  # dummy — usamos select directo
            # Usar fetch directo para obtener el proveedor
            base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
            api_key = st.secrets["connections"]["supabase"]["key"]
            headers = {
                "apikey": api_key,
                "Authorization": f"Bearer {api_key}",
            }
            resp = requests.get(
                f"{base_url}/rest/v1/proveedores_v2?id=eq.{st.session_state.prov_edit_id}&select=*",
                headers=headers, timeout=15,
            )
            if resp.ok and resp.json():
                datos = resp.json()[0]
        except Exception:
            pass

    FORMAS_PAGO = ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"]

    with st.form("form_proveedor", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nombre_comercial = st.text_input("Nombre comercial *", value=datos.get("nombre_comercial", ""))
            cif = st.text_input("CIF", value=datos.get("cif", ""))
            persona_contacto = st.text_input("Persona de contacto", value=datos.get("persona_contacto", ""))
            mail_contacto = st.text_input("Email contacto", value=datos.get("mail_contacto", ""))
            forma_pago = st.selectbox(
                "Forma de pago",
                FORMAS_PAGO,
                index=FORMAS_PAGO.index(datos.get("forma_pago", "")) if datos.get("forma_pago", "") in FORMAS_PAGO else 0,
            )
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
            return

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
                st.success("Proveedor guardado correctamente." if not es_edicion else "Proveedor actualizado.")
                registrar_actividad(
                    "crear_proveedor" if not es_edicion else "editar_proveedor",
                    "Proveedores",
                    {"nombre": nombre_comercial},
                )
                st.session_state.prov_modo = "lista"
                st.session_state.prov_edit_id = None
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error al guardar: {e}")


def _listado_proveedores():
    """Muestra la tabla de proveedores con acciones."""
    try:
        base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
        api_key = st.secrets["connections"]["supabase"]["key"]
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        resp = requests.get(
            f"{base_url}/rest/v1/proveedores_v2?activo=eq.true&order=nombre_comercial.asc&select=*",
            headers=headers, timeout=15,
        )
        if not resp.ok:
            st.error("Error al cargar proveedores.")
            return
        proveedores = resp.json()
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if not proveedores:
        st.info("No hay proveedores registrados. Usa el botón '➕ Nuevo proveedor' para añadir uno.")
        return

    # Búsqueda
    buscar = st.text_input("🔍 Buscar proveedor", placeholder="Nombre, CIF, contacto...")
    if buscar:
        buscar_l = buscar.lower()
        proveedores = [
            p for p in proveedores
            if buscar_l in (p.get("nombre_comercial") or "").lower()
            or buscar_l in (p.get("cif") or "").lower()
            or buscar_l in (p.get("persona_contacto") or "").lower()
        ]

    st.caption(f"{len(proveedores)} proveedores activos")

    # Tabla
    df = pd.DataFrame(proveedores)
    columnas_mostrar = [
        "nombre_comercial", "cif", "persona_contacto",
        "telefono_contacto", "mail_pedidos", "forma_pago", "plazo_pago",
    ]
    columnas_mostrar = [c for c in columnas_mostrar if c in df.columns]
    renombrar = {
        "nombre_comercial": "Nombre",
        "cif": "CIF",
        "persona_contacto": "Contacto",
        "telefono_contacto": "Teléfono",
        "mail_pedidos": "Email pedidos",
        "forma_pago": "Forma pago",
        "plazo_pago": "Plazo pago",
    }

    st.dataframe(
        df[columnas_mostrar].rename(columns=renombrar),
        use_container_width=True,
        hide_index=True,
    )

    # Selector para editar/desactivar
    nombres = {p["id"]: p["nombre_comercial"] for p in proveedores}
    opciones = [""] + [f"{v} (ID:{k})" for k, v in nombres.items()]
    seleccion = st.selectbox("Seleccionar proveedor para editar", opciones)

    if seleccion:
        prov_id = int(seleccion.split("ID:")[1].rstrip(")"))
        c_edit, c_desact = st.columns(2)
        with c_edit:
            if st.button("✏️ Editar", use_container_width=True):
                st.session_state.prov_modo = "editar"
                st.session_state.prov_edit_id = prov_id
                st.rerun()
        with c_desact:
            if st.button("🗑️ Desactivar", use_container_width=True, type="secondary"):
                try:
                    rpc_call("rpc_actualizar_proveedor", {"p_id": prov_id, "p_activo": False})
                    registrar_actividad("desactivar_proveedor", "Proveedores", {"id": prov_id})
                    st.success("Proveedor desactivado.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════
# ██  PANTALLA: PRODUCTOS COMPRA                           ██
# ════════════════════════════════════════════════════════════

def pantalla_productos_compra():
    """Gestión de productos de compra: listado, alta, edición, CSV."""
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🛒 Productos de Compra")

    if "pc_modo" not in st.session_state:
        st.session_state.pc_modo = "lista"
    if "pc_edit_id" not in st.session_state:
        st.session_state.pc_edit_id = None

    tab_lista, tab_csv = st.tabs(["📋 Listado", "📥 Importar CSV"])

    with tab_lista:
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("➕ Nuevo producto", use_container_width=True, key="btn_nuevo_pc"):
                st.session_state.pc_modo = "nuevo"
                st.session_state.pc_edit_id = None
                st.rerun()

        if st.session_state.pc_modo in ("nuevo", "editar"):
            _formulario_producto_compra()
        else:
            _listado_productos_compra()

    with tab_csv:
        _importar_csv_productos_compra()


def _cargar_proveedores_select():
    """Carga proveedores activos para selectboxes."""
    try:
        base_url = st.secrets["connections"]["supabase"]["url"].rstrip("/")
        api_key = st.secrets["connections"]["supabase"]["key"]
        headers = {"apikey": api_key, "Authorization": f"Bearer {api_key}"}
        resp = requests.get(
            f"{base_url}/rest/v1/proveedores_v2?activo=eq.true&order=nombre_comercial.asc&select=id,nombre_comercial,forma_pago,plazo_pago",
            headers=headers, timeout=15,
        )
        return resp.json() if resp.ok else []
    except Exception:
        return []


def _supabase_get(table, params="", select="*"):
    """Helper GET genérico para tablas Supabase."""
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


def _formulario_producto_compra():
    """Formulario crear/editar producto de compra."""
    es_edicion = st.session_state.pc_modo == "editar"
    st.subheader("✏️ Editar producto" if es_edicion else "➕ Nuevo producto de compra")

    datos = {}
    if es_edicion and st.session_state.pc_edit_id:
        rows = _supabase_get("productos_compra_v2", f"id=eq.{st.session_state.pc_edit_id}")
        if rows:
            datos = rows[0]

    proveedores = _cargar_proveedores_select()
    prov_opciones = ["(Sin proveedor)"] + [p["nombre_comercial"] for p in proveedores]
    prov_ids = [None] + [p["id"] for p in proveedores]

    # Buscar índice del proveedor actual
    prov_idx = 0
    if datos.get("proveedor_id"):
        for i, pid in enumerate(prov_ids):
            if pid == datos["proveedor_id"]:
                prov_idx = i
                break

    TIPOS_IVA = ["", "General 21%", "Reducido 10%", "Superreducido 4%", "Exento 0%"]
    FORMAS_PAGO = ["", "SEPA", "Transferencia", "T. Credito", "Efectivo"]
    UNIDADES = ["", "kg", "unidad", "litro", "caja", "bolsa", "paquete", "metro"]

    with st.form("form_producto_compra", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            nombre = st.text_input("Nombre *", value=datos.get("nombre", ""))
            cod_interno = st.text_input("Código interno", value=datos.get("cod_interno", ""))
            proveedor_sel = st.selectbox("Proveedor", prov_opciones, index=prov_idx)
            precio = st.number_input("Precio", value=float(datos.get("precio") or 0), min_value=0.0, step=0.01, format="%.2f")
            tipo_iva = st.selectbox(
                "Tipo IVA",
                TIPOS_IVA,
                index=TIPOS_IVA.index(datos.get("tipo_iva", "")) if datos.get("tipo_iva", "") in TIPOS_IVA else 0,
            )
        with c2:
            cod_proveedor = st.text_input("Código proveedor", value=datos.get("cod_proveedor", ""))
            medidas = st.text_input("Medidas", value=datos.get("medidas", ""))
            color = st.text_input("Color", value=datos.get("color", ""))
            unidad_medida = st.selectbox(
                "Unidad de medida",
                UNIDADES,
                index=UNIDADES.index(datos.get("unidad_medida", "")) if datos.get("unidad_medida", "") in UNIDADES else 0,
            )
            unidad_minima = st.number_input("Unidad mínima compra", value=float(datos.get("unidad_minima_compra") or 0), min_value=0.0, step=1.0)
        with c3:
            dia_pedido = st.text_input("Día(s) pedido", value=datos.get("dia_pedido", ""), placeholder="Lunes,Miércoles")
            dia_entrega = st.text_input("Día(s) entrega", value=datos.get("dia_entrega", ""), placeholder="Martes,Jueves")
            forma_pago = st.selectbox(
                "Forma de pago (producto)",
                FORMAS_PAGO,
                index=FORMAS_PAGO.index(datos.get("forma_pago", "")) if datos.get("forma_pago", "") in FORMAS_PAGO else 0,
                help="Si se deja vacío, hereda del proveedor",
            )
            plazo_pago = st.text_input("Plazo de pago (producto)", value=datos.get("plazo_pago", ""),
                                        help="Si se deja vacío, hereda del proveedor")
            stock_minimo = st.number_input("Stock mínimo alerta", value=float(datos.get("stock_minimo") or 0), min_value=0.0, step=1.0)

        col_s, col_c = st.columns([1, 3])
        with col_s:
            submitted = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
        with col_c:
            cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

    if cancelar:
        st.session_state.pc_modo = "lista"
        st.session_state.pc_edit_id = None
        st.rerun()

    if submitted:
        if not nombre.strip():
            st.error("El nombre es obligatorio.")
            return

        prov_id_sel = prov_ids[prov_opciones.index(proveedor_sel)] if proveedor_sel != "(Sin proveedor)" else None

        params = {
            "p_nombre": nombre.strip(),
            "p_proveedor_id": prov_id_sel,
            "p_cod_proveedor": cod_proveedor.strip() or None,
            "p_cod_interno": cod_interno.strip() or None,
            "p_medidas": medidas.strip() or None,
            "p_color": color.strip() or None,
            "p_unidad_medida": unidad_medida or None,
            "p_unidad_minima_compra": unidad_minima if unidad_minima > 0 else None,
            "p_dia_pedido": dia_pedido.strip() or None,
            "p_dia_entrega": dia_entrega.strip() or None,
            "p_precio": precio if precio > 0 else None,
            "p_tipo_iva": tipo_iva or None,
            "p_forma_pago": forma_pago or None,
            "p_plazo_pago": plazo_pago.strip() or None,
            "p_stock_minimo": stock_minimo if stock_minimo > 0 else 0,
        }

        try:
            if es_edicion:
                params["p_id"] = st.session_state.pc_edit_id
                res = rpc_call("rpc_actualizar_producto_compra", params)
            else:
                res = rpc_call("rpc_crear_producto_compra", params)

            resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
            if resultado.get("ok"):
                st.success("Producto guardado." if not es_edicion else "Producto actualizado.")
                registrar_actividad(
                    "crear_producto_compra" if not es_edicion else "editar_producto_compra",
                    "ProductosCompra",
                    {"nombre": nombre},
                )
                st.session_state.pc_modo = "lista"
                st.session_state.pc_edit_id = None
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error: {e}")


def _listado_productos_compra():
    """Tabla de productos de compra con filtros."""
    productos = _supabase_get(
        "productos_compra_v2",
        "activo=eq.true&order=nombre.asc",
        "id,cod_interno,nombre,medidas,color,unidad_medida,unidad_minima_compra,dia_pedido,dia_entrega,proveedor_id,precio,tipo_iva,forma_pago,plazo_pago,stock_minimo",
    )
    proveedores = _cargar_proveedores_select()
    prov_map = {p["id"]: p["nombre_comercial"] for p in proveedores}

    if not productos:
        st.info("No hay productos de compra. Usa '➕ Nuevo producto' o importa un CSV.")
        return

    # Enriquecer con nombre proveedor
    for p in productos:
        p["proveedor"] = prov_map.get(p.get("proveedor_id"), "—")

    # Filtros
    f1, f2 = st.columns(2)
    with f1:
        buscar = st.text_input("🔍 Buscar producto", placeholder="Nombre, código...", key="buscar_pc")
    with f2:
        filtro_prov = st.selectbox("Filtrar por proveedor", ["Todos"] + list(prov_map.values()), key="filtro_prov_pc")

    if buscar:
        buscar_l = buscar.lower()
        productos = [p for p in productos if buscar_l in (p.get("nombre") or "").lower() or buscar_l in (p.get("cod_interno") or "").lower()]
    if filtro_prov != "Todos":
        productos = [p for p in productos if p.get("proveedor") == filtro_prov]

    st.caption(f"{len(productos)} productos")

    df = pd.DataFrame(productos)
    cols_show = ["cod_interno", "nombre", "proveedor", "precio", "unidad_medida", "dia_pedido", "dia_entrega", "forma_pago", "plazo_pago"]
    cols_show = [c for c in cols_show if c in df.columns]
    renombrar = {
        "cod_interno": "Código", "nombre": "Nombre", "proveedor": "Proveedor",
        "precio": "Precio", "unidad_medida": "Unidad", "dia_pedido": "Día pedido",
        "dia_entrega": "Día entrega", "forma_pago": "Forma pago", "plazo_pago": "Plazo pago",
    }
    st.dataframe(df[cols_show].rename(columns=renombrar), use_container_width=True, hide_index=True)

    # Selector para editar
    nombres = {p["id"]: f"{p.get('cod_interno', '')} - {p['nombre']}" for p in productos}
    opciones = [""] + [f"{v} (ID:{k})" for k, v in nombres.items()]
    seleccion = st.selectbox("Seleccionar producto para editar", opciones, key="sel_edit_pc")

    if seleccion:
        pc_id = int(seleccion.split("ID:")[1].rstrip(")"))
        c_edit, c_desact = st.columns(2)
        with c_edit:
            if st.button("✏️ Editar", use_container_width=True, key="btn_edit_pc"):
                st.session_state.pc_modo = "editar"
                st.session_state.pc_edit_id = pc_id
                st.rerun()
        with c_desact:
            if st.button("🗑️ Desactivar", use_container_width=True, key="btn_desact_pc"):
                try:
                    rpc_call("rpc_actualizar_producto_compra", {"p_id": pc_id, "p_activo": False})
                    registrar_actividad("desactivar_producto_compra", "ProductosCompra", {"id": pc_id})
                    st.success("Producto desactivado.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


def _importar_csv_productos_compra():
    """Importación masiva de productos vía CSV."""
    st.subheader("📥 Importar productos desde CSV")
    st.markdown("""
    **Formato esperado del CSV** (separador `;` o `,`):

    `cod_proveedor;cod_interno;nombre;medidas;color;unidad_medida;unidad_minima_compra;dia_pedido;dia_entrega;proveedor;precio;tipo_iva`

    - **proveedor**: nombre comercial (debe existir en la tabla de proveedores)
    - **tipo_iva**: `General 21%`, `Reducido 10%`, `Superreducido 4%`, `Exento 0%`
    """)

    archivo = st.file_uploader("Seleccionar archivo CSV", type=["csv"], key="csv_pc_upload")

    if archivo:
        try:
            contenido = archivo.read().decode("utf-8")
            # Detectar separador
            sep = ";" if ";" in contenido.split("\n")[0] else ","
            df = pd.read_csv(io.StringIO(contenido), sep=sep, dtype=str)
            df = df.fillna("")

            st.write(f"**{len(df)} filas detectadas**")
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)

            if st.button("🚀 Importar productos", type="primary", key="btn_importar_csv"):
                rows_json = []
                for _, row in df.iterrows():
                    r = {}
                    for col in df.columns:
                        val = str(row[col]).strip()
                        r[col.strip().lower()] = val if val else None
                    rows_json.append(r)

                try:
                    import json as _json
                    res = rpc_call("rpc_upsert_productos_compra_batch", {"p_rows": _json.dumps(rows_json)})
                    resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
                    if resultado.get("ok"):
                        st.success(f"Importación completada: {resultado.get('procesados', 0)} productos procesados.")
                        registrar_actividad("importar_csv_productos", "ProductosCompra", {"filas": len(rows_json)})
                    else:
                        st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
                except Exception as e:
                    st.error(f"Error en la importación: {e}")
        except Exception as e:
            st.error(f"Error leyendo CSV: {e}")


# ════════════════════════════════════════════════════════════
# ██  PANTALLA: LOCALES                                    ██
# ════════════════════════════════════════════════════════════

def pantalla_locales():
    """Gestión de locales para stock y traspasos."""
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("🏪 Locales")

    if "loc_modo" not in st.session_state:
        st.session_state.loc_modo = "lista"
    if "loc_edit_id" not in st.session_state:
        st.session_state.loc_edit_id = None

    col_a, _ = st.columns([1, 5])
    with col_a:
        if st.button("➕ Nuevo local", use_container_width=True):
            st.session_state.loc_modo = "nuevo"
            st.session_state.loc_edit_id = None
            st.rerun()

    if st.session_state.loc_modo in ("nuevo", "editar"):
        _formulario_local()
        return

    _listado_locales()


def _formulario_local():
    """Formulario crear/editar local."""
    es_edicion = st.session_state.loc_modo == "editar"
    st.subheader("✏️ Editar local" if es_edicion else "➕ Nuevo local")

    datos = {}
    if es_edicion and st.session_state.loc_edit_id:
        rows = _supabase_get("locales_compra_v2", f"id=eq.{st.session_state.loc_edit_id}")
        if rows:
            datos = rows[0]

    with st.form("form_local", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre del local *", value=datos.get("nombre", ""))
            direccion = st.text_input("Dirección", value=datos.get("direccion", ""))
        with c2:
            telefono = st.text_input("Teléfono", value=datos.get("telefono", ""))
            transporte = st.text_input("Transporte", value=datos.get("transporte", ""),
                                        placeholder="Furgoneta propia, Mensajería...")

        col_s, col_c = st.columns([1, 3])
        with col_s:
            submitted = st.form_submit_button("💾 Guardar", use_container_width=True, type="primary")
        with col_c:
            cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)

    if cancelar:
        st.session_state.loc_modo = "lista"
        st.session_state.loc_edit_id = None
        st.rerun()

    if submitted:
        if not nombre.strip():
            st.error("El nombre es obligatorio.")
            return
        params = {
            "p_nombre": nombre.strip(),
            "p_direccion": direccion.strip() or None,
            "p_telefono": telefono.strip() or None,
            "p_transporte": transporte.strip() or None,
        }
        try:
            if es_edicion:
                params["p_id"] = st.session_state.loc_edit_id
                res = rpc_call("rpc_actualizar_local_compra", params)
            else:
                res = rpc_call("rpc_crear_local_compra", params)

            resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
            if resultado.get("ok"):
                st.success("Local guardado." if not es_edicion else "Local actualizado.")
                registrar_actividad(
                    "crear_local" if not es_edicion else "editar_local",
                    "Locales", {"nombre": nombre},
                )
                st.session_state.loc_modo = "lista"
                st.session_state.loc_edit_id = None
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error: {e}")


def _listado_locales():
    """Tabla de locales."""
    locales = _supabase_get("locales_compra_v2", "activo=eq.true&order=nombre.asc")

    if not locales:
        st.info("No hay locales registrados.")
        return

    st.caption(f"{len(locales)} locales activos")
    df = pd.DataFrame(locales)
    cols = ["nombre", "direccion", "telefono", "transporte"]
    cols = [c for c in cols if c in df.columns]
    renombrar = {"nombre": "Nombre", "direccion": "Dirección", "telefono": "Teléfono", "transporte": "Transporte"}
    st.dataframe(df[cols].rename(columns=renombrar), use_container_width=True, hide_index=True)

    nombres = {l["id"]: l["nombre"] for l in locales}
    opciones = [""] + [f"{v} (ID:{k})" for k, v in nombres.items()]
    seleccion = st.selectbox("Seleccionar local para editar", opciones)

    if seleccion:
        loc_id = int(seleccion.split("ID:")[1].rstrip(")"))
        c_edit, c_desact = st.columns(2)
        with c_edit:
            if st.button("✏️ Editar", use_container_width=True, key="btn_edit_loc"):
                st.session_state.loc_modo = "editar"
                st.session_state.loc_edit_id = loc_id
                st.rerun()
        with c_desact:
            if st.button("🗑️ Desactivar", use_container_width=True, key="btn_desact_loc"):
                try:
                    rpc_call("rpc_actualizar_local_compra", {"p_id": loc_id, "p_activo": False})
                    registrar_actividad("desactivar_local", "Locales", {"id": loc_id})
                    st.success("Local desactivado.")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════
# ██  PANTALLA: GESTIÓN DE STOCK                           ██
# ════════════════════════════════════════════════════════════

def pantalla_stock():
    """Pantalla principal de stock con sub-tabs."""
    st.button("⬅️ VOLVER", on_click=ir_a, args=("Home",))
    st.header("📦 Gestión de Stock")

    tabs = st.tabs([
        "📊 Por producto",
        "🏭 Por proveedor",
        "📈 Stock vs Sell-out",
        "🔮 Previsión semanal",
        "🔄 Traspasos",
        "✅ Regularización",
        "📜 Historial",
    ])

    with tabs[0]:
        _stock_por_producto()
    with tabs[1]:
        _stock_por_proveedor()
    with tabs[2]:
        _stock_vs_sellout()
    with tabs[3]:
        _prevision_semanal()
    with tabs[4]:
        _stock_traspasos()
    with tabs[5]:
        _stock_regularizacion()
    with tabs[6]:
        _stock_historial()


def _cargar_stock_actual():
    """Carga vista vw_stock_actual."""
    return _supabase_get("vw_stock_actual", "order=producto_nombre.asc")


def _cargar_locales():
    """Carga locales activos."""
    return _supabase_get("locales_compra_v2", "activo=eq.true&order=nombre.asc")


def _cargar_productos_compra():
    """Carga productos de compra activos."""
    return _supabase_get("productos_compra_v2", "activo=eq.true&order=nombre.asc", "id,nombre,cod_interno,proveedor_id,unidad_medida")


def _stock_por_producto():
    """Sub-tab: stock actual por producto."""
    st.subheader("Stock actual por producto")

    stock = _cargar_stock_actual()
    locales = _cargar_locales()

    if not stock:
        st.info("No hay movimientos de stock registrados.")
        return

    # Filtro por local
    local_nombres = ["Todos"] + [l["nombre"] for l in locales]
    local_ids = [None] + [l["id"] for l in locales]
    filtro_local = st.selectbox("📍 Local", local_nombres, key="stock_local_prod")

    if filtro_local != "Todos":
        lid = local_ids[local_nombres.index(filtro_local)]
        stock = [s for s in stock if s.get("local_id") == lid]

    # Alertas: stock bajo mínimo
    alertas = [s for s in stock if s.get("stock_actual", 0) <= s.get("stock_minimo", 0) and s.get("stock_minimo", 0) > 0]
    if alertas:
        with st.expander(f"⚠️ {len(alertas)} productos bajo stock mínimo", expanded=True):
            for a in alertas:
                st.warning(f"**{a['producto_nombre']}** — Stock: {a['stock_actual']} {a.get('unidad_medida','')} (Mín: {a['stock_minimo']})")

    # Métricas
    total_refs = len(set(s["producto_compra_id"] for s in stock))
    total_uds = sum(float(s.get("stock_actual", 0)) for s in stock)
    total_valor = sum(float(s.get("stock_actual", 0)) * float(s.get("precio") or 0) for s in stock)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Referencias", f"{total_refs}")
    m2.metric("Unidades totales", f"{total_uds:,.0f}")
    m3.metric("Valor estimado", f"{total_valor:,.2f} €")
    m4.metric("Alertas", f"{len(alertas)}")

    # Tabla
    df = pd.DataFrame(stock)
    cols = ["producto_nombre", "cod_interno", "local_nombre", "stock_actual", "stock_minimo", "unidad_medida", "proveedor_nombre", "ultimo_movimiento"]
    cols = [c for c in cols if c in df.columns]
    renombrar = {
        "producto_nombre": "Producto", "cod_interno": "Código",
        "local_nombre": "Local", "stock_actual": "Stock",
        "stock_minimo": "Mínimo", "unidad_medida": "Unidad",
        "proveedor_nombre": "Proveedor", "ultimo_movimiento": "Últ. movimiento",
    }
    st.dataframe(df[cols].rename(columns=renombrar), use_container_width=True, hide_index=True)

    # Registrar entrada/salida rápida
    st.divider()
    st.subheader("📥 Registrar movimiento")
    _formulario_movimiento_rapido(stock, locales)


def _formulario_movimiento_rapido(stock, locales):
    """Formulario rápido para registrar entrada/salida."""
    productos = _cargar_productos_compra()
    if not productos or not locales:
        st.info("Necesitas al menos un producto y un local para registrar movimientos.")
        return

    with st.form("form_movimiento_rapido", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            prod_opciones = [f"{p.get('cod_interno', '')} - {p['nombre']}" for p in productos]
            prod_sel = st.selectbox("Producto", prod_opciones, key="mov_prod")
            tipo_mov = st.selectbox("Tipo", ["entrada", "salida", "merma"], key="mov_tipo")
        with c2:
            local_opciones = [l["nombre"] for l in locales]
            local_sel = st.selectbox("Local", local_opciones, key="mov_local")
            cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0, key="mov_cant")
        with c3:
            motivo = st.text_input("Motivo", key="mov_motivo", placeholder="Recepción pedido, Merma...")
            fecha = st.date_input("Fecha", value=datetime.date.today(), key="mov_fecha")

        submitted = st.form_submit_button("✅ Registrar movimiento", type="primary", use_container_width=True)

    if submitted:
        prod_id = productos[prod_opciones.index(prod_sel)]["id"]
        local_id = locales[local_opciones.index(local_sel)]["id"]
        user = get_user()

        try:
            res = rpc_call("rpc_registrar_movimiento_stock", {
                "p_producto_compra_id": prod_id,
                "p_local_id": local_id,
                "p_tipo": tipo_mov,
                "p_cantidad": float(cantidad),
                "p_motivo": motivo.strip() or None,
                "p_fecha": fecha.isoformat(),
                   "p_usuario_id": user["id"] if user else None,
            })
            resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
            if resultado.get("ok"):
                st.success(f"Movimiento registrado: {tipo_mov} de {cantidad} uds.")
                registrar_actividad("registrar_movimiento", "Stock", {"tipo": tipo_mov, "cantidad": float(cantidad)})
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error: {e}")


def _stock_por_proveedor():
    """Sub-tab: stock agrupado por proveedor."""
    st.subheader("Stock por proveedor")
    stock = _cargar_stock_actual()
    if not stock:
        st.info("Sin datos de stock.")
        return

    # Agrupar por proveedor
    por_prov = {}
    for s in stock:
        prov = s.get("proveedor_nombre") or "Sin proveedor"
        if prov not in por_prov:
            por_prov[prov] = {"referencias": 0, "unidades": 0, "valor": 0}
        por_prov[prov]["referencias"] += 1
        por_prov[prov]["unidades"] += float(s.get("stock_actual", 0))
        por_prov[prov]["valor"] += float(s.get("stock_actual", 0)) * float(s.get("precio") or 0)

    rows = [
        {"Proveedor": k, "Referencias": v["referencias"], "Unidades": f"{v['unidades']:,.0f}", "Valor (€)": f"{v['valor']:,.2f}"}
        for k, v in sorted(por_prov.items())
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _stock_vs_sellout():
    """Sub-tab: comparativa stock actual vs ventas."""
    st.subheader("Stock vs Sell-out")
    st.info("Esta vista compara stock actual con el ritmo de ventas. Requiere datos de ventas vinculados a productos de compra (producto_venta_id).")

    stock = _cargar_stock_actual()
    if not stock:
        st.info("Sin datos de stock.")
        return

    # Mostrar productos con producto_venta_id vinculado
    vinculados = [s for s in stock if s.get("producto_venta_id")]
    if not vinculados:
        st.warning("No hay productos de compra vinculados a productos de venta. Configura 'producto_venta_id' en los productos de compra.")
        return

    # Para cada producto vinculado, calcular días de cobertura estimados
    # Usar venta media del último mes como referencia
    fecha_fin = datetime.date.today()
    fecha_ini = fecha_fin - datetime.timedelta(days=30)

    rows = []
    for s in vinculados:
        vid = s["producto_venta_id"]
        try:
            ventas = _supabase_get(
                "ventas_raw_v2",
                f"producto_id=eq.{vid}&fecha=gte.{fecha_ini.isoformat()}&fecha=lte.{fecha_fin.isoformat()}",
                "uds_vendidas",
            )
            total_vendido = sum(float(v.get("uds_vendidas", 0)) for v in ventas) if ventas else 0
            media_diaria = total_vendido / 30 if total_vendido > 0 else 0
            stock_actual = float(s.get("stock_actual", 0))
            dias_cobertura = int(stock_actual / media_diaria) if media_diaria > 0 else 999

            rows.append({
                "Producto": s["producto_nombre"],
                "Stock actual": f"{stock_actual:,.0f}",
                "Venta/día (30d)": f"{media_diaria:,.1f}",
                "Días cobertura": dias_cobertura if dias_cobertura < 999 else "∞",
                "Estado": "🔴 Crítico" if dias_cobertura <= 2 else "🟡 Bajo" if dias_cobertura <= 5 else "🟢 OK",
            })
        except Exception:
            continue

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No se pudieron calcular datos de sell-out.")


def _prevision_semanal():
    """Sub-tab: previsión de necesidades para la próxima semana con alarma inteligente."""
    st.subheader("🔮 Previsión semanal — Alarma inteligente")
    st.caption("Calcula el punto de reorden basado en lead time (día pedido → día entrega + 1 día seguridad) × venta media diaria")

    stock = _cargar_stock_actual()
    if not stock:
        st.info("Sin datos de stock.")
        return

    DIAS_SEMANA = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}

    hoy = datetime.date.today()
    rows_alarma = []

    for s in stock:
        vid = s.get("producto_venta_id")
        if not vid:
            continue

        # Calcular lead time en días
        dia_pedido_str = s.get("dia_pedido", "")
        dia_entrega_str = s.get("dia_entrega", "")
        if not dia_pedido_str or not dia_entrega_str:
            continue

        # Tomar el primer día de pedido y entrega
        dp = dia_pedido_str.split(",")[0].strip()
        de = dia_entrega_str.split(",")[0].strip()
        dp_num = DIAS_SEMANA.get(dp)
        de_num = DIAS_SEMANA.get(de)
        if dp_num is None or de_num is None:
            continue

        lead_time = (de_num - dp_num) % 7
        if lead_time == 0:
            lead_time = 7  # Si es el mismo día, asumir una semana
        lead_time += 1  # +1 día de seguridad

        # Calcular venta media diaria (últimos 30 días)
        try:
            fecha_ini = hoy - datetime.timedelta(days=30)
            ventas = _supabase_get(
                "ventas_raw_v2",
                f"producto_id=eq.{vid}&fecha=gte.{fecha_ini.isoformat()}&fecha=lte.{hoy.isoformat()}",
                "uds_vendidas",
            )
            total_vendido = sum(float(v.get("uds_vendidas", 0)) for v in ventas) if ventas else 0
            venta_media = total_vendido / 30 if total_vendido > 0 else 0
        except Exception:
            venta_media = 0

        stock_actual = float(s.get("stock_actual", 0))
        punto_reorden = venta_media * lead_time
        necesidad = max(0, punto_reorden - stock_actual)

        if necesidad > 0 or stock_actual <= punto_reorden:
            rows_alarma.append({
                "Producto": s["producto_nombre"],
                "Stock actual": f"{stock_actual:,.0f}",
                "Venta/día": f"{venta_media:,.1f}",
                "Lead time": f"{lead_time} días",
                "Punto reorden": f"{punto_reorden:,.0f}",
                "Pedir": f"{max(0, int(np.ceil(necesidad))):,}",
                "Día pedido": dia_pedido_str,
                "Proveedor": s.get("proveedor_nombre", "—"),
                "Urgencia": "🔴" if stock_actual <= venta_media else "🟡" if stock_actual <= punto_reorden else "🟢",
            })

    if rows_alarma:
        # Ordenar por urgencia
        orden_urg = {"🔴": 0, "🟡": 1, "🟢": 2}
        rows_alarma.sort(key=lambda r: orden_urg.get(r["Urgencia"], 3))
        st.dataframe(pd.DataFrame(rows_alarma), use_container_width=True, hide_index=True)

        n_criticos = sum(1 for r in rows_alarma if r["Urgencia"] == "🔴")
        n_bajos = sum(1 for r in rows_alarma if r["Urgencia"] == "🟡")
        m1, m2, m3 = st.columns(3)
        m1.metric("Críticos", f"{n_criticos}", delta=None)
        m2.metric("Bajo mínimo", f"{n_bajos}", delta=None)
        m3.metric("Total a pedir", f"{len(rows_alarma)} productos")
    else:
        st.success("Todos los productos tienen stock suficiente para el lead time previsto.")


def _stock_traspasos():
    """Sub-tab: traspasos entre locales."""
    st.subheader("🔄 Traspaso entre locales")

    productos = _cargar_productos_compra()
    locales = _cargar_locales()

    if not productos or len(locales) < 2:
        st.info("Necesitas al menos 2 locales y 1 producto para hacer traspasos.")
        return

    with st.form("form_traspaso", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            prod_opciones = [f"{p.get('cod_interno', '')} - {p['nombre']}" for p in productos]
            prod_sel = st.selectbox("Producto", prod_opciones, key="trasp_prod")
            local_origen = st.selectbox("Local origen", [l["nombre"] for l in locales], key="trasp_origen")
        with c2:
            cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0, key="trasp_cant")
            local_destino = st.selectbox("Local destino", [l["nombre"] for l in locales], key="trasp_destino")

        motivo = st.text_input("Motivo", key="trasp_motivo", placeholder="Reposición, Evento especial...")
        submitted = st.form_submit_button("🔄 Ejecutar traspaso", type="primary", use_container_width=True)

    if submitted:
        if local_origen == local_destino:
            st.error("El local origen y destino no pueden ser el mismo.")
            return

        prod_id = productos[prod_opciones.index(prod_sel)]["id"]
        origen_id = locales[[l["nombre"] for l in locales].index(local_origen)]["id"]
        destino_id = locales[[l["nombre"] for l in locales].index(local_destino)]["id"]
        user = get_user()

        try:
            res = rpc_call("rpc_traspaso_stock", {
                "p_producto_compra_id": prod_id,
                "p_local_origen_id": origen_id,
                "p_local_destino_id": destino_id,
                "p_cantidad": float(cantidad),
                "p_motivo": motivo.strip() or None,
                "p_fecha": datetime.date.today().isoformat(),
                "p_usuario_id": user["id"] if user else None,
            })
            resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
            if resultado.get("ok"):
                st.success(f"Traspaso completado: {cantidad} uds de {local_origen} → {local_destino}")
                registrar_actividad("traspaso_stock", "Stock", {
                    "origen": local_origen, "destino": local_destino, "cantidad": float(cantidad),
                })
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error: {e}")

    # Historial de traspasos recientes
    st.divider()
    st.caption("Últimos traspasos")
    traspasos = _supabase_get(
        "stock_movimientos_v2",
        "tipo=eq.traspaso_salida&order=created_at.desc&limit=20",
        "id,producto_compra_id,local_id,local_destino_id,cantidad,motivo,fecha,created_at",
    )
    if traspasos:
        # Enriquecer con nombres
        prods = {p["id"]: p["nombre"] for p in _cargar_productos_compra()}
        locs = {l["id"]: l["nombre"] for l in _cargar_locales()}
        rows = []
        for t in traspasos:
            rows.append({
                "Fecha": t.get("fecha", ""),
                "Producto": prods.get(t.get("producto_compra_id"), "?"),
                "Origen": locs.get(t.get("local_id"), "?"),
                "Destino": locs.get(t.get("local_destino_id"), "?"),
                "Cantidad": t.get("cantidad", 0),
                "Motivo": t.get("motivo", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No hay traspasos registrados.")


def _stock_regularizacion():
    """Sub-tab: regularización masiva de stock (inventario)."""
    st.subheader("✅ Regularización de stock (Inventario)")
    st.caption("Introduce el conteo real de cada producto. El sistema calculará las diferencias y creará los ajustes necesarios.")

    locales = _cargar_locales()
    if not locales:
        st.info("No hay locales registrados.")
        return

    local_sel = st.selectbox("📍 Local a regularizar", [l["nombre"] for l in locales], key="reg_local")
    local_id = locales[[l["nombre"] for l in locales].index(local_sel)]["id"]

    # Cargar stock actual de ese local
    stock = [s for s in _cargar_stock_actual() if s.get("local_id") == local_id]

    if not stock:
        st.info("No hay stock registrado en este local.")
        return

    st.write(f"**{len(stock)} productos con stock en {local_sel}**")

    # Formulario de conteo
    with st.form("form_regularizacion"):
        conteos = {}
        for s in stock:
            pid = s["producto_compra_id"]
            nombre = s["producto_nombre"]
            stock_actual = float(s.get("stock_actual", 0))
            unidad = s.get("unidad_medida", "uds")

            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.write(f"**{nombre}** (stock sistema: {stock_actual:,.0f} {unidad})")
            with c2:
                conteo = st.number_input(
                    f"Conteo real", value=float(stock_actual), step=1.0,
                    key=f"reg_{pid}", label_visibility="collapsed",
                )
            with c3:
                diff = conteo - stock_actual
                if diff != 0:
                    color = "red" if diff < 0 else "green"
                    st.markdown(f"<span style='color:{color}; font-weight:bold'>{diff:+,.0f}</span>", unsafe_allow_html=True)
                else:
                    st.write("—")
            conteos[pid] = conteo

        motivo_reg = st.text_input("Motivo de la regularización", value="Inventario físico", key="reg_motivo")
        submitted = st.form_submit_button("✅ Aplicar regularización", type="primary", use_container_width=True)

    if submitted:
        import json as _json
        ajustes = []
        for s in stock:
            pid = s["producto_compra_id"]
            conteo = conteos.get(pid, float(s.get("stock_actual", 0)))
            if conteo != float(s.get("stock_actual", 0)):
                ajustes.append({
                    "producto_compra_id": pid,
                    "local_id": local_id,
                    "conteo_real": conteo,
                    "motivo": motivo_reg,
                })

        if not ajustes:
            st.info("No hay diferencias que ajustar.")
            return

        user = get_user()
        try:
            res = rpc_call("rpc_regularizar_stock", {
                "p_ajustes": _json.dumps(ajustes),
                "p_usuario_id": user["id"] if user else None,
            })
            resultado = res if isinstance(res, dict) else (res[0] if isinstance(res, list) and res else {})
            if resultado.get("ok"):
                n = resultado.get("ajustes_aplicados", 0)
                st.success(f"Regularización completada: {n} ajustes aplicados.")
                registrar_actividad("regularizacion_stock", "Stock", {"local": local_sel, "ajustes": n})
                time.sleep(0.5)
                st.rerun()
            else:
                st.error(f"Error: {resultado.get('error', 'Error desconocido')}")
        except Exception as e:
            st.error(f"Error: {e}")


def _stock_historial():
    """Sub-tab: historial de todos los movimientos de stock."""
    st.subheader("📜 Historial de movimientos")

    # Filtros
    f1, f2, f3 = st.columns(3)
    with f1:
        fecha_desde = st.date_input("Desde", value=datetime.date.today() - datetime.timedelta(days=30), key="hist_desde")
    with f2:
        fecha_hasta = st.date_input("Hasta", value=datetime.date.today(), key="hist_hasta")
    with f3:
        tipos = ["Todos", "entrada", "salida", "merma", "ajuste_positivo", "ajuste_negativo", "traspaso_entrada", "traspaso_salida", "venta_auto"]
        tipo_filtro = st.selectbox("Tipo", tipos, key="hist_tipo")

    # Cargar movimientos
    params = f"fecha=gte.{fecha_desde.isoformat()}&fecha=lte.{fecha_hasta.isoformat()}&order=created_at.desc&limit=500"
    if tipo_filtro != "Todos":
        params += f"&tipo=eq.{tipo_filtro}"

    movimientos = _supabase_get(
        "stock_movimientos_v2",
        params,
        "id,producto_compra_id,local_id,tipo,cantidad,motivo,fecha,usuario_id,local_destino_id,created_at",
    )

    if not movimientos:
        st.info("No hay movimientos en el período seleccionado.")
        return

    # Enriquecer
    prods = {p["id"]: p["nombre"] for p in _cargar_productos_compra()}
    locs = {l["id"]: l["nombre"] for l in _cargar_locales()}

    TIPO_EMOJI = {
        "entrada": "📥", "salida": "📤", "merma": "🗑️",
        "ajuste_positivo": "➕", "ajuste_negativo": "➖",
        "traspaso_entrada": "🔄📥", "traspaso_salida": "🔄📤",
        "venta_auto": "💰",
    }

    rows = []
    for m in movimientos:
        tipo = m.get("tipo", "")
        rows.append({
            "Fecha": m.get("fecha", ""),
            "Tipo": f"{TIPO_EMOJI.get(tipo, '')} {tipo}",
            "Producto": prods.get(m.get("producto_compra_id"), "?"),
            "Local": locs.get(m.get("local_id"), "?"),
            "Cantidad": m.get("cantidad", 0),
            "Motivo": m.get("motivo", ""),
        })

    st.caption(f"{len(rows)} movimientos")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Resumen por tipo
    st.divider()
    st.caption("Resumen por tipo")
    resumen = {}
    for m in movimientos:
        t = m.get("tipo", "?")
        resumen[t] = resumen.get(t, 0) + float(m.get("cantidad", 0))
    st.dataframe(
        pd.DataFrame([{"Tipo": k, "Total": f"{v:,.0f}"} for k, v in sorted(resumen.items())]),
        use_container_width=True, hide_index=True,
    )


# ════════════════════════════════════════════════════════════
# ██  CÓDIGO DE INTEGRACIÓN                                ██
# ════════════════════════════════════════════════════════════
#
# Copiar estos bloques elif al final de la cadena de dispatch
# (después de los elif existentes de Auditoria):
#
# elif st.session_state.pantalla == "Proveedores":
#     if not user_has_access("Proveedores"):
#         st.error("No tienes acceso a esta sección.")
#         st.stop()
#     pantalla_proveedores()
#
# elif st.session_state.pantalla == "ProductosCompra":
#     if not user_has_access("ProductosCompra"):
#         st.error("No tienes acceso a esta sección.")
#         st.stop()
#     pantalla_productos_compra()
#
# elif st.session_state.pantalla == "Locales":
#     if not user_has_access("Locales"):
#         st.error("No tienes acceso a esta sección.")
#         st.stop()
#     pantalla_locales()
#
# elif st.session_state.pantalla == "Stock":
#     if not user_has_access("Stock"):
#         st.error("No tienes acceso a esta sección.")
#         st.stop()
#     pantalla_stock()
#
# ════════════════════════════════════════════════════════════
# Y añadir a TODAS_LAS_PANTALLAS:
#
# TODAS_LAS_PANTALLAS = [
#     "Productos", "Empleados", "Operativa", "BI",
#     "Forecast", "Pendientes", "CargaVentas", "Auditoria",
#     "Proveedores", "ProductosCompra", "Locales", "Stock",  # ← NUEVO
# ]
#
# PANTALLA_LABELS = {
#     ...existentes...,
#     "Proveedores": "Proveedores",                          # ← NUEVO
#     "ProductosCompra": "Productos Compra",                 # ← NUEVO
#     "Locales": "Locales",                                  # ← NUEVO
#     "Stock": "Gestión de Stock",                           # ← NUEVO
# }
#
# Y en Home, añadir a _btn_config:
#     "Proveedores":    ("🏭 PROVEEDORES",       "c1"),      # ← NUEVO
#     "ProductosCompra":("🛒 PRODUCTOS COMPRA",   "c2"),     # ← NUEVO
#     "Locales":        ("🏪 LOCALES",            "c3"),     # ← NUEVO
#     "Stock":          ("📦 STOCK",              "c2"),     # ← NUEVO
# ════════════════════════════════════════════════════════════

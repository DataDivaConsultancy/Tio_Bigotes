-- =========================================================
-- MIGRACIÓN: Limpieza total y recarga de productos/categorías
-- Ejecutar en Supabase SQL Editor BLOQUE POR BLOQUE
-- =========================================================

-- ══════════════════════════════════════════════════════════
-- BLOQUE 1: Crear categorías nuevas (no toca las existentes)
-- ══════════════════════════════════════════════════════════

INSERT INTO tb_v2.categorias_producto (nombre, codigo)
SELECT v.nombre, v.codigo
FROM (VALUES
  ('Empanada Clasica', 'empanada_clasica'),
  ('Empanada Premium', 'empanada_premium'),
  ('Menu', 'menu'),
  ('Glovo Menu', 'glovo_menu'),
  ('Alfajor', 'alfajor'),
  ('Bebida', 'bebida'),
  ('Agua', 'agua'),
  ('Agua Gas', 'agua_gas'),
  ('Aquarius', 'aquarius'),
  ('Bolsa', 'bolsa'),
  ('Cafe', 'cafe'),
  ('Cerveza', 'cerveza'),
  ('Chipa', 'chipa'),
  ('Medialuna', 'medialuna'),
  ('Otros', 'otros'),
  ('Descuentos', 'descuentos'),
  ('Dto Empleados', 'dto_empleados'),
  ('Bocata', 'bocata'),
  ('Fuzetea', 'fuzetea'),
  ('Postre', 'postre'),
  ('Muffin', 'muffin'),
  ('Pizza', 'pizza'),
  ('Salsa', 'salsa'),
  ('Te', 'te'),
  ('Zumo', 'zumo'),
  ('Vino', 'vino')
) AS v(nombre, codigo)
WHERE NOT EXISTS (
  SELECT 1 FROM tb_v2.categorias_producto c WHERE LOWER(c.nombre) = LOWER(v.nombre)
);

-- ══════════════════════════════════════════════════════════
-- BLOQUE 2: Desactivar TODOS los productos existentes
-- (no borramos para no perder referencias en ventas históricas)
-- ══════════════════════════════════════════════════════════

UPDATE tb_v2.productos SET activo = FALSE;

-- ══════════════════════════════════════════════════════════
-- BLOQUE 3: Función para insertar/actualizar producto
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION _tmp_upsert_prod(
  p_nombre TEXT,
  p_categoria TEXT
) RETURNS VOID AS $$
DECLARE
  v_cat_id INT;
  v_prod_id INT;
  v_is_emp BOOLEAN;
  v_is_producible BOOLEAN;
BEGIN
  SELECT id INTO v_cat_id FROM tb_v2.categorias_producto
  WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(p_categoria)) LIMIT 1;

  IF v_cat_id IS NULL THEN
    RAISE EXCEPTION 'Categoría no encontrada: %', p_categoria;
  END IF;

  v_is_emp := LOWER(p_categoria) IN ('empanada clasica', 'empanada premium');
  v_is_producible := LOWER(p_categoria) IN ('empanada clasica', 'empanada premium', 'medialuna', 'chipa', 'pizza', 'muffin', 'bocata');

  -- Find existing product (exact match first, then normalized)
  SELECT id INTO v_prod_id FROM tb_v2.productos
  WHERE TRIM(nombre) = TRIM(p_nombre) LIMIT 1;

  IF v_prod_id IS NULL THEN
    SELECT id INTO v_prod_id FROM tb_v2.productos
    WHERE LOWER(TRIM(nombre)) = LOWER(TRIM(p_nombre)) LIMIT 1;
  END IF;

  IF v_prod_id IS NOT NULL THEN
    UPDATE tb_v2.productos SET
      categoria_id = v_cat_id,
      subtipo = (SELECT codigo FROM tb_v2.categorias_producto WHERE id = v_cat_id),
      activo = TRUE,
      es_vendible = TRUE,
      es_producible = v_is_producible,
      afecta_forecast = v_is_emp,
      visible_en_control_diario = v_is_producible,
      visible_en_forecast = v_is_emp,
      uds_equivalentes_empanadas = CASE WHEN v_is_emp THEN 1 ELSE 0 END
    WHERE id = v_prod_id;
  ELSE
    INSERT INTO tb_v2.productos (
      nombre, nombre_normalizado, categoria_id, subtipo,
      activo, es_vendible, es_producible, afecta_forecast,
      visible_en_control_diario, visible_en_forecast,
      orden_visual, uds_equivalentes_empanadas
    ) VALUES (
      TRIM(p_nombre),
      LOWER(TRIM(p_nombre)),
      v_cat_id,
      (SELECT codigo FROM tb_v2.categorias_producto WHERE id = v_cat_id),
      TRUE, TRUE, v_is_producible, v_is_emp,
      v_is_producible, v_is_emp,
      100,
      CASE WHEN v_is_emp THEN 1 ELSE 0 END
    );
  END IF;
END;
$$ LANGUAGE plpgsql;

-- ══════════════════════════════════════════════════════════
-- BLOQUE 4: Cargar todos los productos
-- ══════════════════════════════════════════════════════════

-- Empanada Clásica
SELECT _tmp_upsert_prod('1.CARNE SUAVE', 'Empanada Clasica');
SELECT _tmp_upsert_prod('11. HUMITA', 'Empanada Clasica');
SELECT _tmp_upsert_prod('13.CAPRESE', 'Empanada Clasica');
SELECT _tmp_upsert_prod('14.ATUN', 'Empanada Clasica');
SELECT _tmp_upsert_prod('16. ESPINACAS Y QUESO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('2. CARNE PICANTE', 'Empanada Clasica');
SELECT _tmp_upsert_prod('3.CARNE CUCHILLO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('4.POLLO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('5.POLLO PICANTE', 'Empanada Clasica');
SELECT _tmp_upsert_prod('6.JAMON Y ROQUEFORT', 'Empanada Clasica');
SELECT _tmp_upsert_prod('7.JAMON Y QUESO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('8. CEBOLLA Y QUESO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('9.BACÓN Y QUESO', 'Empanada Clasica');
SELECT _tmp_upsert_prod('CHORIZO PICANTE', 'Empanada Clasica');
SELECT _tmp_upsert_prod('CORDOBESA', 'Empanada Clasica');

-- Empanada Premium
SELECT _tmp_upsert_prod('20. VERDURA VEGANA', 'Empanada Premium');
SELECT _tmp_upsert_prod('24. NUTELLA, BROWNIE Y PISTACHO (UNIDAD)', 'Empanada Premium');
SELECT _tmp_upsert_prod('30. NDUJA Y PROVOLONE', 'Empanada Premium');
SELECT _tmp_upsert_prod('CRIOLLA', 'Empanada Premium');
SELECT _tmp_upsert_prod('JAMON IBER, RUCULA, TOMATE Y PARMESANO', 'Empanada Premium');
SELECT _tmp_upsert_prod('MANZANA AL RON', 'Empanada Premium');
SELECT _tmp_upsert_prod('PROVOLONE Y OLIVAS', 'Empanada Premium');
SELECT _tmp_upsert_prod('QUESO DE CABRA Y CEBOLLA CARAMELIZADA', 'Empanada Premium');
SELECT _tmp_upsert_prod('QUESO Y DULCE DE MEMBRILLO (unidad)', 'Empanada Premium');
SELECT _tmp_upsert_prod('SMASH BURGER', 'Empanada Premium');
SELECT _tmp_upsert_prod('TUCUMANA', 'Empanada Premium');
SELECT _tmp_upsert_prod('VACIO, PROVOLONE Y CHIMICHURRI', 'Empanada Premium');

-- Menu
SELECT _tmp_upsert_prod('2 EMPANADAS + 1 BEBIDA CC', 'Menu');
SELECT _tmp_upsert_prod('3 EMPANADAS + 1 BEBIDA CC', 'Menu');
SELECT _tmp_upsert_prod('MENU 10 EMPANADAS', 'Menu');
SELECT _tmp_upsert_prod('MENÚ 10 EMPANADAS (PROMO NAVIDAD)', 'Menu');
SELECT _tmp_upsert_prod('MENÚ 2 EMPANADAS + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_prod('MENÚ 2 EMPANADAS+1 BEBIDA + LAY''S', 'Menu');
SELECT _tmp_upsert_prod('MENU 20 EMP + 6 BEBIDAS', 'Menu');
SELECT _tmp_upsert_prod('MENÚ 20 EMPANADAS + 6 BEBIDAS', 'Menu');
SELECT _tmp_upsert_prod('MENU 6 EMP + 2 BEBIDAS', 'Menu');
SELECT _tmp_upsert_prod('MENÚ 6 EMPANADAS + 2 BEBIDAS', 'Menu');
SELECT _tmp_upsert_prod('Menu Pizza Cuadrada + bebida', 'Menu');
SELECT _tmp_upsert_prod('MENU PORCIÓN PIZZA + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_prod('PACK 6 EMPANADAS', 'Menu');
SELECT _tmp_upsert_prod('PACK 10 EMPANADAS', 'Menu');
SELECT _tmp_upsert_prod('PACK 20 EMPANADAS', 'Menu');
SELECT _tmp_upsert_prod('PROMO  flauta jamon  y queso + familia', 'Menu');
SELECT _tmp_upsert_prod('PROMO 2 EMPANADAS + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_prod('PROMO 3 ALFAJORES MINI', 'Menu');
SELECT _tmp_upsert_prod('promo croissant jyq + cafe', 'Menu');
SELECT _tmp_upsert_prod('promo muffin + cafe', 'Menu');

-- Glovo Menu
SELECT _tmp_upsert_prod('2 EMPANADAS + 1 BEBIDA CC GLOVO', 'Glovo Menu');
SELECT _tmp_upsert_prod('3 EMPANADAS + 1 BEBIDA CC GLOVO', 'Glovo Menu');
SELECT _tmp_upsert_prod('Glovo Menu 10 empanadas', 'Glovo Menu');
SELECT _tmp_upsert_prod('Glovo Menu 2 emp + 1 bebida', 'Glovo Menu');
SELECT _tmp_upsert_prod('Glovo Menu 20 emp + 6 bebidas', 'Glovo Menu');
SELECT _tmp_upsert_prod('Glovo Menu 6 emp + 2 bebidas', 'Glovo Menu');
SELECT _tmp_upsert_prod('Glovo Menu Porción Pizza + 1 bebida', 'Glovo Menu');
SELECT _tmp_upsert_prod('GLOVO PACK 10 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_prod('GLOVO PACK 20 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_prod('GLOVO PACK 6 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_prod('MENU GLOVO 2 EMP + BEBIDA.', 'Glovo Menu');
SELECT _tmp_upsert_prod('MENU GLOVO 3 EMP + BEBIDA.', 'Glovo Menu');
SELECT _tmp_upsert_prod('MENU GLOVO 6 EMP + 2 BEBIDAS.', 'Glovo Menu');

-- Alfajor
SELECT _tmp_upsert_prod('3 ALAFAJOR MINI PISTACHO', 'Alfajor');
SELECT _tmp_upsert_prod('ALFAJOR', 'Alfajor');
SELECT _tmp_upsert_prod('ALFAJOR MINI', 'Alfajor');
SELECT _tmp_upsert_prod('ALFAJOR MINI PISTACHO', 'Alfajor');
SELECT _tmp_upsert_prod('ALFAJOR SAN VALENTIN 3 UND', 'Alfajor');

-- Bebida
SELECT _tmp_upsert_prod('COCA-COLA 500ML', 'Bebida');
SELECT _tmp_upsert_prod('COCA-COLA ZERO 500ML', 'Bebida');
SELECT _tmp_upsert_prod('FANTA LIMON 500ML', 'Bebida');
SELECT _tmp_upsert_prod('FANTA NARANJA 500ML', 'Bebida');
SELECT _tmp_upsert_prod('MONSTER', 'Bebida');
SELECT _tmp_upsert_prod('PEPSI', 'Bebida');
SELECT _tmp_upsert_prod('PEPSI LIGHT', 'Bebida');
SELECT _tmp_upsert_prod('PEPSI MAX', 'Bebida');
SELECT _tmp_upsert_prod('PEPSI MAX LIMA', 'Bebida');
SELECT _tmp_upsert_prod('Pepsi Zero', 'Bebida');
SELECT _tmp_upsert_prod('SPRITE', 'Bebida');
SELECT _tmp_upsert_prod('7UP', 'Bebida');
SELECT _tmp_upsert_prod('7Up FREE', 'Bebida');

-- Agua
SELECT _tmp_upsert_prod('AGUA', 'Agua');
SELECT _tmp_upsert_prod('AGUA 500 ML.', 'Agua');
SELECT _tmp_upsert_prod('AQUABONA', 'Agua');
SELECT _tmp_upsert_prod('AQUAFINA 500 ml.', 'Agua');

-- Agua Gas
SELECT _tmp_upsert_prod('AGUA CON GAS', 'Agua Gas');
SELECT _tmp_upsert_prod('VICHY CATALÁN', 'Agua Gas');

-- Aquarius
SELECT _tmp_upsert_prod('AQUARADE', 'Aquarius');
SELECT _tmp_upsert_prod('AQUARADE LIMON', 'Aquarius');
SELECT _tmp_upsert_prod('AQUARADE NARANJA', 'Aquarius');
SELECT _tmp_upsert_prod('AQUARIUS LIMON', 'Aquarius');
SELECT _tmp_upsert_prod('AQUARIUS NARANJA', 'Aquarius');
SELECT _tmp_upsert_prod('KAS LIMON', 'Aquarius');
SELECT _tmp_upsert_prod('KAS NARANJA', 'Aquarius');

-- Bolsa
SELECT _tmp_upsert_prod('Bolsa Tio Bigotes', 'Bolsa');

-- Café
SELECT _tmp_upsert_prod('CAFE CON LECHE', 'Cafe');
SELECT _tmp_upsert_prod('CAFE CORTADO', 'Cafe');
SELECT _tmp_upsert_prod('CAFE DOBLE', 'Cafe');
SELECT _tmp_upsert_prod('CAFE GRANDE', 'Cafe');
SELECT _tmp_upsert_prod('CAFE SOLO - ESPRESSO', 'Cafe');

-- Cerveza
SELECT _tmp_upsert_prod('CERVEZA - VARIOS', 'Cerveza');
SELECT _tmp_upsert_prod('CERVEZA DE LATA', 'Cerveza');
SELECT _tmp_upsert_prod('Estrella Damm', 'Cerveza');
SELECT _tmp_upsert_prod('Estrella Galicia', 'Cerveza');
SELECT _tmp_upsert_prod('FREE DAM LEMON', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ -  lata', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ - O.O lata', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ - RADLER - lata', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ - TORRADA 0.0 - lata', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ 7 - lata', 'Cerveza');
SELECT _tmp_upsert_prod('MORITZ EPIDOR - lata', 'Cerveza');

-- Chipá
SELECT _tmp_upsert_prod('CHIPÁ', 'Chipa');

-- Medialuna
SELECT _tmp_upsert_prod('CROISSANT', 'Medialuna');
SELECT _tmp_upsert_prod('croissant jyq', 'Medialuna');

-- Fuze Tea
SELECT _tmp_upsert_prod('FUZE TEA LIMON', 'Fuzetea');
SELECT _tmp_upsert_prod('FUZE TEA MARACUYA', 'Fuzetea');
SELECT _tmp_upsert_prod('LIPTON LIMON', 'Fuzetea');
SELECT _tmp_upsert_prod('LIPTON MELOCOTON', 'Fuzetea');

-- Pizza
SELECT _tmp_upsert_prod('PIZZA - PORCIÓN', 'Pizza');
SELECT _tmp_upsert_prod('PIZZA porción cuadrada', 'Pizza');

-- Muffin
SELECT _tmp_upsert_prod('Muffin', 'Muffin');

-- Bocata
SELECT _tmp_upsert_prod('Flauta de Jamon', 'Bocata');

-- Postre
SELECT _tmp_upsert_prod('HELADO.', 'Postre');

-- Salsa
SELECT _tmp_upsert_prod('SALSA BARBACOA', 'Salsa');
SELECT _tmp_upsert_prod('SALSA BRAVA', 'Salsa');
SELECT _tmp_upsert_prod('SALSA CHIMICHURRI', 'Salsa');
SELECT _tmp_upsert_prod('SALSA TÁRTARA', 'Salsa');

-- Té
SELECT _tmp_upsert_prod('TE - INFUSIÓN', 'Te');
SELECT _tmp_upsert_prod('TEA NEGRO', 'Te');
SELECT _tmp_upsert_prod('TEA VERDE', 'Te');

-- Zumo
SELECT _tmp_upsert_prod('Tropicana naranja', 'Zumo');
SELECT _tmp_upsert_prod('ZUMO MELOCOTÓN 200ML', 'Zumo');
SELECT _tmp_upsert_prod('ZUMO PIÑA 200ML', 'Zumo');

-- Vino
SELECT _tmp_upsert_prod('VINO TINTO', 'Vino');

-- Descuentos / Otros
SELECT _tmp_upsert_prod('Descuento comercial', 'Descuentos');
SELECT _tmp_upsert_prod('Empleados', 'Dto Empleados');
SELECT _tmp_upsert_prod('Desc Máquina', 'Otros');
SELECT _tmp_upsert_prod('Invitación', 'Otros');
SELECT _tmp_upsert_prod('Largo', 'Otros');
SELECT _tmp_upsert_prod('LAYS', 'Otros');
SELECT _tmp_upsert_prod('MILKA BOMBÓN', 'Otros');
SELECT _tmp_upsert_prod('MILKA CONO BOLA', 'Otros');
SELECT _tmp_upsert_prod('Normal', 'Otros');
SELECT _tmp_upsert_prod('OREO BOMBÓN', 'Otros');
SELECT _tmp_upsert_prod('plus premium', 'Otros');
SELECT _tmp_upsert_prod('SERVICIO DE ENTREGA', 'Otros');
SELECT _tmp_upsert_prod('SUPLEMENTO CERVEZA', 'Otros');
SELECT _tmp_upsert_prod('SUPLEMENTO VINO', 'Otros');
SELECT _tmp_upsert_prod('TOBLERONE BOMBON', 'Otros');

-- ══════════════════════════════════════════════════════════
-- BLOQUE 5: Eliminar duplicados (mantener el de menor ID)
-- ══════════════════════════════════════════════════════════

-- Primero reasignar ventas de duplicados al original
UPDATE tb_v2.ventas_raw vr
SET producto_id = keeper.id
FROM tb_v2.productos dup
JOIN (
  SELECT MIN(id) AS id, LOWER(TRIM(nombre)) AS nombre_norm
  FROM tb_v2.productos
  GROUP BY LOWER(TRIM(nombre))
) keeper ON LOWER(TRIM(dup.nombre)) = keeper.nombre_norm AND dup.id != keeper.id
WHERE vr.producto_id = dup.id;

-- Reasignar en staging también
UPDATE tb_v2.ventas_staging vr
SET producto_id = keeper.id
FROM tb_v2.productos dup
JOIN (
  SELECT MIN(id) AS id, LOWER(TRIM(nombre)) AS nombre_norm
  FROM tb_v2.productos
  GROUP BY LOWER(TRIM(nombre))
) keeper ON LOWER(TRIM(dup.nombre)) = keeper.nombre_norm AND dup.id != keeper.id
WHERE vr.producto_id = dup.id;

-- Ahora borrar los duplicados
DELETE FROM tb_v2.productos
WHERE id NOT IN (
  SELECT MIN(id)
  FROM tb_v2.productos
  GROUP BY LOWER(TRIM(nombre))
);

-- ══════════════════════════════════════════════════════════
-- BLOQUE 6: Limpiar y verificar
-- ══════════════════════════════════════════════════════════

DROP FUNCTION IF EXISTS _tmp_upsert_prod(TEXT, TEXT);

-- Verificación: productos activos por categoría
SELECT c.nombre AS categoria, COUNT(*) AS productos,
       STRING_AGG(p.nombre, ', ' ORDER BY p.nombre) AS lista
FROM tb_v2.productos p
JOIN tb_v2.categorias_producto c ON p.categoria_id = c.id
WHERE p.activo = TRUE
GROUP BY c.nombre
ORDER BY c.nombre;

-- =========================================================
-- MIGRACIÓN: Actualización completa de productos y categorías
-- Ejecutar en Supabase SQL Editor EN ORDEN (bloque por bloque)
-- =========================================================

-- ══════════════════════════════════════════════════════════
-- BLOQUE 1: Crear categorías nuevas (si no existen)
-- ══════════════════════════════════════════════════════════

INSERT INTO tb_v2.categorias_producto (nombre, codigo)
SELECT v.nombre, v.codigo
FROM (VALUES
  ('Empanada', 'empanada'),
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
-- BLOQUE 2: Insertar productos nuevos y actualizar categorías
-- Ejecutar DESPUÉS del bloque 1
-- ══════════════════════════════════════════════════════════

-- Función temporal para insertar o actualizar producto
CREATE OR REPLACE FUNCTION _tmp_upsert_producto(
  p_nombre TEXT,
  p_categoria TEXT
) RETURNS VOID AS $$
DECLARE
  v_cat_id INT;
  v_prod_id INT;
  v_nombre_norm TEXT;
BEGIN
  -- Get category id
  SELECT id INTO v_cat_id FROM tb_v2.categorias_producto WHERE LOWER(nombre) = LOWER(p_categoria) LIMIT 1;
  IF v_cat_id IS NULL THEN
    RAISE EXCEPTION 'Categoría no encontrada: %', p_categoria;
  END IF;

  -- Normalize name
  v_nombre_norm := LOWER(TRIM(p_nombre));

  -- Check if product exists (by normalized name match)
  SELECT id INTO v_prod_id FROM tb_v2.productos
  WHERE LOWER(TRIM(nombre)) = v_nombre_norm
  LIMIT 1;

  IF v_prod_id IS NOT NULL THEN
    -- Update category and ensure active
    UPDATE tb_v2.productos
    SET categoria_id = v_cat_id, activo = TRUE
    WHERE id = v_prod_id;
  ELSE
    -- Insert new product
    INSERT INTO tb_v2.productos (
      nombre, nombre_normalizado, categoria_id, subtipo,
      activo, es_vendible, es_producible, afecta_forecast,
      visible_en_control_diario, visible_en_forecast,
      orden_visual, uds_equivalentes_empanadas
    ) VALUES (
      TRIM(p_nombre),
      v_nombre_norm,
      v_cat_id,
      (SELECT codigo FROM tb_v2.categorias_producto WHERE id = v_cat_id),
      TRUE,
      TRUE,
      CASE WHEN LOWER(p_categoria) = 'empanada' THEN TRUE ELSE FALSE END,
      CASE WHEN LOWER(p_categoria) = 'empanada' THEN TRUE ELSE FALSE END,
      CASE WHEN LOWER(p_categoria) IN ('empanada', 'medialuna', 'chipa', 'pizza', 'muffin') THEN TRUE ELSE FALSE END,
      CASE WHEN LOWER(p_categoria) = 'empanada' THEN TRUE ELSE FALSE END,
      100,
      CASE WHEN LOWER(p_categoria) = 'empanada' THEN 1 ELSE 0 END
    );
  END IF;
END;
$$ LANGUAGE plpgsql;

-- ══════════════════════════════════════════════════════════
-- BLOQUE 3: Ejecutar upsert para todos los productos
-- Ejecutar DESPUÉS del bloque 2
-- ══════════════════════════════════════════════════════════

-- Empanadas
SELECT _tmp_upsert_producto('1.CARNE SUAVE', 'Empanada');
SELECT _tmp_upsert_producto('11. HUMITA', 'Empanada');
SELECT _tmp_upsert_producto('13.CAPRESE', 'Empanada');
SELECT _tmp_upsert_producto('14.ATUN', 'Empanada');
SELECT _tmp_upsert_producto('16. ESPINACAS Y QUESO', 'Empanada');
SELECT _tmp_upsert_producto('2. CARNE PICANTE', 'Empanada');
SELECT _tmp_upsert_producto('20. VERDURA VEGANA', 'Empanada');
SELECT _tmp_upsert_producto('24. NUTELLA, BROWNIE Y PISTACHO (UNIDAD)', 'Empanada');
SELECT _tmp_upsert_producto('3.CARNE CUCHILLO', 'Empanada');
SELECT _tmp_upsert_producto('30. NDUJA Y PROVOLONE', 'Empanada');
SELECT _tmp_upsert_producto('4.POLLO', 'Empanada');
SELECT _tmp_upsert_producto('5.POLLO PICANTE', 'Empanada');
SELECT _tmp_upsert_producto('6.JAMON Y ROQUEFORT', 'Empanada');
SELECT _tmp_upsert_producto('7.JAMON Y QUESO', 'Empanada');
SELECT _tmp_upsert_producto('8. CEBOLLA Y QUESO', 'Empanada');
SELECT _tmp_upsert_producto('9.BACÓN Y QUESO', 'Empanada');
SELECT _tmp_upsert_producto('CHORIZO PICANTE', 'Empanada');
SELECT _tmp_upsert_producto('CORDOBESA', 'Empanada');
SELECT _tmp_upsert_producto('CRIOLLA', 'Empanada');
SELECT _tmp_upsert_producto('JAMON IBER, RUCULA, TOMATE Y PARMESANO', 'Empanada');
SELECT _tmp_upsert_producto('MANZANA AL RON', 'Empanada');
SELECT _tmp_upsert_producto('PROVOLONE Y OLIVAS', 'Empanada');
SELECT _tmp_upsert_producto('QUESO DE CABRA Y CEBOLLA CARAMELIZADA', 'Empanada');
SELECT _tmp_upsert_producto('QUESO Y DULCE DE MEMBRILLO (unidad)', 'Empanada');
SELECT _tmp_upsert_producto('SMASH BURGER', 'Empanada');
SELECT _tmp_upsert_producto('TUCUMANA', 'Empanada');
SELECT _tmp_upsert_producto('VACIO, PROVOLONE Y CHIMICHURRI', 'Empanada');

-- Menús
SELECT _tmp_upsert_producto('2 EMPANADAS + 1 BEBIDA CC', 'Menu');
SELECT _tmp_upsert_producto('3 EMPANADAS + 1 BEBIDA CC', 'Menu');
SELECT _tmp_upsert_producto('MENU 10 EMPANADAS', 'Menu');
SELECT _tmp_upsert_producto('MENÚ 10 EMPANADAS (PROMO NAVIDAD)', 'Menu');
SELECT _tmp_upsert_producto('MENÚ 2 EMPANADAS + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_producto('MENÚ 2 EMPANADAS+1 BEBIDA + LAY''S', 'Menu');
SELECT _tmp_upsert_producto('MENU 20 EMP + 6 BEBIDAS', 'Menu');
SELECT _tmp_upsert_producto('MENÚ 20 EMPANADAS + 6 BEBIDAS', 'Menu');
SELECT _tmp_upsert_producto('MENU 6 EMP + 2 BEBIDAS', 'Menu');
SELECT _tmp_upsert_producto('MENÚ 6 EMPANADAS + 2 BEBIDAS', 'Menu');
SELECT _tmp_upsert_producto('Menu Pizza Cuadrada + bebida', 'Menu');
SELECT _tmp_upsert_producto('MENU PORCIÓN PIZZA + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_producto('PACK 6 EMPANADAS', 'Menu');
SELECT _tmp_upsert_producto('PACK 10 EMPANADAS', 'Menu');
SELECT _tmp_upsert_producto('PACK 20 EMPANADAS', 'Menu');
SELECT _tmp_upsert_producto('PROMO  flauta jamon  y queso + familia', 'Menu');
SELECT _tmp_upsert_producto('PROMO 2 EMPANADAS + 1 BEBIDA', 'Menu');
SELECT _tmp_upsert_producto('PROMO 3 ALFAJORES MINI', 'Menu');
SELECT _tmp_upsert_producto('promo croissant jyq + cafe', 'Menu');
SELECT _tmp_upsert_producto('promo muffin + cafe', 'Menu');

-- Glovo Menús
SELECT _tmp_upsert_producto('2 EMPANADAS + 1 BEBIDA CC GLOVO', 'Glovo Menu');
SELECT _tmp_upsert_producto('3 EMPANADAS + 1 BEBIDA CC GLOVO', 'Glovo Menu');
SELECT _tmp_upsert_producto('Glovo Menu 10 empanadas', 'Glovo Menu');
SELECT _tmp_upsert_producto('Glovo Menu 2 emp + 1 bebida', 'Glovo Menu');
SELECT _tmp_upsert_producto('Glovo Menu 20 emp + 6 bebidas', 'Glovo Menu');
SELECT _tmp_upsert_producto('Glovo Menu 6 emp + 2 bebidas', 'Glovo Menu');
SELECT _tmp_upsert_producto('Glovo Menu Porción Pizza + 1 bebida', 'Glovo Menu');
SELECT _tmp_upsert_producto('GLOVO PACK 10 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_producto('GLOVO PACK 20 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_producto('GLOVO PACK 6 EMPANADAS.', 'Glovo Menu');
SELECT _tmp_upsert_producto('MENU GLOVO 2 EMP + BEBIDA.', 'Glovo Menu');
SELECT _tmp_upsert_producto('MENU GLOVO 3 EMP + BEBIDA.', 'Glovo Menu');
SELECT _tmp_upsert_producto('MENU GLOVO 6 EMP + 2 BEBIDAS.', 'Glovo Menu');

-- Alfajores
SELECT _tmp_upsert_producto('3 ALAFAJOR MINI PISTACHO', 'Alfajor');
SELECT _tmp_upsert_producto('ALFAJOR', 'Alfajor');
SELECT _tmp_upsert_producto('ALFAJOR MINI', 'Alfajor');
SELECT _tmp_upsert_producto('ALFAJOR MINI PISTACHO', 'Alfajor');
SELECT _tmp_upsert_producto('ALFAJOR SAN VALENTIN 3 UND', 'Alfajor');

-- Bebidas
SELECT _tmp_upsert_producto('COCA-COLA 500ML', 'Bebida');
SELECT _tmp_upsert_producto('COCA-COLA ZERO 500ML', 'Bebida');
SELECT _tmp_upsert_producto('FANTA LIMON 500ML', 'Bebida');
SELECT _tmp_upsert_producto('FANTA NARANJA 500ML', 'Bebida');
SELECT _tmp_upsert_producto('MONSTER', 'Bebida');
SELECT _tmp_upsert_producto('PEPSI', 'Bebida');
SELECT _tmp_upsert_producto('PEPSI LIGHT', 'Bebida');
SELECT _tmp_upsert_producto('PEPSI MAX', 'Bebida');
SELECT _tmp_upsert_producto('PEPSI MAX LIMA', 'Bebida');
SELECT _tmp_upsert_producto('Pepsi Zero', 'Bebida');
SELECT _tmp_upsert_producto('SPRITE', 'Bebida');
SELECT _tmp_upsert_producto('7UP', 'Bebida');
SELECT _tmp_upsert_producto('7Up FREE', 'Bebida');

-- Agua
SELECT _tmp_upsert_producto('AGUA', 'Agua');
SELECT _tmp_upsert_producto('AGUA 500 ML.', 'Agua');
SELECT _tmp_upsert_producto('AQUABONA', 'Agua');
SELECT _tmp_upsert_producto('AQUAFINA 500 ml.', 'Agua');

-- Agua Gas
SELECT _tmp_upsert_producto('AGUA CON GAS', 'Agua Gas');
SELECT _tmp_upsert_producto('VICHY CATALÁN', 'Agua Gas');

-- Aquarius
SELECT _tmp_upsert_producto('AQUARADE', 'Aquarius');
SELECT _tmp_upsert_producto('AQUARADE LIMON', 'Aquarius');
SELECT _tmp_upsert_producto('AQUARADE NARANJA', 'Aquarius');
SELECT _tmp_upsert_producto('AQUARIUS LIMON', 'Aquarius');
SELECT _tmp_upsert_producto('AQUARIUS NARANJA', 'Aquarius');
SELECT _tmp_upsert_producto('KAS LIMON', 'Aquarius');
SELECT _tmp_upsert_producto('KAS NARANJA', 'Aquarius');

-- Bolsa
SELECT _tmp_upsert_producto('Bolsa Tio Bigotes', 'Bolsa');

-- Café
SELECT _tmp_upsert_producto('CAFE CON LECHE', 'Cafe');
SELECT _tmp_upsert_producto('CAFE CORTADO', 'Cafe');
SELECT _tmp_upsert_producto('CAFE DOBLE', 'Cafe');
SELECT _tmp_upsert_producto('CAFE GRANDE', 'Cafe');
SELECT _tmp_upsert_producto('CAFE SOLO - ESPRESSO', 'Cafe');

-- Cerveza
SELECT _tmp_upsert_producto('CERVEZA - VARIOS', 'Cerveza');
SELECT _tmp_upsert_producto('CERVEZA DE LATA', 'Cerveza');
SELECT _tmp_upsert_producto('Estrella Damm', 'Cerveza');
SELECT _tmp_upsert_producto('Estrella Galicia', 'Cerveza');
SELECT _tmp_upsert_producto('FREE DAM LEMON', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ -  lata', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ - O.O lata', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ - RADLER - lata', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ - TORRADA 0.0 - lata', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ 7 - lata', 'Cerveza');
SELECT _tmp_upsert_producto('MORITZ EPIDOR - lata', 'Cerveza');

-- Chipá
SELECT _tmp_upsert_producto('CHIPÁ', 'Chipa');

-- Medialuna
SELECT _tmp_upsert_producto('CROISSANT', 'Medialuna');
SELECT _tmp_upsert_producto('croissant jyq', 'Medialuna');

-- Fuze Tea
SELECT _tmp_upsert_producto('FUZE TEA LIMON', 'Fuzetea');
SELECT _tmp_upsert_producto('FUZE TEA MARACUYA', 'Fuzetea');
SELECT _tmp_upsert_producto('LIPTON LIMON', 'Fuzetea');
SELECT _tmp_upsert_producto('LIPTON MELOCOTON', 'Fuzetea');

-- Pizza
SELECT _tmp_upsert_producto('PIZZA - PORCIÓN', 'Pizza');
SELECT _tmp_upsert_producto('PIZZA porción cuadrada', 'Pizza');

-- Muffin
SELECT _tmp_upsert_producto('Muffin', 'Muffin');

-- Bocata
SELECT _tmp_upsert_producto('Flauta de Jamon', 'Bocata');

-- Postre
SELECT _tmp_upsert_producto('HELADO.', 'Postre');

-- Salsa
SELECT _tmp_upsert_producto('SALSA BARBACOA', 'Salsa');
SELECT _tmp_upsert_producto('SALSA BRAVA', 'Salsa');
SELECT _tmp_upsert_producto('SALSA CHIMICHURRI', 'Salsa');
SELECT _tmp_upsert_producto('SALSA TÁRTARA', 'Salsa');

-- Té
SELECT _tmp_upsert_producto('TE - INFUSIÓN', 'Te');
SELECT _tmp_upsert_producto('TEA NEGRO', 'Te');
SELECT _tmp_upsert_producto('TEA VERDE', 'Te');

-- Zumo
SELECT _tmp_upsert_producto('Tropicana naranja', 'Zumo');
SELECT _tmp_upsert_producto('ZUMO MELOCOTÓN 200ML', 'Zumo');
SELECT _tmp_upsert_producto('ZUMO PIÑA 200ML', 'Zumo');

-- Vino
SELECT _tmp_upsert_producto('VINO TINTO', 'Vino');

-- Descuentos
SELECT _tmp_upsert_producto('Descuento comercial', 'Descuentos');

-- Dto Empleados
SELECT _tmp_upsert_producto('Empleados', 'Dto Empleados');

-- Otros
SELECT _tmp_upsert_producto('Desc Máquina', 'Otros');
SELECT _tmp_upsert_producto('Invitación', 'Otros');
SELECT _tmp_upsert_producto('Largo', 'Otros');
SELECT _tmp_upsert_producto('LAYS', 'Otros');
SELECT _tmp_upsert_producto('MILKA BOMBÓN', 'Otros');
SELECT _tmp_upsert_producto('MILKA CONO BOLA', 'Otros');
SELECT _tmp_upsert_producto('Normal', 'Otros');
SELECT _tmp_upsert_producto('OREO BOMBÓN', 'Otros');
SELECT _tmp_upsert_producto('plus premium', 'Otros');
SELECT _tmp_upsert_producto('SERVICIO DE ENTREGA', 'Otros');
SELECT _tmp_upsert_producto('SUPLEMENTO CERVEZA', 'Otros');
SELECT _tmp_upsert_producto('SUPLEMENTO VINO', 'Otros');
SELECT _tmp_upsert_producto('TOBLERONE BOMBON', 'Otros');

-- ══════════════════════════════════════════════════════════
-- BLOQUE 4: Limpiar función temporal
-- Ejecutar DESPUÉS del bloque 3
-- ══════════════════════════════════════════════════════════

DROP FUNCTION IF EXISTS _tmp_upsert_producto(TEXT, TEXT);

-- ══════════════════════════════════════════════════════════
-- BLOQUE 5: Verificación
-- Ejecutar para confirmar que todo está bien
-- ══════════════════════════════════════════════════════════

SELECT c.nombre AS categoria, COUNT(*) AS productos,
       STRING_AGG(p.nombre, ', ' ORDER BY p.nombre) AS lista
FROM tb_v2.productos p
JOIN tb_v2.categorias_producto c ON p.categoria_id = c.id
WHERE p.activo = TRUE
GROUP BY c.nombre
ORDER BY c.nombre;

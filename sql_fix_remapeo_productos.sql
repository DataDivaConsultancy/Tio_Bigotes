-- =========================================================
-- FIX: Remapear producto_id en ventas_staging_v2
--
-- Problema: Tras la limpieza del catálogo de productos,
-- 198,471 de 302,412 filas (66%) tienen producto_id NULL
-- o apuntando a productos inactivos/eliminados.
--
-- Estrategia:
--   1. Reasignar por alias existentes en producto_aliases
--   2. Reasignar por coincidencia exacta nombre producto
--   3. Reasignar por coincidencia articulo_normalizado
--   4. Actualizar estado_mapeo
--
-- Ejecutar en Supabase SQL Editor
-- =========================================================

-- PASO 0: Diagnóstico antes del fix
-- (Ejecutar primero para verificar el estado actual)
SELECT
  COUNT(*) AS total,
  COUNT(CASE WHEN vs.producto_id IS NULL THEN 1 END) AS producto_id_null,
  COUNT(CASE WHEN vs.producto_id IS NOT NULL AND p.id IS NULL THEN 1 END) AS producto_id_inexistente,
  COUNT(CASE WHEN p.id IS NOT NULL AND p.activo = FALSE THEN 1 END) AS producto_inactivo,
  COUNT(CASE WHEN p.id IS NOT NULL AND p.activo = TRUE THEN 1 END) AS producto_ok
FROM tb_v2.ventas_staging vs
LEFT JOIN tb_v2.productos p ON vs.producto_id = p.id;

-- =========================================================
-- PASO 1: Crear tabla temporal de mapeo
-- Construye un diccionario alias_normalizado → producto_id
-- usando múltiples fuentes
-- =========================================================
DROP TABLE IF EXISTS _tmp_mapeo_fix;

CREATE TEMP TABLE _tmp_mapeo_fix AS

-- 1a: Desde producto_aliases (mapeo manual ya resuelto)
SELECT DISTINCT ON (alias_normalizado)
  pa.alias_normalizado,
  pa.producto_id
FROM tb_v2.producto_aliases pa
JOIN tb_v2.productos p ON pa.producto_id = p.id AND p.activo = TRUE
ORDER BY alias_normalizado, pa.id DESC

UNION ALL

-- 1b: Nombre normalizado del producto = alias
SELECT DISTINCT ON (nombre_norm)
  nombre_norm AS alias_normalizado,
  id AS producto_id
FROM (
  SELECT id, UPPER(TRIM(nombre)) AS nombre_norm
  FROM tb_v2.productos
  WHERE activo = TRUE
) sub
ORDER BY nombre_norm, producto_id;

-- Eliminar duplicados, priorizar alias manual (producto_aliases)
DROP TABLE IF EXISTS _tmp_mapeo_unico;
CREATE TEMP TABLE _tmp_mapeo_unico AS
SELECT DISTINCT ON (alias_normalizado)
  alias_normalizado,
  producto_id
FROM _tmp_mapeo_fix
ORDER BY alias_normalizado, producto_id;

-- Crear índice para performance
CREATE INDEX ON _tmp_mapeo_unico (alias_normalizado);

-- =========================================================
-- PASO 2: Reasignar producto_id por articulo_normalizado
-- =========================================================
UPDATE tb_v2.ventas_staging vs
SET
  producto_id = m.producto_id,
  estado_mapeo = 'ok'
FROM _tmp_mapeo_unico m
WHERE UPPER(TRIM(vs.articulo_normalizado)) = m.alias_normalizado
  AND (
    vs.producto_id IS NULL
    OR NOT EXISTS (
      SELECT 1 FROM tb_v2.productos p
      WHERE p.id = vs.producto_id AND p.activo = TRUE
    )
  );

-- =========================================================
-- PASO 3: Intentar también con subarticulo_normalizado
-- (para filas que aún no tienen match)
-- =========================================================
UPDATE tb_v2.ventas_staging vs
SET
  producto_id = m.producto_id,
  estado_mapeo = 'ok'
FROM _tmp_mapeo_unico m
WHERE UPPER(TRIM(vs.subarticulo_normalizado)) = m.alias_normalizado
  AND vs.subarticulo_normalizado IS NOT NULL
  AND vs.subarticulo_normalizado != ''
  AND (
    vs.producto_id IS NULL
    OR NOT EXISTS (
      SELECT 1 FROM tb_v2.productos p
      WHERE p.id = vs.producto_id AND p.activo = TRUE
    )
  );

-- =========================================================
-- PASO 4: Marcar filas sin match como 'pendiente'
-- =========================================================
UPDATE tb_v2.ventas_staging vs
SET estado_mapeo = 'pendiente'
WHERE (
  vs.producto_id IS NULL
  OR NOT EXISTS (
    SELECT 1 FROM tb_v2.productos p
    WHERE p.id = vs.producto_id AND p.activo = TRUE
  )
)
AND (vs.estado_mapeo IS NULL OR vs.estado_mapeo != 'pendiente');

-- =========================================================
-- PASO 5: Insertar aliases no reconocidos en articulos_pendientes
-- para resolución manual desde la UI
-- =========================================================
INSERT INTO tb_v2.articulos_pendientes (
  alias_normalizado,
  articulo_raw_ejemplo,
  veces_detectado,
  primera_fecha,
  ultima_fecha,
  estado
)
SELECT
  UPPER(TRIM(vs.articulo_normalizado)) AS alias_normalizado,
  MIN(vs.articulo_raw) AS articulo_raw_ejemplo,
  COUNT(*) AS veces_detectado,
  MIN(vs.fecha) AS primera_fecha,
  MAX(vs.fecha) AS ultima_fecha,
  'pendiente' AS estado
FROM tb_v2.ventas_staging vs
WHERE (
  vs.producto_id IS NULL
  OR NOT EXISTS (
    SELECT 1 FROM tb_v2.productos p
    WHERE p.id = vs.producto_id AND p.activo = TRUE
  )
)
AND vs.articulo_normalizado IS NOT NULL
AND TRIM(vs.articulo_normalizado) != ''
GROUP BY UPPER(TRIM(vs.articulo_normalizado))
ON CONFLICT (alias_normalizado) DO UPDATE SET
  veces_detectado = EXCLUDED.veces_detectado,
  ultima_fecha = EXCLUDED.ultima_fecha;

-- =========================================================
-- PASO 6: Diagnóstico después del fix
-- =========================================================
SELECT
  COUNT(*) AS total,
  COUNT(CASE WHEN vs.producto_id IS NULL THEN 1 END) AS producto_id_null,
  COUNT(CASE WHEN vs.producto_id IS NOT NULL AND p.id IS NULL THEN 1 END) AS producto_id_inexistente,
  COUNT(CASE WHEN p.id IS NOT NULL AND p.activo = FALSE THEN 1 END) AS producto_inactivo,
  COUNT(CASE WHEN p.id IS NOT NULL AND p.activo = TRUE THEN 1 END) AS producto_ok
FROM tb_v2.ventas_staging vs
LEFT JOIN tb_v2.productos p ON vs.producto_id = p.id;

-- Limpieza
DROP TABLE IF EXISTS _tmp_mapeo_fix;
DROP TABLE IF EXISTS _tmp_mapeo_unico;

-- =========================================================
-- RESUMEN: Artículos que quedaron sin mapear
-- =========================================================
SELECT
  UPPER(TRIM(vs.articulo_normalizado)) AS articulo,
  COUNT(*) AS filas,
  MIN(vs.fecha) AS desde,
  MAX(vs.fecha) AS hasta
FROM tb_v2.ventas_staging vs
WHERE vs.producto_id IS NULL
   OR NOT EXISTS (
     SELECT 1 FROM tb_v2.productos p
     WHERE p.id = vs.producto_id AND p.activo = TRUE
   )
GROUP BY UPPER(TRIM(vs.articulo_normalizado))
ORDER BY filas DESC
LIMIT 30;

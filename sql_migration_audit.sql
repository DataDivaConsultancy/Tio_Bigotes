-- =========================================================
-- MIGRACIÓN: Sistema de auditoría para Tío Bigotes
-- Ejecutar en Supabase SQL Editor
-- =========================================================

-- 1. Crear tabla de audit log
CREATE TABLE IF NOT EXISTS tb_v2.audit_log (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  user_id INT,
  user_name TEXT,
  user_email TEXT,
  accion TEXT NOT NULL,
  seccion TEXT,
  detalle JSONB DEFAULT '{}'::jsonb
);

-- 2. Índices para búsqueda eficiente
CREATE INDEX IF NOT EXISTS idx_audit_log_ts ON tb_v2.audit_log (ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON tb_v2.audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_seccion ON tb_v2.audit_log (seccion);

-- 3. Vista pública para consulta desde Streamlit
CREATE OR REPLACE VIEW public.audit_log_v2 AS
SELECT id, ts, user_id, user_name, user_email, accion, seccion, detalle
FROM tb_v2.audit_log;

-- 4. Función RPC: registrar actividad
CREATE OR REPLACE FUNCTION rpc_registrar_actividad(
  p_user_id INT,
  p_user_name TEXT,
  p_user_email TEXT,
  p_accion TEXT,
  p_seccion TEXT,
  p_detalle JSONB DEFAULT '{}'::jsonb
)
RETURNS JSON AS $$
BEGIN
  INSERT INTO tb_v2.audit_log (user_id, user_name, user_email, accion, seccion, detalle)
  VALUES (p_user_id, p_user_name, p_user_email, p_accion, p_seccion, p_detalle);

  RETURN json_build_object('ok', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Función RPC: obtener log de auditoría (con paginación)
CREATE OR REPLACE FUNCTION rpc_obtener_audit_log(
  p_limit INT DEFAULT 100,
  p_offset INT DEFAULT 0,
  p_user_id INT DEFAULT NULL,
  p_seccion TEXT DEFAULT NULL,
  p_desde TIMESTAMPTZ DEFAULT NULL,
  p_hasta TIMESTAMPTZ DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
  v_result JSON;
BEGIN
  SELECT json_agg(row_to_json(t))
  INTO v_result
  FROM (
    SELECT id, ts, user_id, user_name, user_email, accion, seccion, detalle
    FROM tb_v2.audit_log
    WHERE (p_user_id IS NULL OR user_id = p_user_id)
      AND (p_seccion IS NULL OR seccion = p_seccion)
      AND (p_desde IS NULL OR ts >= p_desde)
      AND (p_hasta IS NULL OR ts <= p_hasta)
    ORDER BY ts DESC
    LIMIT p_limit
    OFFSET p_offset
  ) t;

  RETURN COALESCE(v_result, '[]'::json);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

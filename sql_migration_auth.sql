-- =========================================================
-- MIGRACIÓN: Sistema de autenticación para Tío Bigotes
-- Ejecutar en Supabase SQL Editor
-- =========================================================

-- 1. Agregar columnas de autenticación a empleados_v2
ALTER TABLE empleados_v2
  ADD COLUMN IF NOT EXISTS email TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS telefono TEXT,
  ADD COLUMN IF NOT EXISTS password_hash TEXT,
  ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS permisos JSONB DEFAULT '[]'::jsonb;

-- 2. Crear el superadmin inicial (cambiar email/telefono según corresponda)
-- IMPORTANTE: La contraseña inicial es "admin123" (hash SHA-256)
-- El usuario DEBE cambiarla en el primer login
-- UPDATE empleados_v2
-- SET email = 'tu_email@ejemplo.com',
--     telefono = '34600000000',
--     password_hash = '240be518fabd2724ddb6f04eeb9d56b7e49218367c1f05b1c0a5353bcc455621',
--     must_change_password = TRUE,
--     rol = 'superadmin',
--     permisos = '["Productos","Empleados","Operativa","BI","Forecast","Pendientes","CargaVentas"]'::jsonb
-- WHERE nombre = 'TU_NOMBRE_AQUI';

-- 3. Función RPC: verificar login
CREATE OR REPLACE FUNCTION rpc_verificar_login(p_email TEXT, p_password_hash TEXT)
RETURNS JSON AS $$
DECLARE
  v_emp RECORD;
BEGIN
  SELECT id, nombre, email, telefono, rol, activo, must_change_password, permisos, local_id
  INTO v_emp
  FROM empleados_v2
  WHERE email = LOWER(TRIM(p_email))
    AND password_hash = p_password_hash;

  IF NOT FOUND THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Credenciales incorrectas');
  END IF;

  IF NOT v_emp.activo THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Usuario inactivo. Contacta al administrador.');
  END IF;

  RETURN json_build_object(
    'ok', TRUE,
    'id', v_emp.id,
    'nombre', v_emp.nombre,
    'email', v_emp.email,
    'telefono', v_emp.telefono,
    'rol', v_emp.rol,
    'must_change_password', v_emp.must_change_password,
    'permisos', v_emp.permisos,
    'local_id', v_emp.local_id
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Función RPC: cambiar contraseña
CREATE OR REPLACE FUNCTION rpc_cambiar_password(p_user_id INT, p_old_hash TEXT, p_new_hash TEXT)
RETURNS JSON AS $$
DECLARE
  v_current_hash TEXT;
BEGIN
  SELECT password_hash INTO v_current_hash
  FROM empleados_v2
  WHERE id = p_user_id;

  IF NOT FOUND THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Usuario no encontrado');
  END IF;

  IF v_current_hash IS DISTINCT FROM p_old_hash THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Contraseña actual incorrecta');
  END IF;

  UPDATE empleados_v2
  SET password_hash = p_new_hash,
      must_change_password = FALSE
  WHERE id = p_user_id;

  RETURN json_build_object('ok', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Función RPC: reset password (superadmin)
CREATE OR REPLACE FUNCTION rpc_reset_password(p_user_id INT, p_new_hash TEXT)
RETURNS JSON AS $$
BEGIN
  UPDATE empleados_v2
  SET password_hash = p_new_hash,
      must_change_password = TRUE
  WHERE id = p_user_id;

  IF NOT FOUND THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Usuario no encontrado');
  END IF;

  RETURN json_build_object('ok', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Función RPC: crear empleado con auth
CREATE OR REPLACE FUNCTION rpc_crear_empleado_v2(
  p_local_id INT,
  p_nombre TEXT,
  p_email TEXT,
  p_telefono TEXT,
  p_rol TEXT,
  p_password_hash TEXT,
  p_permisos JSONB,
  p_fecha_alta DATE
)
RETURNS JSON AS $$
DECLARE
  v_id INT;
BEGIN
  -- Verificar email duplicado
  IF EXISTS (SELECT 1 FROM empleados_v2 WHERE email = LOWER(TRIM(p_email))) THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Ya existe un usuario con ese email');
  END IF;

  INSERT INTO empleados_v2 (local_id, nombre, email, telefono, rol, password_hash, must_change_password, permisos, fecha_alta, activo)
  VALUES (p_local_id, TRIM(p_nombre), LOWER(TRIM(p_email)), TRIM(p_telefono), p_rol, p_password_hash, TRUE, p_permisos, p_fecha_alta, TRUE)
  RETURNING id INTO v_id;

  RETURN json_build_object('ok', TRUE, 'id', v_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Función RPC: actualizar permisos
CREATE OR REPLACE FUNCTION rpc_actualizar_permisos(p_user_id INT, p_permisos JSONB)
RETURNS JSON AS $$
BEGIN
  UPDATE empleados_v2
  SET permisos = p_permisos
  WHERE id = p_user_id;

  IF NOT FOUND THEN
    RETURN json_build_object('ok', FALSE, 'error', 'Usuario no encontrado');
  END IF;

  RETURN json_build_object('ok', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

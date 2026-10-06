BEGIN;

INSERT INTO modulos (nombre, nombre_corto, icono, ruta, en_navegacion, estatus)
VALUES ('UDP CUBICULOS', U&'Cub\00edculos', 'mdi mdi-door', '/udp_cubiculos', TRUE, 'A')
ON CONFLICT (nombre) DO UPDATE
SET nombre_corto = EXCLUDED.nombre_corto,
    icono = EXCLUDED.icono,
    ruta = EXCLUDED.ruta,
    en_navegacion = EXCLUDED.en_navegacion,
    estatus = EXCLUDED.estatus;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM roles WHERE nombre = 'ADMINISTRADOR' AND estatus = 'A') THEN
        RAISE EXCEPTION 'No existe el rol activo ADMINISTRADOR para asignar permisos de cubículos';
    END IF;
END;
$$;

INSERT INTO permisos (rol_id, modulo_id, nivel, nombre, estatus)
SELECT rol.id, modulo.id, 4, 'ADMINISTRADOR puede ADMINISTRAR en UDP CUBICULOS', 'A'
FROM roles AS rol
CROSS JOIN modulos AS modulo
WHERE rol.nombre = 'ADMINISTRADOR'
  AND rol.estatus = 'A'
  AND modulo.nombre = 'UDP CUBICULOS'
  AND modulo.estatus = 'A'
  AND NOT EXISTS (
      SELECT 1
      FROM permisos AS permiso
      WHERE permiso.nombre = 'ADMINISTRADOR puede ADMINISTRAR en UDP CUBICULOS'
  );

COMMIT;

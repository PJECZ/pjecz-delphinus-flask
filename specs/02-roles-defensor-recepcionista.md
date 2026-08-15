# SPEC 02 — Roles RECEPCIONISTA y DEFENSOR con selector de defensor en atenciones

> **Status:** Implementado
> **Depends on:** SPEC 01
> **Date:** 2026-08-06
> **Objective:** Crear los roles RECEPCIONISTA y DEFENSOR con sus permisos, y agregar un selector de defensor obligatorio en los formularios de atenciones usando `usuarios/select_json` mejorado.

## Alcance

**Dentro:**

- Crear rol `RECEPCIONISTA` con nivel 3 (VER, MODIFICAR y CREAR) en todos los módulos `udp_*` y nivel 1 (VER) en los demás.
- Crear rol `DEFENSOR` con nivel 2 (VER y MODIFICAR) en `UDP ATENCIONES` y nivel 1 (VER) en los demás.
- Agregar filas a `seed/roles_permisos.csv` para ambos roles.
- Agregar usuarios de muestra con ambos roles a `seed/usuarios_roles.csv`.
- Modificar `usuarios/select_json` para aceptar parámetro `rol` y filtrar usuarios por nombre de rol.
- Repropositar `usuario_id` en `UdpAtencion`: ahora significa el defensor asignado, no el creador.
- Agregar campo `defensor` (SelectField) al formulario `UdpAtencionForm`.
- Modificar plantillas `new.jinja2` y `edit.jinja2` para mostrar el selector de defensor que llama a `usuarios/select_json?rol=DEFENSOR`.
- Si el usuario actual tiene rol DEFENSOR, seleccionarlo por defecto en el selector.
- Mostrar texto `"{email}: {nombre} - {puesto}"` en las opciones del selector.
- Modificar `detail.jinja2` para mostrar el defensor asignado.

**Fuera de alcance (para specs futuros):**

- Migración de datos de usuarios existentes.
- Cambios en otros formularios que usen `select_json`.

## Modelo de datos

No se crean nuevas tablas. Solo se modifican tablas existentes.

### Tabla `roles` (semilla)

Dos nuevas filas:

| rol_id | nombre      |
| ------ | ----------- |
| 2      | RECEPCIONISTA |
| 3      | DEFENSOR    |

### Tabla `roles_permisos` (semilla)

Nuevas filas para cada rol con los niveles especificados:

**RECEPCIONISTA (rol_id=2):**

- Todos los módulos que comienzan con `UDP`: nivel 3
- Todos los demás módulos: nivel 1

**DEFENSOR (rol_id=3):**

- `UDP ATENCIONES`: nivel 2
- Todos los demás módulos: nivel 1

### Tabla `usuarios_roles` (semilla)

Agregar usuarios de muestra:

| usuario_id | email | nombres | apellido_paterno | roles | estatus |
| ---------- | ----- | ------- | ---------------- | ----- | ------- |
| 2 | recepcionista@pjecz.gob.mx | RECEPCIONISTA | PRUEBA | RECEPCIONISTA | A |
| 3 | defensor@pjecz.gob.mx | DEFENSOR | PRUEBA | DEFENSOR | A |

### Modelo `UdpAtencion` (sin cambios de esquema)

La columna `usuario_id` se repurposa: ahora significa "defensor asignado". No se crea columna nueva.

### Endpoint `usuarios/select_json`

Agregar parámetro `rol` (nombre del rol) para filtrar usuarios que tengan ese rol activo.

## Plan de implementación

1. Modificar `seed/roles_permisos.csv` para agregar las filas de RECEPCIONISTA (nivel 3 en módulos UDP, nivel 1 en los demás) y DEFENSOR (nivel 2 en UDP ATENCIONES, nivel 1 en los demás).
2. Modificar `seed/usuarios_roles.csv` para agregar los usuarios de muestra con ambos roles.
3. Modificar `blueprints/usuarios/views.py` en `select_json` para aceptar parámetro `rol` y filtrar por nombre de rol mediante join con `UsuarioRol` y `Rol`.
4. Modificar `blueprints/udp_atenciones/forms.py` para agregar campo `defensor` (SelectField, requerido, sin choices predefinidos).
5. Modificar `blueprints/udp_atenciones/views.py` en `new` y `edit` para guardar el `usuario_id` seleccionado (el defensor). En `new`, si el usuario actual tiene rol DEFENSOR, pasarlo como valor por defecto a la plantilla.
6. Modificar `blueprints/udp_atenciones/templates/udp_atenciones/new.jinja2` para agregar el select de defensor con JavaScript que llama a `usuarios/select_json?rol=DEFENSOR`.
7. Modificar `blueprints/udp_atenciones/templates/udp_atenciones/edit.jinja2` para agregar el select de defensor con JavaScript que llama a `usuarios/select_json?rol=DEFENSOR` y preselecciona el defensor actual.
8. Modificar `blueprints/udp_atenciones/templates/udp_atenciones/detail.jinja2` para mostrar "Defensor asignado" en lugar de "Asignado al usuario".
9. Verificar: `black .`, `isort .`, `ruff check .`.

## Criterios de aceptación

- [x] Rol RECEPCIONISTA creado con nivel 3 en todos los módulos `udp_*` y nivel 1 en los demás.
- [x] Rol DEFENSOR creado con nivel 2 en `UDP ATENCIONES` y nivel 1 en los demás.
- [x] Usuarios de muestra agregados a `usuarios_roles.csv` con los roles correspondientes.
- [x] `usuarios/select_json` acepta parámetro `rol` y filtra por nombre de rol.
- [x] Formulario de nueva atención muestra select de defensor obligatorio.
- [x] Formulario de editar atención muestra select de defensor obligatorio con el valor actual preseleccionado.
- [x] Si el usuario actual tiene rol DEFENSOR, aparece seleccionado por defecto al crear atención.
- [x] Opciones del select muestran formato `"{email}: {nombre} - {puesto}"`.
- [x] Detalle de atención muestra "Defensor asignado" con el email del defensor.
- [x] Código pasa `black .`, `isort .`, `ruff check .`.

## Decisiones

- **Sí:** Repropositar `usuario_id` en lugar de crear columna nueva. El campo ya existe, la semántica cambia pero el esquema no.
- **Sí:** Formato `"{email}: {nombre} - {puesto}"` para las opciones del select. Consistente con `select2_json` y más informativo que solo email.
- **Sí:** Parámetro `rol` por nombre (no por id). Más legible y los nombres de rol son únicos.
- **Sí:** Select obligatorio. El defensor es un dato esencial de la atención.
- **No:** Crear columna `defensor_usuario_id` separada. Innecesario si se repurposa `usuario_id`.
- **No:** Usar Select2. El usuario lo pidió explícitamente.

## Qué **no** está en este spec

- Migración de datos de usuarios existentes.
- Cambios en otros formularios que usen `select_json`.
- Roles adicionales más allá de RECEPCIONISTA y DEFENSOR.

# SPEC 03 — Advertencia de posible contraparte en detalle de persona

> **Status:** Implementado
> **Depends on:** SPEC 01
> **Date:** 2026-08-15
> **Objective:** Mostrar en el detalle de una persona un card con fondo amarillo que advierta cuando existan contrapartes que coincidan por (nombres y apellido_primero), CURP o fecha de nacimiento, con enlaces a sus detalles.

## Alcance

**Dentro:**

- Modificar la vista `detail` de `blueprints/udp_personas/views.py` para buscar contrapartes activas que coincidan con la persona por alguno de tres criterios:
  - `nombres` y `apellido_primero` exactamente iguales.
  - `curp` igual (solo si la persona tiene CURP no vacía).
  - `nacimiento_fecha` igual (solo si la persona tiene fecha de nacimiento).
- Los criterios se combinan con OR y el resultado se deduplica: cada contraparte aparece una sola vez.
- Pasar la lista de coincidencias a la plantilla `udp_personas/detail.jinja2`.
- Modificar `blueprints/udp_personas/templates/udp_personas/detail.jinja2` para mostrar, antes del card de datos de la persona, un card con fondo amarillo (`text-bg-warning`) con el listado de coincidencias.
- Cada elemento del listado muestra el nombre completo de la contraparte como enlace a `udp_contrapartes.detail`, seguido de su CURP y fecha de nacimiento.
- El card solo se muestra si el usuario actual tiene permiso VER en el módulo `UDP CONTRAPARTES`.

**Fuera de alcance (para specs futuros):**

- Indicar por cuál criterio coincidió cada contraparte.
- Advertencias en los formularios de nueva persona o edición de persona.
- Vínculo o relación en base de datos entre `udp_personas` y `udp_contrapartes`.
- Coincidencia por `apellido_segundo` u otros campos.
- Cambios en el blueprint `udp_contrapartes`.

## Modelo de datos

No se crean nuevas tablas ni columnas. Se reutilizan los modelos `UdpPersona` y `UdpContraparte` de SPEC 01.

La consulta de coincidencias se construye con condiciones OR sobre `UdpContraparte`:

```python
from sqlalchemy import or_

condiciones = [
    (UdpContraparte.nombres == udp_persona.nombres) & (UdpContraparte.apellido_primero == udp_persona.apellido_primero)
]
if udp_persona.curp:
    condiciones.append(UdpContraparte.curp == udp_persona.curp)
if udp_persona.nacimiento_fecha:
    condiciones.append(UdpContraparte.nacimiento_fecha == udp_persona.nacimiento_fecha)
posibles_contrapartes = (
    UdpContraparte.query.filter(UdpContraparte.estatus == "A")
    .filter(or_(*condiciones))
    .order_by(UdpContraparte.apellido_primero, UdpContraparte.apellido_segundo, UdpContraparte.nombres)
    .all()
)
```

## Plan de implementación

1. Modificar `blueprints/udp_personas/views.py`: importar `or_` de SQLAlchemy y el modelo `UdpContraparte`; en la vista `detail` construir las condiciones, ejecutar la consulta y pasar `posibles_contrapartes` a la plantilla. La página sigue funcionando igual si no hay coincidencias.
2. Modificar `blueprints/udp_personas/templates/udp_personas/detail.jinja2`: al inicio del bloque `content`, si `posibles_contrapartes` no está vacía y `current_user.can_view('UDP CONTRAPARTES')`, renderizar el card amarillo con la macro `detail.card` usando `border_class='text-bg-warning'`, título de advertencia y un `<ul>` con un `<li>` por contraparte (nombre completo enlazado, CURP y fecha de nacimiento).
3. Verificar: `black .`, `isort .`, `ruff check .`. Prueba manual: abrir el detalle de una persona que coincida con una contraparte y confirmar que aparece el card con el enlace funcional.

## Criterios de aceptación

- [x] Una persona que coincide por `nombres` y `apellido_primero` con una contraparte activa muestra el card amarillo con esa contraparte.
- [x] Una persona con CURP no vacía igual al de una contraparte activa muestra el card amarillo.
- [x] Una persona con fecha de nacimiento igual a la de una contraparte activa muestra el card amarillo.
- [x] Una contraparte que coincide por más de un criterio aparece una sola vez en el listado.
- [x] Una persona con CURP vacía no genera coincidencias por CURP.
- [x] Una persona sin fecha de nacimiento no genera coincidencias por fecha.
- [x] Las contrapartes eliminadas (estatus `B`) no aparecen en la advertencia.
- [x] Si no hay coincidencias, no se muestra ningún card amarillo.
- [x] Un usuario sin permiso VER en `UDP CONTRAPARTES` no ve el card aunque existan coincidencias.
- [x] Cada elemento del listado enlaza al detalle correcto de la contraparte.
- [x] El código pasa `black .`, `isort .`, `ruff check .`.

## Decisiones

- **Sí:** OR de los tres criterios con lista deduplicada. Pedido explícitamente; es lo más simple y una sola coincidencia basta para advertir.
- **Sí:** Coincidencia exacta por `nombres` y `apellido_primero`. Ambos modelos se guardan normalizados con `safe_string` (mayúsculas, sin acentos), así que la igualdad simple funciona.
- **Sí:** Omitir el criterio CURP cuando la persona tiene CURP vacía, y el de fecha cuando es `None`. De lo contrario todo registro sin dato coincidiría con todos los demás sin dato.
- **Sí:** Solo contrapartes con estatus `A`. Consistente con el resto de los listados del sistema.
- **Sí:** Card visible solo con permiso VER en `UDP CONTRAPARTES` y colocado antes del card de datos de la persona. Los enlaces apuntan a ese módulo; sin permiso darían error.
- **Sí:** Clase `text-bg-warning` de Bootstrap 5.3 pasada por `border_class` a la macro `detail.card`. No requiere modificar macros ni CSS.
- **Sí:** Listado renderizado en servidor con `<ul>`, sin DataTables ni JavaScript. Son pocos elementos y no necesitan paginación ni filtros.
- **No:** Indicar por cuál criterio coincidió cada contraparte. Complejidad innecesaria para una advertencia.
- **No:** Coincidencia flexible (ILIKE, sin distinguir acentos). Generaría falsos positivos; la normalización al guardar ya cubre el caso.
- **No:** Advertencia tipo flash al crear o editar persona. Ya existe una advertencia de posible duplicado entre personas; esto es otro asunto.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Falsos positivos por fecha de nacimiento sola (personas distintas nacidas el mismo día) | Es solo una advertencia, no un bloqueo; el usuario verifica manualmente abriendo los enlaces. |
| Coincidencias exactas que fallan por capturas históricas sin normalizar | Los datos se guardan con `safe_string`; si aparecen casos viejos, se corrigen editando el registro. |

## Qué **no** está en este spec

- Indicar el criterio de coincidencia por contraparte.
- Advertencias en los formularios de nueva persona o edición de persona.
- Vínculo en base de datos entre personas y contrapartes.
- Coincidencia por `apellido_segundo` u otros campos.
- Cambios en el blueprint `udp_contrapartes`.

Cada uno de esos, si llega, va en su propio spec.

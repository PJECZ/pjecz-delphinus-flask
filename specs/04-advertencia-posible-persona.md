# SPEC 04 — Advertencia de posible persona en detalle de contraparte

> **Status:** Implementado
> **Depends on:** SPEC 01
> **Date:** 2026-08-15
> **Objective:** Mostrar en el detalle de una contraparte un card con fondo amarillo que advierta cuando existan personas que coincidan por (nombres y apellido_primero), CURP o fecha de nacimiento, con enlaces a sus detalles.

## Alcance

**Dentro:**

- Modificar la vista `detail` de `blueprints/udp_contrapartes/views.py` para buscar personas activas que coincidan con la contraparte por alguno de tres criterios:
  - `nombres` y `apellido_primero` exactamente iguales.
  - `curp` igual (solo si la contraparte tiene CURP no vacía).
  - `nacimiento_fecha` igual (solo si la contraparte tiene fecha de nacimiento).
- Los criterios se combinan con OR y el resultado se deduplica: cada persona aparece una sola vez.
- Pasar la lista de coincidencias a la plantilla `udp_contrapartes/detail.jinja2`.
- Modificar `blueprints/udp_contrapartes/templates/udp_contrapartes/detail.jinja2` para mostrar, antes del card de datos de la contraparte, un card con fondo amarillo (`text-bg-warning`) titulado «Advertencia: posible persona» con el listado de coincidencias.
- Cada elemento del listado muestra el nombre completo de la persona como enlace a `udp_personas.detail`, seguido de su CURP y fecha de nacimiento (solo si tienen valor).
- El card solo se muestra si el usuario actual tiene permiso VER en el módulo `UDP PERSONAS`.

**Fuera de alcance (para specs futuros):**

- Indicar por cuál criterio coincidió cada persona.
- Advertencias en los formularios de nueva contraparte o edición de contraparte.
- Vínculo o relación en base de datos entre `udp_contrapartes` y `udp_personas`.
- Coincidencia por `apellido_segundo` u otros campos.
- Cambios en el blueprint `udp_personas`.

## Modelo de datos

No se crean nuevas tablas ni columnas. Se reutilizan los modelos `UdpContraparte` y `UdpPersona` de SPEC 01.

La consulta de coincidencias se construye con condiciones OR sobre `UdpPersona`:

```python
from sqlalchemy import or_

condiciones = [
    (UdpPersona.nombres == udp_contraparte.nombres) & (UdpPersona.apellido_primero == udp_contraparte.apellido_primero)
]
if udp_contraparte.curp:
    condiciones.append(UdpPersona.curp == udp_contraparte.curp)
if udp_contraparte.nacimiento_fecha:
    condiciones.append(UdpPersona.nacimiento_fecha == udp_contraparte.nacimiento_fecha)
posibles_personas = (
    UdpPersona.query.filter(UdpPersona.estatus == "A")
    .filter(or_(*condiciones))
    .order_by(UdpPersona.apellido_primero, UdpPersona.apellido_segundo, UdpPersona.nombres)
    .all()
)
```

## Plan de implementación

1. Modificar `blueprints/udp_contrapartes/views.py`: importar `or_` de SQLAlchemy y el modelo `UdpPersona`; en la vista `detail` construir las condiciones, ejecutar la consulta y pasar `posibles_personas` a la plantilla. La página sigue funcionando igual si no hay coincidencias.
2. Modificar `blueprints/udp_contrapartes/templates/udp_contrapartes/detail.jinja2`: al inicio del bloque `content`, si `posibles_personas` no está vacía y `current_user.can_view('UDP PERSONAS')`, renderizar el card amarillo con la macro `detail.card` usando `border_class='text-bg-warning'`, título «Advertencia: posible persona» y un `<ul>` con un `<li>` por persona (nombre completo enlazado, CURP y fecha de nacimiento).
3. Verificar: `black .`, `isort .`, `ruff check .`. Prueba manual: abrir el detalle de una contraparte que coincida con una persona y confirmar que aparece el card con el enlace funcional.

## Criterios de aceptación

- [x] Una contraparte que coincide por `nombres` y `apellido_primero` con una persona activa muestra el card amarillo con esa persona.
- [x] Una contraparte con CURP no vacía igual al de una persona activa muestra el card amarillo.
- [x] Una contraparte con fecha de nacimiento igual a la de una persona activa muestra el card amarillo.
- [x] Una persona que coincide por más de un criterio aparece una sola vez en el listado.
- [x] Una contraparte con CURP vacía no genera coincidencias por CURP.
- [x] Una contraparte sin fecha de nacimiento no genera coincidencias por fecha.
- [x] Las personas eliminadas (estatus `B`) no aparecen en la advertencia.
- [x] Si no hay coincidencias, no se muestra ningún card amarillo.
- [x] Un usuario sin permiso VER en `UDP PERSONAS` no ve el card aunque existan coincidencias.
- [x] Cada elemento del listado enlaza al detalle correcto de la persona.
- [x] El código pasa `black .`, `isort .`, `ruff check .`.

## Decisiones

- **Sí:** Espejo exacto de SPEC 03 en dirección contraria (contraparte → persona). Confirmado por el usuario; mantiene consistencia entre ambos módulos.
- **Sí:** OR de los tres criterios con lista deduplicada. Pedido explícitamente; es lo más simple y una sola coincidencia basta para advertir.
- **Sí:** Coincidencia exacta por `nombres` y `apellido_primero`. Ambos modelos se guardan normalizados con `safe_string` (mayúsculas, sin acentos), así que la igualdad simple funciona.
- **Sí:** Omitir el criterio CURP cuando la contraparte tiene CURP vacía, y el de fecha cuando es `None`. De lo contrario todo registro sin dato coincidiría con todos los demás sin dato.
- **Sí:** Solo personas con estatus `A`. Consistente con el resto de los listados del sistema.
- **Sí:** Card visible solo con permiso VER en `UDP PERSONAS` y colocado antes del card de datos de la contraparte. Los enlaces apuntan a ese módulo; sin permiso darían error.
- **Sí:** Título «Advertencia: posible persona». Espejo del título «Advertencia: posible contraparte» de SPEC 03.
- **Sí:** Clase `text-bg-warning` de Bootstrap 5.3 pasada por `border_class` a la macro `detail.card`. No requiere modificar macros ni CSS.
- **Sí:** Listado renderizado en servidor con `<ul>`, sin DataTables ni JavaScript. Son pocos elementos y no necesitan paginación ni filtros.
- **No:** Indicar por cuál criterio coincidió cada persona. Complejidad innecesaria para una advertencia.
- **No:** Coincidencia flexible (ILIKE, sin distinguir acentos). Generaría falsos positivos; la normalización al guardar ya cubre el caso.
- **No:** Advertencia tipo flash al crear o editar contraparte. Ya existe una advertencia de CURP duplicado entre contrapartes; esto es otro asunto.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Falsos positivos por fecha de nacimiento sola (personas distintas nacidas el mismo día) | Es solo una advertencia, no un bloqueo; el usuario verifica manualmente abriendo los enlaces. |
| Coincidencias exactas que fallan por capturas históricas sin normalizar | Los datos se guardan con `safe_string`; si aparecen casos viejos, se corrigen editando el registro. |

## Qué **no** está en este spec

- Indicar el criterio de coincidencia por persona.
- Advertencias en los formularios de nueva contraparte o edición de contraparte.
- Vínculo en base de datos entre contrapartes y personas.
- Coincidencia por `apellido_segundo` u otros campos.
- Cambios en el blueprint `udp_personas`.

Cada uno de esos, si llega, va en su propio spec.

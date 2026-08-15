# SPEC 01 — UDP Contrapartes independientes con vínculo a atenciones

> **Status:** Implementado
> **Depends on:** —
> **Date:** 2026-08-04
> **Objective:** Crear tabla `udp_contrapartes` independiente, tabla intermedia `udp_atenciones_contrapartes`, y restricción de unicidad CURP que permita valores vacíos.

## Scope

**In:**

- Nueva tabla `udp_contrapartes` con las mismas columnas que `udp_personas_contrapartes` pero sin FK a `udp_personas`.
- Nueva tabla intermedia `udp_atenciones_contrapartes` que vincula atenciones con contrapartes (cada atención tiene una contraparte; una contraparte reutilizable en varias atenciones).
- Restricción de unicidad parcial en CURP (unique donde CURP no sea vacío) aplicada a `udp_contrapartes` y a `udp_personas`.
- Nuevo blueprint `udp_contrapartes` con CRUD completo (vistas, formularios, plantillas).
- Crear vista `select_json` para entregar las contrapartes en formato JSON para selectores en formularios. Debe poder recibir desde cuatro caracteres para filtrar por CURP o nombre o apellido paterno o apellido materno.
- Registro del módulo `UDP CONTRAPARTES` y permisos en archivos semilla.
- Eliminar el blueprint existente `udp_personas_contrapartes` así como sus relaciones y vistas/formularios/plantillas.
  - Eliminar el módulo `UDP PERSONAS CONTRAPARTES` de los archivos semilla.
  - Eliminar el blueprint `udp_personas_contrapartes` y sus vistas/formularios/plantillas.
  - Retirar la relación `udp_personas_contrapartes` de `UdpPersona`.
- Modificar las vistas/formularios de `udp_atenciones` para seleccionar contraparte en el formulario de atención.
  - En el formulario de atención, agregar un selector de contraparte que liste las contrapartes existentes (de `udp_contrapartes`) que llame a la vista `select_json` para filtrar por CURP o nombre o apellido paterno o apellido materno.

**Fuera de alcance (para specs futuros):**

- Migración de datos.

## Data model

### Tabla `udp_contrapartes`

```python
class UdpContraparte(database.Model, UniversalMixin):
    __tablename__ = "udp_contrapartes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombres: Mapped[str] = mapped_column(String(256))
    apellido_primero: Mapped[str] = mapped_column(String(256))
    apellido_segundo: Mapped[Optional[str]] = mapped_column(String(256), default="", server_default="")
    curp: Mapped[Optional[str]] = mapped_column(CHAR(18), default="", server_default="")
    nacimiento_fecha: Mapped[Optional[date]]
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024), default="", server_default="")

    # Hijos
    udp_atenciones_contrapartes: Mapped[list["UdpAtencionContraparte"]] = relationship(back_populates="udp_contraparte")
```

Misma estructura de columnas que `udp_personas_contrapartes`. Sin FK a `udp_personas`. Propiedad `nombre_completo` idéntica.

### Tabla `udp_atenciones_contrapartes`

```python
class UdpAtencionContraparte(database.Model, UniversalMixin):
    __tablename__ = "udp_atenciones_contrapartes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    udp_atencion: Mapped["UdpAtencion"] = relationship(back_populates="udp_atencion_contraparte")
    udp_atencion_id: Mapped[int] = mapped_column(ForeignKey("udp_atenciones.id"), unique=True)
    udp_contraparte: Mapped["UdpContraparte"] = relationship(back_populates="udp_atenciones_contrapartes")
    udp_contraparte_id: Mapped[int] = mapped_column(ForeignKey("udp_contrapartes.id"))
```

`unique=True` en `udp_atencion_id` garantiza que cada atención tenga exactamente una contraparte. Una contraparte puede aparecer en múltiples atenciones.

### Restricción CURP única (parcial)

```python
from sqlalchemy import Index, text

# En UdpContraparte (agregar a __table_args__ existente o crear):
__table_args__ = (
    Index("ix_udp_contrapartes_curp_no_vacio", "curp", unique=True, postgresql_where=text("curp != ''")),
)

# En UdpPersona (agregar a __table_args__ existente o crear):
__table_args__ = (
    Index("ix_udp_personas_curp_no_vacio", "curp", unique=True, postgresql_where=text("curp != ''")),
)
```

Permite múltiples filas con CURP vacía, pero enforce unicidad cuando CURP tiene valor.

## Implementation plan

1. Crear blueprint `blueprints/udp_contrapartes/` con `__init__.py` vacío y `models.py` con el modelo `UdpContraparte` incluyendo el índice parcial CURP.
2. Crear `blueprints/udp_atenciones_contrapartes/models.py` con el modelo `UdpAtencionContraparte` y sus relaciones.
3. Modificar `blueprints/udp_atenciones/models.py` para agregar la relación `udp_atencion_contraparte` con `back_populates`.
4. Modificar `blueprints/udp_personas/models.py` para agregar el índice parcial CURP.
5. Crear `blueprints/udp_contrapartes/forms.py` con `UdpContraparteForm` (mismos campos que `UdpPersonaContraparteForm`).
6. Crear `blueprints/udp_contrapartes/views.py` con vistas: `datatable_json`, `list_active`, `list_inactive`, `detail`, `new`, `edit`, `delete`, `recover`.
7. Crear plantillas en `blueprints/udp_contrapartes/templates/udp_contrapartes/`: `list.jinja2`, `detail.jinja2`, `new.jinja2`, `edit.jinja2`.
8. Registrar blueprint en `pjecz_delphinus_flask/app.py`.
9. Agregar módulo `UDP CONTRAPARTES` a `seed/modulos.csv` y columna de permisos a `seed/roles_permisos.csv`.
10. Eliminar blueprint `blueprints/udp_personas_contrapartes/`
10. Verificar: `black .`, `isort .`, `ruff check .`.

## Acceptance criteria

- [x] Tabla `udp_contrapartes` creada con columnas: id, nombres, apellido_primero, apellido_segundo, curp, nacimiento_fecha, observaciones, creado, modificado, estatus.
- [x] Tabla `udp_contrapartes` sin FK a `udp_personas`.
- [x] Índice parcial CURP único en `udp_contrapartes` (permite vacíos, rechaza duplicados con valor).
- [x] Índice parcial CURP único en `udp_personas` (mismo comportamiento).
- [x] Tabla intermedia `udp_atenciones_contrapartes` creada con FKs a `udp_atenciones` y `udp_contrapartes`.
- [x] `udp_atencion_id` tiene `unique=True` en la tabla intermedia.
- [x] Relación `udp_atencion_contraparte` agregada en `UdpAtencion`.
- [x] Blueprint `udp_contrapartes` registrado en `app.py`.
- [x] Módulo `UDP CONTRAPARTES` presente en `seed/modulos.csv`.
- [x] Permisos del módulo presente en `seed/roles_permisos.csv`.
- [x] CRUD funcional: listar, ver detalle, crear, editar, eliminar (soft delete), recuperar.
- [x] Código pasa `black .`, `isort .`, `ruff check .`.

## Decisions

- **Sí:** Blueprint independiente `udp_contrapartes` separado de `udp_personas_contrapartes`. La tabla nueva es conceptualmente distinta (contraparte genérica, no ligada a una persona).
- **Sí:** Tabla intermedia `udp_atenciones_contrapartes` en lugar de FK directo en `udp_atenciones`. Permite mantener la relación limpia y extensible.
- **Sí:** Índice parcial con `postgresql_where=text("curp != ''")` para unicidad CURP. En PostgreSQL, los índices parciales permiten múltiples filas con cadena vacía pero rechazan duplicados con valor.
- **Si:** Eliminar el blueprint `udp_personas_contrapartes` existente.
- **No:** Migración de datos. La base de datos es de prueba y se reconstruye manualmente.
- **No:** Agregar selector de contraparte en el formulario de atenciones. Va en otro spec.

## Risks

| Riesgo | Mitigación |
| --- | --- |
| Índice parcial no soportado en SQLite (dev) | PostgreSQL es el DB engine en producción. SQLite no se usa. |
| Confusión entre `udp_personas_contrapartes` y `udp_contrapartes` | Nombres claramente distintos. El spec documenta la diferencia. |

## What is **not** in this spec

- Migración de datos.

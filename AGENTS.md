# AGENTS.md

Flask app for PJECZ Defensoría case management. Spanish-language codebase.

## Quick commands

```bash
# Run dev server (uvicorn with reload)
python main.py

# CLI (Typer-based, in cli/app.py)
python cli/app.py db reiniciar        # drop tables + seed from CSV (DEVELOPMENT only)
python cli/app.py db inicializar      # drop + create tables
python cli/app.py db alimentar        # seed from seed/*.csv
python cli/app.py db respaldar        # export DB to CSV
python cli/app.py usuarios nueva-api-key EMAIL
python cli/app.py usuarios nueva-contrasena EMAIL

# Formatting & linting (line-length=128 everywhere)
black .
isort .
ruff check .
```

## Architecture

- **Entry**: `main.py` → uvicorn loads `pjecz_delphinus_flask.app:create_app()` (app factory)
- **App factory**: `pjecz_delphinus_flask/app.py` creates Flask app, registers blueprints, inits extensions
- **Blueprints** in `pjecz_delphinus_flask/blueprints/`: each has `views.py`, `models.py`, `forms.py`, `templates/`
- **Models** live in each blueprint's own `models.py` (e.g. `blueprints/usuarios/models.py`), not a shared file
- **Views** in each blueprint's `views.py`: standard functions are `datatable_json`, `list_active`, `list_inactive`, `detail`, `new`, `edit`, `delete`, `recover`
- **Forms** in each blueprint's `forms.py`: Flask-WTF form classes
- **Templates** in each blueprint's `templates/<blueprint_name>/`: Jinja2 with `.jinja2` extension (not `.html`). Common: `list.jinja2`, `detail.jinja2`, `new.jinja2`, `edit.jinja2`
- **Decorators** in `blueprints/usuarios/decorators.py`: `permission_required(module, level)` and `anonymous_required`
- **CLI** in `cli/`: separate Typer app with `db` and `usuarios` subcommands
- **Lib** in `pjecz_delphinus_flask/lib/`: shared utils (safe_string, datatables, cryptography, pwgen, universal_mixin, safe_next_url)
- **Config** in `pjecz_delphinus_flask/config/`: `settings.py` (pydantic-settings), `extensions.py` (Flask extensions)
- **Seed data**: CSV files in `seed/` for database seeding

## Key patterns

- All models inherit `UniversalMixin` which adds `creado`, `modificado`, `estatus` columns and `save()`/`delete()`/`recover()`/`encode_id()`/`decode_id()` methods
- Soft delete: `estatus="A"` active, `estatus="B"` deleted
- IDs exposed via HashIDs (salt from env `SALT`), use `model.encode_id()` / `Model.decode_id()`
- Passwords hashed with passlib `pbkdf2_sha256` (see `extensions.py` `pwd_context`)
- Permissions system: `Usuario` → `UsuarioRol` → `Rol` → `Permiso` → `Modulo`, levels 0-4 (VER, CREAR, MODIFICAR, ADMINISTRAR)
- Templates use `.jinja2` extension

## Environment

- Python 3.14, managed by uv
- PostgreSQL via psycopg2-binary
- `.env` loaded by python-dotenv (not committed)
- Key env vars: `SQLALCHEMY_DATABASE_URI`, `SECRET_KEY`, `SALT`, `DEPLOYMENT_ENVIRONMENT`, `TZ`
- `DEPLOYMENT_ENVIRONMENT=PRODUCTION` prevents DB reset commands

## Gotchas

- CLI commands push app context at import time: `app.app_context().push()`
- Ruff ignores F821 (undefined variable) and RUF012 (mutable class attributes)
- No test suite yet (tests/ is empty)
- Production uses Gunicorn (gthread, 4 workers × 2 threads); dev uses uvicorn with reload

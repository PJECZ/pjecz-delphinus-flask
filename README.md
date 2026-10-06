# pjecz-delphinus-flask

Plataforma para las atenciones de Defensoría.

# Uso

Inicializar el entorno virtual, cargar las variables y aiases por medio del `.bashrc`

```bash
source .bashrc
```

Ejecutar la ayuda del CLI

```bash
cli --help
```

Arrancar Flask

```bash
arrancar
```

# Instalación

Crear el entorno virtual

```bash
python3.11 -m venv .venv
```

Ingresar al entorno virtual

```bash
source .venv/bin/activate
```

Actualizar el gestor de paquetes **pip**

```bash
pip install --upgrade pip
```

Si no lo tiene, instalar el paquete **uv** para gestionar las dependencias

```bash
pip install uv
```

Instalar las dependencias por medio de **uv**

```bash
uv sync
```

# Configuración

Copiar el archivo `.env.example` a `.env`

```bash
cp .env.example .env
```

Editar el archivo `.env`

```bash
nano .env
```

Crear el archivo `.bashrc` que servirá para activar el entorno virtual y cargar las variables de entorno

```bash
if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

if command -v figlet &> /dev/null
then
    figlet Hercules BETA Flask
else
    echo "== Hercules BETA Flask"
fi
echo

if [ -f .env ]
then
    echo "-- Variables de entorno"
    export $(grep -v '^#' .env | xargs)
    # source .env && export $(sed '/^#/d' .env | cut -d= -f1)
    echo "   DB_HOST: ${DB_HOST}"
    echo "   DB_PORT: ${DB_PORT}"
    echo "   DB_NAME: ${DB_NAME}"
    echo "   DB_USER: ${DB_USER}"
    echo "   DB_PASS: ${DB_PASS}"
    echo "   DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT}"
    echo "   ESTADO_CLAVE: ${ESTADO_CLAVE}"
    echo "   FERNET_KEY: ${FERNET_KEY}"
    echo "   GOOGLE_APPLICATION_CREDENTIALS: ${GOOGLE_APPLICATION_CREDENTIALS}"
    echo "   HOST: ${HOST}"
    echo "   MUNICIPIO_CLAVE: ${MUNICIPIO_CLAVE}"
    echo "   REDIS_URL: ${REDIS_URL}"
    echo "   SALT: ${SALT}"
    echo "   SQLALCHEMY_DATABASE_URI: ${SQLALCHEMY_DATABASE_URI}"
    echo "   TASK_QUEUE: ${TASK_QUEUE}"
    echo "   TZ: ${TZ}"
    echo
    export PGHOST=$DB_HOST
    export PGPORT=$DB_PORT
    export PGDATABASE=$DB_NAME
    export PGUSER=$DB_USER
    export PGPASSWORD=$DB_PASS
fi

if [ -d .venv ]
then
    echo "-- Python Virtual Environment"
    source .venv/bin/activate
    echo "   $(python3 --version)"
    export PYTHONPATH=$(pwd)
    echo "   PYTHONPATH: ${PYTHONPATH}"
    echo
    echo "-- Command Line Interface"
    alias cli="python3 cli/app.py"
    echo "   cli = python3 cli/app.py"
    echo
    echo "-- Flask 127.0.0.1:5000"
    alias arrancar="flask run --port=5000"
    echo "   arrancar = flask run --port=5000"
    echo
fi
# importar desde seed
# docker compose exec app python cli/app.py db reiniciar

#nueva contraseña
#docker compose exec app python cli/app.py usuarios nueva-contrasena correodelusuario@pjecz.gob.mx


```

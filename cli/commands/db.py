"""
CLI DB
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress
from sqlalchemy import text
from typer import Typer

from pjecz_delphinus_flask.app import create_app
from pjecz_delphinus_flask.blueprints.autoridades.models import Autoridad
from pjecz_delphinus_flask.blueprints.distritos.models import Distrito
from pjecz_delphinus_flask.blueprints.estados.models import Estado
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.municipios.models import Municipio
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.roles.models import Rol
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.udp_atenciones.models import UdpAtencion
from pjecz_delphinus_flask.blueprints.udp_sexos.models import UdpSexo
from pjecz_delphinus_flask.blueprints.udp_tipos_condiciones.models import UdpTipoCondicion
from pjecz_delphinus_flask.blueprints.udp_tipos_tramites.models import UdpTipoTramite
from pjecz_delphinus_flask.blueprints.udp_tipos_visitas.models import UdpTipoVisita
from pjecz_delphinus_flask.blueprints.udp_ingresos.models import UdpIngreso
from pjecz_delphinus_flask.blueprints.udp_domicilios.models import UdpDomicilio
from pjecz_delphinus_flask.blueprints.usuarios.models import Usuario
from pjecz_delphinus_flask.blueprints.usuarios_roles.models import UsuarioRol
from pjecz_delphinus_flask.config.extensions import database, pwd_context
from pjecz_delphinus_flask.lib.pwgen import generar_contrasena
from pjecz_delphinus_flask.lib.safe_string import safe_clave, safe_email, safe_string, safe_int



# Rutas a los archivos CSV
AUTORIDADES_CSV = "seed/autoridades.csv"
DISTRITOS_CSV = "seed/distritos.csv"
ESTADOS_CSV = "seed/estados.csv"
MODULOS_CSV = "seed/modulos.csv"
MUNICIPIOS_CSV = "seed/municipios.csv"
PERMISOS_CSV = "seed/roles_permisos.csv"
ROLES_CSV = "seed/roles_permisos.csv"
USUARIOS_CSV = "seed/usuarios_roles.csv"
USUARIOS_ROLES_CSV = "seed/usuarios_roles.csv"
UDP_PERSONAS_CSV = "seed/PERSONAS.csv"
UDP_PERSONAS_ATENCIONES_CSV = "seed/ATENCIONES.csv"
UDP_SEXOS_CSV = "seed/udp_sexos.csv"
UDP_TIPOS_CONDICIONES_CSV = "seed/udp_tipos_condiciones.csv"
UDP_TIPOS_TRAMITES_CSV = "seed/udp_tipos_tramites.csv"
UDP_TIPOS_VISITAS_CSV = "seed/udp_tipos_visitas.csv"

# Cargar variables de entorno
load_dotenv()
DEPLOYMENT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEVELOPMENT").upper()
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")

# Inicializar la aplicación
app = create_app()
app.app_context().push()

db = Typer()


def alimentar_modulos():
    """Alimentar Modulos"""
    console = Console()
    ruta_csv = Path(MODULOS_CSV)
    if not ruta_csv.exists():
        console.print(f"[red]ERROR: {ruta_csv.name} no se encontró.")
        sys.exit(1)
    if not ruta_csv.is_file():
        console.print(f"[red]ERROR: {ruta_csv.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando modulos...")
    contador = 0
    with open(ruta_csv, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            modulo_id = int(row["modulo_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], do_unidecode=False, save_enie=True, to_uppercase=False)
            icono = row["icono"]
            ruta = row["ruta"]
            en_navegacion = row["en_navegacion"] == "1"
            estatus = row["estatus"]
            if modulo_id != contador + 1:
                console.print(f"[red]ERROR: modulo_id {modulo_id} no es consecutivo")
                sys.exit(1)
            Modulo(
                nombre=nombre,
                nombre_corto=nombre_corto,
                icono=icono,
                ruta=ruta,
                en_navegacion=en_navegacion,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} modulos alimentados.")


def alimentar_roles():
    """Alimentar Roles"""
    console = Console()
    ruta = Path(ROLES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            rol_id = int(row["rol_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if rol_id != contador + 1:
                console.print(f"[red]ERROR: rol_id {rol_id} no es consecutivo")
                sys.exit(1)
            Rol(
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} roles alimentados.")


def alimentar_permisos():
    """Alimentar Permisos"""
    console = Console()
    ruta = Path(PERMISOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    modulos = Modulo.query.all()
    if len(modulos) == 0:
        console.print("[red]ERROR: No hay modulos alimentados.")
        sys.exit(1)
    console.print("Alimentando permisos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            rol_id = int(row["rol_id"])
            estatus = row["estatus"]
            rol = Rol.query.get(rol_id)
            if rol is None:
                console.print(f"[red]ERROR: rol_id {rol_id} no existe")
                sys.exit(1)
            for modulo in modulos:
                columna = modulo.nombre.lower()
                if columna not in row:
                    continue
                if row[columna] == "":
                    continue
                try:
                    nivel = int(row[columna])
                except ValueError:
                    nivel = 0
                nivel = max(0, nivel)
                nivel = min(4, nivel)
                if nivel == 0:
                    continue
                Permiso(
                    rol=rol,
                    modulo=modulo,
                    nivel=nivel,
                    nombre=f"{rol.nombre} puede {Permiso.NIVELES[nivel]} en {modulo.nombre}",
                    estatus=estatus,
                ).save()
            contador += 1
    console.print(f"[green]{contador} permisos alimentados.")


def alimentar_distritos():
    """Alimentar Distritos"""
    console = Console()
    ruta = Path(DISTRITOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando distritos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            distrito_id = int(row["distrito_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], save_enie=True)
            estatus = row["estatus"]
            if distrito_id != contador + 1:
                console.print(f"[red]ERROR: distrito_id {distrito_id} no es consecutivo")
                sys.exit(1)
            Distrito(
                clave=clave,
                nombre=nombre,
                nombre_corto=nombre_corto,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} distritos alimentados.")


def alimentar_autoridades():
    """Alimentar Autoridades"""
    console = Console()
    ruta = Path(AUTORIDADES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    distrito_nd = Distrito.query.filter_by(clave="ND").first()
    if distrito_nd is None:
        console.print("[red]ERROR: No se encontró el distrito 'ND'.")
        sys.exit(1)
    console.print("Alimentando autoridades...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si autoridad_id NO es consecutivo, se inserta una autoridad "NO EXISTE"
            autoridad_id = int(row["autoridad_id"])
            while autoridad_id > contador + 1:
                Autoridad(
                    distrito_id=distrito_nd.id,
                    clave=f"NE-{contador}",
                    descripcion="NO EXISTE",
                    descripcion_corta="NO EXISTE",
                    estatus="B",
                ).save()
                contador += 1
            distrito_id = int(row["distrito_id"])
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                console.print(f"[red]AVISO: distrito_id {distrito_id} no existe")
                sys.exit(1)
            clave = safe_clave(row["clave"])
            descripcion = safe_string(row["descripcion"], save_enie=True)
            descripcion_corta = safe_string(row["descripcion_corta"], save_enie=True)
            estatus = row["estatus"]
            Autoridad(
                distrito=distrito,
                clave=clave,
                descripcion=descripcion,
                descripcion_corta=descripcion_corta,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} autoridades alimentadas.")


def alimentar_usuarios():
    """Alimentar Usuarios"""
    console = Console()
    ruta = Path(USUARIOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()
    if autoridad_nd is None:
        console.print("[red]ERROR: No se encontró la autoridad 'ND'.")
        sys.exit(1)
    console.print("Alimentando usuarios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si usuario_id NO es consecutivo, se inserta un usuario "NO EXISTE"
            usuario_id = int(row["usuario_id"])
            while usuario_id > contador + 1:
                Usuario(
                    autoridad_id=autoridad_nd.id,
                    email=f"no-existe-{contador}@server.com",
                    nombres="NO EXISTE",
                    apellido_paterno="",
                    apellido_materno="",
                    curp="",
                    puesto="",
                    estatus="B",
                    api_key="",
                    api_key_expiracion=datetime(year=2000, month=1, day=1),
                    contrasena=pwd_context.hash(generar_contrasena()),
                ).save()
                contador += 1
            autoridad_clave = safe_clave(row["autoridad_clave"])
            email = safe_email(row["email"])
            nombres = safe_string(row["nombres"], save_enie=True)
            apellido_paterno = safe_string(row["apellido_paterno"], save_enie=True)
            apellido_materno = safe_string(row["apellido_materno"], save_enie=True)
            curp = safe_string(row["curp"])
            puesto = safe_string(row["puesto"], save_enie=True)
            estatus = row["estatus"]
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
            if autoridad is None:
                console.print(f"[red]ERROR: autoridad_clave {autoridad_clave} no existe")
                sys.exit(1)
            Usuario(
                autoridad=autoridad,
                email=email,
                nombres=nombres,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                curp=curp,
                puesto=puesto,
                estatus=estatus,
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1),
                contrasena=pwd_context.hash(generar_contrasena()),
            ).save()
            contador += 1
    console.print(f"[green]{contador} usuarios alimentados.")


def alimentar_usuarios_roles():
    """Alimentar Usuarios-Roles"""
    console = Console()
    ruta = Path(USUARIOS_ROLES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    usuarios_que_no_existen = []
    console.print("Alimentando usuarios-roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            usuario_id = int(row["usuario_id"])
            usuario = Usuario.query.get(usuario_id)
            if usuario is None:
                usuarios_que_no_existen.append(str(usuario_id))
                continue
            for rol_nombre in row["roles"].split(","):
                rol_nombre = rol_nombre.strip().upper()
                rol = Rol.query.filter_by(nombre=rol_nombre).first()
                if rol is None:
                    continue
                UsuarioRol(
                    usuario=usuario,
                    rol=rol,
                    descripcion=f"{usuario.email} en {rol.nombre}",
                ).save()
                contador += 1
    if usuarios_que_no_existen:
        console.print(f"[yellow]AVISO: {','.join(usuarios_que_no_existen)} usuarios no existen.")
    console.print(f"[green]{contador} usuarios-roles alimentados.")


def alimentar_udp_sexos():
    """Alimentar UDP Sexos"""
    console = Console()
    ruta = Path(UDP_SEXOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando udp_sexos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_sexo_id = int(row["udp_sexo_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            if udp_sexo_id != contador + 1:
                console.print(f"[red]ERROR: udp_sexo_id {udp_sexo_id} no es consecutivo")
                sys.exit(1)
            UdpSexo(nombre=nombre).save()
            contador += 1
    console.print(f"[green]{contador} udp_sexos alimentados.")


def alimentar_udp_tipos_condiciones():
    """Alimentar UDP Tipos Condiciones"""
    console = Console()
    ruta = Path(UDP_TIPOS_CONDICIONES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando udp_tipos_condiciones...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_tipo_condicion_id = int(row["udp_tipo_condicion_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            if udp_tipo_condicion_id != contador + 1:
                console.print(f"[red]ERROR: udp_tipo_condicion_id {udp_tipo_condicion_id} no es consecutivo")
                sys.exit(1)
            UdpTipoCondicion(nombre=nombre).save()
            contador += 1
    console.print(f"[green]{contador} udp_tipos_condiciones alimentados.")


def alimentar_udp_tipos_tramites():
    """Alimentar UDP Tipos Tramites"""
    console = Console()
    ruta = Path(UDP_TIPOS_TRAMITES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando udp_tipos_tramites...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_tipo_tramite_id = int(row["udp_tipo_tramite_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            if udp_tipo_tramite_id != contador + 1:
                console.print(f"[red]ERROR: udp_tipo_tramite_id {udp_tipo_tramite_id} no es consecutivo")
                sys.exit(1)
            UdpTipoTramite(nombre=nombre).save()
            contador += 1
    console.print(f"[green]{contador} udp_tipos_tramites alimentados.")


def alimentar_udp_tipos_visitas():
    """Alimentar UDP Tipos Visitas"""
    console = Console()
    ruta = Path(UDP_TIPOS_VISITAS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando udp_tipos_visitas...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_tipo_visita_id = int(row["udp_tipo_visita_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            if udp_tipo_visita_id != contador + 1:
                console.print(f"[red]ERROR: udp_tipo_visita_id {udp_tipo_visita_id} no es consecutivo")
                sys.exit(1)
            UdpTipoVisita(nombre=nombre).save()
            contador += 1
    console.print(f"[green]{contador} udp_tipos_visitas alimentados.")

def obtener_o_crear_udp_sexo(nombre: str) -> UdpSexo:
    """Obtener un UdpSexo por nombre, o crearlo si no existe"""
    nombre = safe_string(nombre, save_enie=True)
    udp_sexo = UdpSexo.query.filter_by(nombre=nombre).first()
    if udp_sexo is None:
        udp_sexo = UdpSexo(nombre=nombre).save()
    return udp_sexo


def obtener_o_crear_udp_tipo_condicion(nombre: str) -> UdpTipoCondicion:
    """Obtener un UdpTipoCondicion por nombre, o crearlo si no existe"""
    nombre = safe_string(nombre, save_enie=True)
    udp_tipo_condicion = UdpTipoCondicion.query.filter_by(nombre=nombre).first()
    if udp_tipo_condicion is None:
        udp_tipo_condicion = UdpTipoCondicion(nombre=nombre).save()
    return udp_tipo_condicion


def partir_nombre_completo(nombre_completo: str) -> tuple[str, str, str]:
    """Partir un nombre completo en (nombres, apellido_primero, apellido_segundo)

    Se asume la convención mexicana: nombre(s) de pila seguidos del apellido
    paterno y, opcionalmente, el apellido materno al final.
    """
    palabras = safe_string(nombre_completo, save_enie=True).split()
    if len(palabras) == 0:
        return "", "", ""
    if len(palabras) == 1:
        return palabras[0], "", ""
    if len(palabras) == 2:
        return palabras[0], palabras[1], ""
    *nombres_palabras, apellido_primero, apellido_segundo = palabras
    return " ".join(nombres_palabras), apellido_primero, apellido_segundo


def convertir_fecha(fecha_str: str) -> date | None:
    """Convertir una fecha con formato DD/MM/AAAA (con u sin hora) a un objeto date"""
    fecha_str = fecha_str.strip()
    if fecha_str == "":
        return None
    for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(fecha_str, formato).date()
        except ValueError:
            continue
    return None


def alimentar_udp_personas():
    """Alimentar UDP Personas"""
    console = Console()
    ruta = Path(UDP_PERSONAS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando udp_personas...")
    contador = 0
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_sexo = obtener_o_crear_udp_sexo(row["SEXO"])
            udp_sexo_contraparte = obtener_o_crear_udp_sexo('ND') 
            udp_tipo_condicion = obtener_o_crear_udp_tipo_condicion(row["CONDICIÓN"])
            udp_tipo_condicion_contraparte = obtener_o_crear_udp_tipo_condicion('NA')
            nombres, apellido_primero, apellido_segundo = partir_nombre_completo(row["NOMBRE_USUARIO"])
            udp_persona = obtener_o_crear_udp_persona(
                nombre_completo=row["NOMBRE_USUARIO"],
                udp_sexo=udp_sexo,
                udp_tipo_condicion=udp_tipo_condicion,
                nacimiento_fecha=convertir_fecha(row["FECH_NAC_USUARIO"]),
                
            )
            udp_persona_contraparte= obtener_o_crear_udp_persona(
                nombre_completo=row["NOMBRE_CONTRAPARTE"],
                udp_sexo=udp_sexo_contraparte,
                udp_tipo_condicion=udp_tipo_condicion_contraparte,
                nacimiento_fecha=convertir_fecha(row["FECH_NAC_CONTRAPARTE"]),
            )
            UdpIngreso(
                udp_persona=udp_persona,
                ocupacion=safe_string(row["OCUPACIÓN"]) if "OCUPACIÓN" in row else 'ND',
                ingresos=safe_int(row["INGRESOS"]) if "INGRESOS" in row else 0,
                observaciones=safe_string(row["OBSERVACIONES_INGRESO"], max_len=2048, save_enie=True, to_uppercase=False) if "OBSERVACIONES_INGRESO" in row else 'ND',
            ).save()
            UdpAtencion(
                udp_persona=udp_persona,
                contraparte_id=udp_persona_contraparte.id,
                udp_tipo_tramite=obtener_o_crear_udp_tipo_tramite(row["TRAMITE"]),
                expediente=safe_string(row["NO_EXPEDIENTE"]) if row["NO_EXPEDIENTE"] else "",
                observaciones=safe_string(row["OBSERVACIONES"], max_len=2048, save_enie=True, to_uppercase=False),
                fecha=convertir_fecha(row["FECHA"]),
                usuario=obtener_o_crear_usuario_por_nombre(row["ATENDIO"], autoridad=autoridad_nd),
                visita=convertir_fecha(row["VISITA"]) if row["VISITA"] else None,
                como_se_entero=row["COMO_SE_ENTERO"] if "COMO_SE_ENTERO" in row else None,
                atendio=row["ATENDIO"] if "ATENDIO" in row else None,
                hora_salida=convertir_fecha(row["HORA_SALIDA"]) if "HORA_SALIDA" in row else None,
                observaciones_aj= safe_string(row["OBSERVACIONES_AJ"], max_len=2040, save_enie=True, to_uppercase=False) if "OBSERVACIONES_AJ" in row else None,
                fecha_hora_aj=convertir_fecha(row["FECHA_HORA_AJ"]) if "FECHA_HORA_AJ" in row else None,
                canalizado=row["CANALIZADO"] if "CANALIZADO" in row else None,
                fecha_canalizado=convertir_fecha(row["FECHA_CANALIZADO"]) if "FECHA_CANALIZADO" in row else None,
            ).save()
            municipio_id=66
            UdpDomicilio(
                udp_persona=udp_persona,
                municipio_id=municipio_id,
                calle=safe_string(row["CALLE"]) if "CALLE" in row else '',
                num_exterior=safe_string(row["NUMERO_EXTERIOR"]) if "NUMERO_EXTERIOR" in row else '',
                num_interior=safe_string(row["NUMERO_INTERIOR"]) if "NUMERO_INTERIOR" in row else '',
                colonia=safe_string(row["COLONIA"]) if "COLONIA" in row else '',
                codigo_postal=safe_string(row["CODIGO_POSTAL"]) if "CODIGO_POSTAL" in row else 0,
                              
            ).save()
            contador += 1
        """ for row in rows:
            console.print(f"row ={row}") """
        
    console.print(f"[green]{contador} udp_personas alimentados.")


def obtener_o_crear_udp_tipo_tramite(nombre: str) -> UdpTipoTramite:
    """Obtener un UdpTipoTramite por nombre, o crearlo si no existe"""
    nombre = safe_string(nombre, save_enie=True)
    udp_tipo_tramite = UdpTipoTramite.query.filter_by(nombre=nombre).first()
    if udp_tipo_tramite is None:
        udp_tipo_tramite = UdpTipoTramite(nombre=nombre).save()
    return udp_tipo_tramite


def obtener_o_crear_udp_persona(nombre_completo: str, udp_sexo: UdpSexo, udp_tipo_condicion: UdpTipoCondicion, nacimiento_fecha) -> UdpPersona:
    """Obtener un UdpPersona por su nombre completo, o crearlo si no existe"""
    nombres, apellido_primero, apellido_segundo = partir_nombre_completo(nombre_completo)
    udp_persona = UdpPersona.query.filter_by(
        nombres=nombres,
        apellido_primero=apellido_primero,
        apellido_segundo=apellido_segundo,
    ).first()
    if udp_persona is None:
        udp_persona = UdpPersona(
            udp_sexo=udp_sexo,
            udp_tipo_condicion=udp_tipo_condicion,
            nombres=nombres,
            apellido_primero=apellido_primero,
            apellido_segundo=apellido_segundo,
            nacimiento_fecha=nacimiento_fecha,
        ).save()
    return udp_persona


def obtener_o_crear_usuario_por_nombre(nombre_completo: str, autoridad: Autoridad) -> Usuario:
    """Obtener un Usuario por su nombre completo, o crearlo con datos minimos si no existe"""
    nombre_completo = safe_string(nombre_completo, save_enie=True)
    usuario = Usuario.query.filter_by(nombres=nombre_completo).first()
    if usuario is None:
        usuario = Usuario(
            autoridad=autoridad,
            email=f"{safe_clave(nombre_completo, max_len=64, separator='-').lower()}@pjecz.gob.mx",
            nombres=nombre_completo,
            apellido_paterno="",
            apellido_materno="",
            curp="",
            puesto="",
            api_key="",
            api_key_expiracion=datetime(year=2000, month=1, day=1),
            contrasena=pwd_context.hash(generar_contrasena()),
        ).save()
    return usuario
def obtener_municipio(nombre: str) -> Municipio:
    """Obtener un Municipio por su nombre"""
    return Municipio.query.filter_by(nombre=nombre).first()

def alimentar_atenciones():
    """Alimentar UDP Personas Atenciones"""
    console = Console()
    ruta = Path(UDP_PERSONAS_ATENCIONES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()
    if autoridad_nd is None:
        console.print("[red]ERROR: No se encontró la autoridad 'ND'.")
        sys.exit(1)
    console.print("Alimentando atenciones ->...")
    contador = 0
    with open(ruta, encoding="cp1252") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            udp_sexo = obtener_o_crear_udp_sexo(row["SEXO"])
            udp_tipo_condicion = obtener_o_crear_udp_tipo_condicion(row["CONDICIÓN"])
            udp_persona = obtener_o_crear_udp_persona(
                row["NOMBRE_USUARIO"],
                udp_sexo,
                udp_tipo_condicion,
                convertir_fecha(row["FECH_NAC_USUARIO"]),
            )
            udp_tipo_tramite = obtener_o_crear_udp_tipo_tramite(row["TRAMITE"])
            usuario = obtener_o_crear_usuario_por_nombre(row["ATENDIO"], autoridad_nd)
            no_expediente = row["NO_EXPEDIENTE"].strip()
            anio_expediente = row["AÑO_EXPEDIENTE"].strip()
            expediente = f"{no_expediente}/{anio_expediente}" if no_expediente and anio_expediente else ""
            observaciones = safe_string(row["OBSERVACIONES"], max_len=2048, save_enie=True, to_uppercase=False)
            UdpAtencion(
                autoridad=autoridad_nd,
                udp_persona=udp_persona,
                udp_tipo_tramite=udp_tipo_tramite,
                usuario=usuario,
                expediente=expediente,
                observaciones=observaciones,
                fecha=convertir_fecha(row["FECHA"]),
                visita=convertir_fecha(row["VISITA"]) if row["VISITA"] else None,
                como_se_entero=row["COMO_SE_ENTERO"] if "COMO_SE_ENTERO" in row else None,
                atendio=row["ATENDIO"] if "ATENDIO" in row else None,
                hora_salida=convertir_fecha(row["HORA_SALIDA"]) if "HORA_SALIDA" in row else None,
                observaciones_aj= safe_string(row["OBSERVACIONES_AJ"], max_len=2048, save_enie=True, to_uppercase=False) if "OBSERVACIONES_AJ" in row else None,
                fecha_hora_aj=convertir_fecha(row["FECHA_HORA_AJ"]) if "FECHA_HORA_AJ" in row else None,
                canalizado=row["CANALIZADO"] if "CANALIZADO" in row else None,
                fecha_canalizado=convertir_fecha(row["FECHA_CANALIZADO"]) if "FECHA_CANALIZADO" in row else None,
            ).save()
            contador += 1
    console.print(f"[green]{contador} atenciones alimentadas.")

def alimentar_estados():
    """Alimentar Estados"""
    console = Console()
    ruta = Path(ESTADOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando estados...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            estado_id = int(row["estado_id"])
            clave = safe_string(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if estado_id != contador + 1:
                console.print(f"[red]ERROR: estado_id {estado_id} no es consecutivo")
                sys.exit(1)
            Estado(
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} estados alimentados.")


def alimentar_municipios():
    """Alimentar Municipios"""
    console = Console()
    ruta = Path(MUNICIPIOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando municipios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            municipio_id = int(row["municipio_id"])
            estado_id = int(row["estado_id"])
            estado = Estado.query.get(estado_id)
            if estado is None:
                console.print(f"[red]ERROR: estado_id {estado_id} no existe")
                sys.exit(1)
            clave = safe_string(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if municipio_id != contador + 1:
                console.print(f"[red]ERROR: municipio_id {municipio_id} no es consecutivo")
                sys.exit(1)
            Municipio(
                estado=estado,
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} municipios alimentados.")


def respaldar_autoridades():
    """Respaldar Autoridades"""
    console = Console()
    ruta = Path(AUTORIDADES_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {AUTORIDADES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando autoridades...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "autoridad_id",
                "distrito_id",
                "clave",
                "descripcion",
                "descripcion_corta",
                "estatus",
            ]
        )
        for autoridad in Autoridad.query.order_by(Autoridad.id).all():
            respaldo.writerow(
                [
                    autoridad.id,
                    autoridad.distrito_id,
                    autoridad.clave,
                    autoridad.descripcion,
                    autoridad.descripcion_corta,
                    autoridad.estatus,
                ]
            )
            contador += 1
    console.print(f"[green]{contador} autoridades respaldadas.")


def respaldar_distritos():
    """Respaldar Distritos"""
    console = Console()
    ruta = Path(DISTRITOS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {DISTRITOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando distritos...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "distrito_id",
                "clave",
                "nombre",
                "nombre_corto",
                "estatus",
            ]
        )
        for distrito in Distrito.query.order_by(Distrito.id).all():
            respaldo.writerow(
                [
                    distrito.id,
                    distrito.clave,
                    distrito.nombre,
                    distrito.nombre_corto,
                    distrito.estatus,
                ]
            )
            contador += 1
    console.print(f"[green]{contador} distritos respaldados.")


def respaldar_modulos():
    """Respaldar Modulos"""
    console = Console()
    ruta = Path(MODULOS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {MODULOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando modulos...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "modulo_id",
                "nombre",
                "nombre_corto",
                "icono",
                "ruta",
                "en_navegacion",
                "estatus",
            ]
        )
        for modulo in Modulo.query.order_by(Modulo.id).all():
            respaldo.writerow(
                [
                    modulo.id,
                    modulo.nombre,
                    modulo.nombre_corto,
                    modulo.icono,
                    modulo.ruta,
                    int(modulo.en_navegacion),
                    modulo.estatus,
                ]
            )
            contador += 1
    console.print(f"[green]{contador} modulos respaldados.")


def respaldar_roles_permisos():
    """Respaldar Roles-Permisos"""
    console = Console()
    ruta = Path(ROLES_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {ROLES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    modulos = Modulo.query.order_by(Modulo.id).all()
    console.print("Respaldando roles-permisos...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        encabezados = ["rol_id", "nombre"]
        for modulo in modulos:
            encabezados.append(modulo.nombre.lower())
        encabezados.append("estatus")
        respaldo = csv.writer(puntero)
        respaldo.writerow(encabezados)
        for rol in Rol.query.order_by(Rol.id).all():
            renglon = [rol.id, rol.nombre]
            for modulo in modulos:
                permiso_str = ""
                for permiso in rol.permisos:
                    if permiso.modulo_id == modulo.id and permiso.estatus == "A":
                        permiso_str = str(permiso.nivel)
                renglon.append(permiso_str)
            renglon.append(rol.estatus)
            respaldo.writerow(renglon)
            contador += 1
    console.print(f"[green]{contador} roles-permisos respaldados.")


def respaldar_usuarios_roles():
    """Respaldar Usuarios-Roles"""
    console = Console()
    ruta = Path(USUARIOS_ROLES_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {USUARIOS_ROLES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando usuarios-roles...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "usuario_id",
                "autoridad_clave",
                "email",
                "nombres",
                "apellido_paterno",
                "apellido_materno",
                "curp",
                "puesto",
                "roles",
                "estatus",
            ]
        )
        for usuario in Usuario.query.order_by(Usuario.id).all():
            roles_list = []
            for usuario_rol in usuario.usuarios_roles:
                if usuario_rol.estatus == "A":
                    roles_list.append(usuario_rol.rol.nombre)
            respaldo.writerow(
                [
                    usuario.id,
                    usuario.autoridad.clave,
                    usuario.email,
                    usuario.nombres,
                    usuario.apellido_paterno,
                    usuario.apellido_materno,
                    usuario.curp,
                    usuario.puesto,
                    ",".join(roles_list),
                    usuario.estatus,
                ]
            )
            contador += 1
    console.print(f"[green]{contador} usuarios-roles respaldados.")


def respaldar_udp_sexos():
    """Respaldar UDP Sexos"""
    console = Console()
    ruta = Path(UDP_SEXOS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {UDP_SEXOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando udp_sexos...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["udp_sexo_id", "nombre"])
        for udp_sexo in UdpSexo.query.order_by(UdpSexo.id).all():
            respaldo.writerow([udp_sexo.id, udp_sexo.nombre])
            contador += 1
    console.print(f"[green]{contador} udp_sexos respaldados.")


def respaldar_udp_tipos_condiciones():
    """Respaldar UDP Tipos Condiciones"""
    console = Console()
    ruta = Path(UDP_TIPOS_CONDICIONES_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {UDP_TIPOS_CONDICIONES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando udp_tipos_condiciones...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["udp_tipo_condicion_id", "nombre"])
        for udp_tipo_condicion in UdpTipoCondicion.query.order_by(UdpTipoCondicion.id).all():
            respaldo.writerow([udp_tipo_condicion.id, udp_tipo_condicion.nombre])
            contador += 1
    console.print(f"[green]{contador} udp_tipos_condiciones respaldados.")


def respaldar_udp_tipos_tramites():
    """Respaldar UDP Tipos Tramites"""
    console = Console()
    ruta = Path(UDP_TIPOS_TRAMITES_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {UDP_TIPOS_TRAMITES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando udp_tipos_tramites...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["udp_tipo_tramite_id", "nombre"])
        for udp_tipo_tramite in UdpTipoTramite.query.order_by(UdpTipoTramite.id).all():
            respaldo.writerow([udp_tipo_tramite.id, udp_tipo_tramite.nombre])
            contador += 1
    console.print(f"[green]{contador} udp_tipos_tramites respaldados.")


def respaldar_udp_tipos_visitas():
    """Respaldar UDP Tipos Visitas"""
    console = Console()
    ruta = Path(UDP_TIPOS_VISITAS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {UDP_TIPOS_VISITAS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando udp_tipos_visitas...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["udp_tipo_visita_id", "nombre"])
        for udp_tipo_visita in UdpTipoVisita.query.order_by(UdpTipoVisita.id).all():
            respaldo.writerow([udp_tipo_visita.id, udp_tipo_visita.nombre])
            contador += 1
    console.print(f"[green]{contador} udp_tipos_visitas respaldados.")


def respaldar_estados():
    """Respaldar Estados"""
    console = Console()
    ruta = Path(ESTADOS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {ESTADOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando estados...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["estado_id", "clave", "nombre", "estatus"])
        for estado in Estado.query.order_by(Estado.id).all():
            respaldo.writerow([estado.id, estado.clave, estado.nombre, estado.estatus])
            contador += 1
    console.print(f"[green]{contador} estados respaldados.")


def respaldar_municipios():
    """Respaldar Municipios"""
    console = Console()
    ruta = Path(MUNICIPIOS_CSV)
    if ruta.exists():
        console.print(f"[red]ERROR: {MUNICIPIOS_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    console.print("Respaldando municipios...")
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["municipio_id", "estado_id", "clave", "nombre", "estatus"])
        for municipio in Municipio.query.order_by(Municipio.id).all():
            respaldo.writerow([municipio.id, municipio.estado_id, municipio.clave, municipio.nombre, municipio.estatus])
            contador += 1
    console.print(f"[green]{contador} municipios respaldados.")


@db.command()
def inicializar():
    """Inicializar la base de datos"""
    console = Console()
    if DEPLOYMENT_ENVIRONMENT != "DEVELOPMENT":
        console.print(f"[red]PROHIBIDO: No se inicializa porque DEPLOYMENT_ENVIRONMENT es {DEPLOYMENT_ENVIRONMENT}.")
        sys.exit(1)
    # DROP CASCADE del esquema completo para eliminar tablas huérfanas que impiden borrar por dependencias
    database.session.execute(text("DROP SCHEMA public CASCADE"))
    database.session.execute(text("CREATE SCHEMA public"))
    database.session.commit()
    database.create_all()
    console.print("[green]La base de datos se ha inicializado correctamente.")


@db.command()
def alimentar():
    """Alimentar la base de datos con los datos en los archivos CSV en la carpeta 'seed'"""
    console = Console()
    if DEPLOYMENT_ENVIRONMENT == "PRODUCTION":
        console.print("[red]PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_modulos()
    alimentar_roles()
    alimentar_permisos()
    alimentar_estados()
    alimentar_municipios()
    alimentar_distritos()
    alimentar_autoridades()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    alimentar_udp_sexos()
    alimentar_udp_tipos_condiciones()
    alimentar_udp_tipos_tramites()
    alimentar_udp_tipos_visitas()
    alimentar_udp_personas()    
    #alimentar_atenciones()
    console.print("[green]La base de datos se ha alimentado correctamente.")

def eliminar_personas():
    """Eliminar todas las personas de la base de datos"""
    for persona in UdpPersona.query.all():
        database.session.delete(persona)
    database.session.commit()

@db.command()
def alimentar_personas():
    """Alimentar la base de datos con los datos de personas en el archivo CSV correspondiente"""
    #eliminar_personas()
    alimentar_udp_personas()
@db.command()
def reiniciar():
    """Reiniciar la base de datos (inicializar y alimentar)"""
    inicializar()
    alimentar()


@db.command()
def respaldar():
    """Respaldar la base de datos en archivos CSV"""
    respaldar_autoridades()
    respaldar_distritos()
    respaldar_estados()
    respaldar_modulos()
    respaldar_municipios()
    respaldar_roles_permisos()
    respaldar_usuarios_roles()
    respaldar_udp_sexos()
    respaldar_udp_tipos_condiciones()
    respaldar_udp_tipos_tramites()
    respaldar_udp_tipos_visitas()
    

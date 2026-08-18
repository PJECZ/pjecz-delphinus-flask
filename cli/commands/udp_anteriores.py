"""
CLI UDP Anteriores
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from typer import Typer

from pjecz_delphinus_flask.app import create_app
from pjecz_delphinus_flask.blueprints.autoridades.models import Autoridad
from pjecz_delphinus_flask.blueprints.municipios.models import Municipio
from pjecz_delphinus_flask.blueprints.udp_contrapartes.models import UdpContraparte
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.udp_sexos.models import UdpSexo
from pjecz_delphinus_flask.blueprints.udp_tipos_condiciones.models import UdpTipoCondicion
from pjecz_delphinus_flask.blueprints.udp_tipos_tramites.models import UdpTipoTramite
from pjecz_delphinus_flask.blueprints.udp_tipos_visitas.models import UdpTipoVisita
from pjecz_delphinus_flask.lib.safe_string import safe_string

# Rutas a los archivos CSV
UDP_PERSONAS_CSV = "seed/PERSONAS.csv"

# Inicializar la aplicación
app = create_app()
app.app_context().push()

udp_anteriores = Typer()


@udp_anteriores.command()
def insertar():
    """Insertar registros del sistema anterior"""
    console = Console()
    ruta = Path(UDP_PERSONAS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    # Inicializar listados
    udp_personas = []
    udp_contrapartes = []
    # Iniciar insertar
    console.print("Insertando...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # UdpPersona
            nombres = ""
            apellido_primero = ""
            apellido_segundo = ""
            nombre_completo = safe_string(str(row.get("NOMBRE_USUARIO")), save_enie=True)
            palabras = nombre_completo.split(" ")  # Separar por palabras
            if len(palabras) >= 3:
                nombres = " ".join(palabras[:-2])
                apellido_primero = palabras[-2]
                apellido_segundo = palabras[-1]
            observaciones = row.get("OBSERVACIONES")
            udp_persona = UdpPersona()
            udp_persona.nombres = nombres
            udp_persona.apellido_primero = apellido_primero
            udp_persona.apellido_segundo = apellido_segundo
            udp_persona.observaciones = observaciones
            udp_personas.append(udp_persona)
            # UdpContraparte
            nombres = ""
            apellido_primero = ""
            apellido_segundo = ""
            nombre_completo = safe_string(str(row.get("NOMBRE_CONTRAPARTE")), save_enie=True)
            palabras = nombre_completo.split(" ")  # Separar por palabras
            if len(palabras) >= 3:
                nombres = " ".join(palabras[:-2])
                apellido_primero = palabras[-2]
                apellido_segundo = palabras[-1]
            udp_contraparte = UdpContraparte()
            udp_contraparte.nombres = nombres
            udp_contraparte.apellido_primero = apellido_primero
            udp_contraparte.apellido_segundo = apellido_segundo
            udp_contrapartes.append(udp_contraparte)
            # Incrementar contador
            contador += 1
            if contador >= 10:
                break
    # Mostrar tabla
    tabla = Table(title="udp_personas")
    tabla.add_column("Nombres")
    tabla.add_column("Apellido primero")
    tabla.add_column("Apellido segundo")
    tabla.add_column("Observaciones")
    for udp_persona in udp_personas:
        tabla.add_row(
            udp_persona.nombres,
            udp_persona.apellido_primero,
            udp_persona.apellido_segundo,
            udp_persona.observaciones,
        )
    console.print(tabla)
    # Mostrar tabla
    tabla = Table(title="udp_contrapartes")
    tabla.add_column("Nombres")
    tabla.add_column("Apellido primero")
    tabla.add_column("Apellido segundo")
    for udp_contraparte in udp_contrapartes:
        tabla.add_row(
            udp_contraparte.nombres,
            udp_contraparte.apellido_primero,
            udp_contraparte.apellido_segundo,
        )
    console.print(tabla)


"""
Columnas del archivo UDP_PERSONAS_CSV:
- ID
- NOMBRE_USUARIO
- FECHA
- NO_EXPEDIENTE
- FECH_NAC_USUARIO
- EDAD
- SEXO
- CONDICIÓN
- NOMBRE_CONTRAPARTE
- FECH_NAC_CONTRAPARTE
- OCUPACIÓN
- INGRESOS
- COLONIA
- TELEFONO
- TRAMITE
- VISITA
- COMO_SE_ENTERO
- OBSERVACIONES
- ATENDIO
- HORA_SALIDA
- ASIGNADO_A
- HORA_SALIDA_AJ
- OBSERVACIONES_AJ
- AÑO_EXPEDIENTE
- FECHA_HORA_EAJ
- CANALIZADO
- FECHA_CANALIZADO
"""

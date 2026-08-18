"""
CLI UDP Atenciones Contrapartes
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from typer import Typer

from pjecz_delphinus_flask.app import create_app

# Rutas a los archivos CSV
UDP_PERSONAS_CSV = "seed/PERSONAS.csv"

# Inicializar la aplicación
app = create_app()
app.app_context().push()

udp_atenciones_contrapartes = Typer()


@udp_atenciones_contrapartes.command()
def migrar():
    """Migrar las atenciones-contrapartes del sistema anterior"""
    console = Console()
    ruta = Path(UDP_PERSONAS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando atenciones-contrapartes...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)

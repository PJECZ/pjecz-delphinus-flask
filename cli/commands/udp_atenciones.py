"""
CLI UDP Atenciones
"""

from rich.console import Console
from typer import Typer

from pjecz_delphinus_flask.app import create_app

# Inicializar la aplicación
app = create_app()
app.app_context().push()

udp_atenciones = Typer()


@udp_atenciones.command()
def mostrar():
    """Mostrar las atenciones"""
    console = Console()
    console.print("Mostrando las atenciones...")

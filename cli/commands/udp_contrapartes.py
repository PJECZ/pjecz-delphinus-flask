"""
CLI UDP Contrapartes
"""

from rich.console import Console
from typer import Typer

from pjecz_delphinus_flask.app import create_app

# Inicializar la aplicación
app = create_app()
app.app_context().push()

udp_contrapartes = Typer()


@udp_contrapartes.command()
def mostrar():
    """Mostrar las contrapartes"""
    console = Console()
    console.print("Mostrando las contrapartes...")

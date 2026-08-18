"""
CLI UDP Personas
"""

from rich.console import Console
from typer import Typer

from pjecz_delphinus_flask.app import create_app

# Inicializar la aplicación
app = create_app()
app.app_context().push()

udp_personas = Typer()


@udp_personas.command()
def mostrar():
    """Mostrar las personas"""
    console = Console()
    console.print("Mostrando las personas...")

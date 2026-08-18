"""
PJECZ Delphinus Flask CLI
"""

from typer import Typer

from cli.commands.db import db
from cli.commands.udp_atenciones import udp_atenciones
from cli.commands.udp_atenciones_contrapartes import udp_atenciones_contrapartes
from cli.commands.udp_contrapartes import udp_contrapartes
from cli.commands.udp_personas import udp_personas
from cli.commands.usuarios import usuarios

cli = Typer()
cli.add_typer(db, name="db")
cli.add_typer(udp_atenciones, name="udp_atenciones")
cli.add_typer(udp_atenciones_contrapartes, name="udp_atenciones_contrapartes")
cli.add_typer(udp_contrapartes, name="udp_contrapartes")
cli.add_typer(udp_personas, name="udp_personas")
cli.add_typer(usuarios, name="usuarios")

if __name__ == "__main__":
    cli()

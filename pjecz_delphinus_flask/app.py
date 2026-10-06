"""
PJECZ Delphinus Flask Application
"""

from flask import Flask

from pjecz_delphinus_flask.blueprints.autoridades.views import autoridades
from pjecz_delphinus_flask.blueprints.bitacoras.views import bitacoras
from pjecz_delphinus_flask.blueprints.distritos.views import distritos
from pjecz_delphinus_flask.blueprints.entradas_salidas.views import entradas_salidas
from pjecz_delphinus_flask.blueprints.estados.views import estados
from pjecz_delphinus_flask.blueprints.modulos.views import modulos
from pjecz_delphinus_flask.blueprints.municipios.views import municipios
from pjecz_delphinus_flask.blueprints.permisos.views import permisos
from pjecz_delphinus_flask.blueprints.roles.views import roles
from pjecz_delphinus_flask.blueprints.sistemas.views import sistemas
from pjecz_delphinus_flask.blueprints.tareas.views import tareas
from pjecz_delphinus_flask.blueprints.udp_atenciones.views import udp_atenciones
from pjecz_delphinus_flask.blueprints.udp_atenciones_contrapartes.views import udp_atenciones_contrapartes
from pjecz_delphinus_flask.blueprints.udp_contrapartes.views import udp_contrapartes
from pjecz_delphinus_flask.blueprints.udp_cubiculos.models import UdpCubiculo  # noqa: F401
from pjecz_delphinus_flask.blueprints.udp_cubiculos.views import udp_cubiculos
from pjecz_delphinus_flask.blueprints.udp_domicilios.views import udp_domicilios
from pjecz_delphinus_flask.blueprints.udp_ingresos.views import udp_ingresos
from pjecz_delphinus_flask.blueprints.udp_personas.views import udp_personas
from pjecz_delphinus_flask.blueprints.udp_sexos.views import udp_sexos
from pjecz_delphinus_flask.blueprints.udp_tipos_condiciones.views import udp_tipos_condiciones
from pjecz_delphinus_flask.blueprints.udp_tipos_tramites.views import udp_tipos_tramites
from pjecz_delphinus_flask.blueprints.udp_tipos_visitas.views import udp_tipos_visitas
from pjecz_delphinus_flask.blueprints.udp_visitas.views import udp_visitas
from pjecz_delphinus_flask.blueprints.usuarios.models import Usuario
from pjecz_delphinus_flask.blueprints.usuarios.views import usuarios
from pjecz_delphinus_flask.blueprints.usuarios_roles.views import usuarios_roles
from pjecz_delphinus_flask.config.extensions import authentication, csrf, database, login_manager, moment
from pjecz_delphinus_flask.config.settings import Settings


def create_app():
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)
    app.add_url_rule("/favicon.ico", endpoint="sistemas.favicon")
    app.config.from_object(Settings())

    # Registrar blueprints
    app.register_blueprint(autoridades)
    app.register_blueprint(bitacoras)
    app.register_blueprint(distritos)
    app.register_blueprint(entradas_salidas)
    app.register_blueprint(estados)
    app.register_blueprint(modulos)
    app.register_blueprint(municipios)
    app.register_blueprint(permisos)
    app.register_blueprint(roles)
    app.register_blueprint(sistemas)
    app.register_blueprint(tareas)
    app.register_blueprint(usuarios)
    app.register_blueprint(usuarios_roles)
    app.register_blueprint(udp_atenciones)
    app.register_blueprint(udp_atenciones_contrapartes)
    app.register_blueprint(udp_contrapartes)
    app.register_blueprint(udp_cubiculos)
    app.register_blueprint(udp_domicilios)
    app.register_blueprint(udp_ingresos)
    app.register_blueprint(udp_personas)
    app.register_blueprint(udp_sexos)
    app.register_blueprint(udp_tipos_condiciones)
    app.register_blueprint(udp_tipos_tramites)
    app.register_blueprint(udp_tipos_visitas)
    app.register_blueprint(udp_visitas)

    # Inicializar extensiones
    csrf.init_app(app)
    database.init_app(app)
    login_manager.init_app(app)
    moment.init_app(app)

    # Cargar el modelo de usuario para la autenticación
    authentication(Usuario)

    return app

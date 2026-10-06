"""
UDP Cubículos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class UdpCubiculoForm(FlaskForm):
    """Formulario UdpCubiculo"""

    nombre = StringField("Nombre del cubículo", validators=[DataRequired(), Length(max=64)])
    guardar = SubmitField("Guardar")

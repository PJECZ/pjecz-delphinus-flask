"""
UDP Atenciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from pjecz_delphinus_flask.lib.safe_string import EXPEDIENTE_REGEXP


class UdpAtencionForm(FlaskForm):
    """Formulario UdpAtencion"""

    udp_tipo_tramite = SelectField("Tipo de Trámite", validators=[DataRequired()], choices=None, validate_choice=False)
    distrito = SelectField("Distrito", validators=[DataRequired()], choices=None, validate_choice=False)
    autoridad = SelectField("Autoridad", validators=[DataRequired()], choices=None, validate_choice=False)
    defensor = SelectField("Defensor", validators=[DataRequired()], choices=None, validate_choice=False)
    visita = SelectField("Visita", validators=[Optional()], choices=None, validate_choice=False)
    expediente = StringField("Expediente", validators=[Optional(), Regexp(EXPEDIENTE_REGEXP)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    guardar = SubmitField("Guardar")

"""
UDP Atenciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from pjecz_delphinus_flask.lib.safe_string import EXPEDIENTE_REGEXP


class UdpAtencionForm(FlaskForm):
    """Formulario UdpAtencion"""

    udp_tipo_tramite = SelectField("Tipo de Trámite", validators=[DataRequired()], choices=None, validate_choice=False)
    distrito = SelectField("Distrito", validators=[DataRequired()], choices=None, validate_choice=False)
    autoridad = SelectField("Autoridad", validators=[DataRequired()], choices=None, validate_choice=False)
    defensor = SelectField("Defensor", validators=[DataRequired()], choices=None, validate_choice=False)
    visita = SelectField("Visita", validators=[Optional()], choices=None, validate_choice=False)
    udp_contraparte = SelectField("Contraparte", validators=[Optional()], choices=None, validate_choice=False)
    nueva_contraparte = BooleanField("Registrar nueva contraparte")
    contraparte_nombres = StringField("Nombres", validators=[Optional(), Length(max=256)])
    contraparte_apellido_primero = StringField("Apellido Primero", validators=[Optional(), Length(max=256)])
    contraparte_apellido_segundo = StringField("Apellido Segundo", validators=[Optional(), Length(max=256)])
    contraparte_nacimiento_fecha = DateField("Fecha de Nacimiento", validators=[Optional()])
    contraparte_udp_sexo = SelectField("Sexo", validators=[Optional()], choices=None, validate_choice=False)
    contraparte_udp_tipo_condicion = SelectField("Tipo de Condición", validators=[Optional()], choices=None, validate_choice=False)
    contraparte_curp = StringField("CURP", validators=[Optional(), Length(max=18)])
    contraparte_observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    expediente = StringField("Expediente", validators=[Optional(), Regexp(EXPEDIENTE_REGEXP)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    guardar = SubmitField("Guardar")

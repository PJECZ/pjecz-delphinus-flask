"""
UDP Atenciones, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_atenciones.forms import UdpAtencionForm
from pjecz_delphinus_flask.blueprints.udp_atenciones.models import UdpAtencion
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP ATENCIONES"

udp_atenciones = Blueprint("udp_atenciones", __name__, template_folder="templates")


@udp_atenciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@udp_atenciones.route("/udp_atenciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Atenciones"""
    draw, start, rows_per_page = get_datatable_parameters()
    consulta = UdpAtencion.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "udp_persona_id" in request.form:
        consulta = consulta.filter(UdpAtencion.udp_persona_id == request.form["udp_persona_id"])
    registros = consulta.order_by(UdpAtencion.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                    "url": url_for("udp_atenciones.detail", udp_atencion_id=resultado.id),
                },
                "udp_tipo_tramite_nombre": resultado.udp_tipo_tramite.nombre,
                "usuario_email": resultado.usuario.email,
                "autoridad_clave": resultado.autoridad.clave if resultado.autoridad and resultado.autoridad.clave else "",
                "expediente": resultado.expediente or "",
            }
        )
    return output_datatable_json(draw, total, data)


@udp_atenciones.route("/udp_atenciones")
def list_active():
    """Listado de Atenciones activas"""
    return render_template(
        "udp_atenciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Atenciones",
        estatus="A",
    )


@udp_atenciones.route("/udp_atenciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Atenciones inactivas"""
    return render_template(
        "udp_atenciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Atenciones eliminadas",
        estatus="B",
    )


@udp_atenciones.route("/udp_atenciones/<int:udp_atencion_id>")
def detail(udp_atencion_id):
    """Detalle de una Atención"""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    return render_template("udp_atenciones/detail.jinja2", udp_atencion=udp_atencion)


@udp_atenciones.route("/udp_atenciones/nuevo/<int:udp_persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(udp_persona_id):
    """Nueva Atención"""
    udp_persona = UdpPersona.query.get_or_404(udp_persona_id)
    form = UdpAtencionForm()
    if form.validate_on_submit():
        udp_atencion = UdpAtencion(
            udp_persona_id=udp_persona.id,
            udp_tipo_tramite_id=form.udp_tipo_tramite.data,
            usuario_id=form.defensor.data,
            autoridad_id=form.autoridad.data,
            visita=form.visita.data,
            expediente=form.expediente.data,
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        udp_atencion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva atención para {udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Si el usuario actual tiene rol DEFENSOR, pasar su id como defensor por defecto
    defensor_id = None
    if "DEFENSOR" in current_user.get_roles():
        defensor_id = current_user.id
    return render_template(
        "udp_atenciones/new.jinja2",
        form=form,
        udp_persona=udp_persona,
        distrito_por_defecto=current_user.autoridad.distrito,
        autoridad_por_defecto=current_user.autoridad,
        defensor_id=defensor_id,
    )


@udp_atenciones.route("/udp_atenciones/edicion/<int:udp_atencion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(udp_atencion_id):
    """Editar Atención"""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    form = UdpAtencionForm()
    if form.validate_on_submit():
        udp_atencion.udp_tipo_tramite_id = form.udp_tipo_tramite.data
        udp_atencion.autoridad_id = form.autoridad.data
        udp_atencion.usuario_id = form.defensor.data
        udp_atencion.visita = form.visita.data
        udp_atencion.expediente = form.expediente.data
        udp_atencion.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
        udp_atencion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada atención de {udp_atencion.udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_atencion.udp_persona_id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.udp_tipo_tramite.data = udp_atencion.udp_tipo_tramite_id
    form.autoridad.data = udp_atencion.autoridad_id
    form.defensor.data = udp_atencion.usuario_id
    form.visita.data = udp_atencion.visita
    form.expediente.data = udp_atencion.expediente
    form.observaciones.data = udp_atencion.observaciones
    return render_template("udp_atenciones/edit.jinja2", form=form, udp_atencion=udp_atencion)


@udp_atenciones.route("/udp_atenciones/eliminar/<int:udp_atencion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(udp_atencion_id):
    """Eliminar Atención"""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    if udp_atencion.estatus == "A":
        udp_atencion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada atención de {udp_atencion.udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_atencion.udp_persona_id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_personas.detail", udp_persona_id=udp_atencion.udp_persona_id))


@udp_atenciones.route("/udp_atenciones/recuperar/<int:udp_atencion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(udp_atencion_id):
    """Recuperar Atención"""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    if udp_atencion.estatus == "B":
        udp_atencion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada atención de {udp_atencion.udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_atencion.udp_persona_id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_personas.detail", udp_persona_id=udp_atencion.udp_persona_id))

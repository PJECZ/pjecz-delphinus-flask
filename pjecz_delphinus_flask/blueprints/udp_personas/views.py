"""
UDP Personas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_contrapartes.models import UdpContraparte
from pjecz_delphinus_flask.blueprints.udp_personas.forms import UdpPersonaForm
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP PERSONAS"

udp_personas = Blueprint("udp_personas", __name__, template_folder="templates")


@udp_personas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@udp_personas.route("/udp_personas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Personas"""
    draw, start, rows_per_page = get_datatable_parameters()
    consulta = UdpPersona.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(UdpPersona.nombres.contains(nombres))
    if "apellido_primero" in request.form:
        apellido_primero = safe_string(request.form["apellido_primero"], save_enie=True)
        if apellido_primero != "":
            consulta = consulta.filter(UdpPersona.apellido_primero.contains(apellido_primero))
    if "apellido_segundo" in request.form:
        apellido_segundo = safe_string(request.form["apellido_segundo"], save_enie=True)
        if apellido_segundo != "":
            consulta = consulta.filter(UdpPersona.apellido_segundo.contains(apellido_segundo))
    if "curp" in request.form:
        curp = safe_string(request.form["curp"])
        if curp != "":
            consulta = consulta.filter(UdpPersona.curp.contains(curp))
    registros = (
        consulta.order_by(UdpPersona.apellido_primero, UdpPersona.apellido_segundo, UdpPersona.nombres)
        .offset(start)
        .limit(rows_per_page)
        .all()
    )
    total = consulta.count()
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre_completo": resultado.nombre_completo,
                    "url": url_for("udp_personas.detail", udp_persona_id=resultado.id),
                },
                "curp": resultado.curp or "",
                "nacimiento_fecha": resultado.nacimiento_fecha.strftime("%Y-%m-%d") if resultado.nacimiento_fecha else "",
                "udp_sexo_nombre": resultado.udp_sexo.nombre,
            }
        )
    return output_datatable_json(draw, total, data)


@udp_personas.route("/udp_personas")
def list_active():
    """Listado de Personas activas"""
    return render_template(
        "udp_personas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Personas",
        estatus="A",
    )


@udp_personas.route("/udp_personas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Personas inactivas"""
    return render_template(
        "udp_personas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Personas eliminadas",
        estatus="B",
    )


@udp_personas.route("/udp_personas/<int:udp_persona_id>")
def detail(udp_persona_id):
    """Detalle de una Persona"""
    udp_persona = UdpPersona.query.get_or_404(udp_persona_id)
    # Buscar contrapartes activas que coincidan por (nombres y apellido_primero), CURP o fecha de nacimiento
    condiciones = [
        (UdpContraparte.nombres == udp_persona.nombres) & (UdpContraparte.apellido_primero == udp_persona.apellido_primero)
    ]
    if udp_persona.curp:
        condiciones.append(UdpContraparte.curp == udp_persona.curp)
    if udp_persona.nacimiento_fecha:
        condiciones.append(UdpContraparte.nacimiento_fecha == udp_persona.nacimiento_fecha)
    posibles_contrapartes = (
        UdpContraparte.query.filter(UdpContraparte.estatus == "A")
        .filter(or_(*condiciones))
        .order_by(UdpContraparte.apellido_primero, UdpContraparte.apellido_segundo, UdpContraparte.nombres)
        .all()
    )
    return render_template("udp_personas/detail.jinja2", udp_persona=udp_persona, posibles_contrapartes=posibles_contrapartes)


@udp_personas.route("/udp_personas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Persona"""
    form = UdpPersonaForm()
    if form.validate_on_submit():
        es_valido = True
        nombres = safe_string(form.nombres.data, save_enie=True)
        apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
        apellido_segundo = safe_string(form.apellido_segundo.data, save_enie=True)
        curp = safe_string(form.curp.data)
        nacimiento_fecha = form.nacimiento_fecha.data
        # Verificar posible duplicado por nacimiento_fecha
        if nacimiento_fecha:
            posible_duplicado = UdpPersona.query.filter(
                UdpPersona.nombres == nombres,
                UdpPersona.apellido_primero == apellido_primero,
                UdpPersona.estatus == "A",
            ).first()
            if posible_duplicado:
                flash(f"Posible duplicado: {posible_duplicado.nombre_completo}. Verifique.", "warning")
        # Verificar posible duplicado por nombres y apellido_primero
        posible_duplicado_nombre = UdpPersona.query.filter(
            UdpPersona.nombres == nombres,
            UdpPersona.apellido_primero == apellido_primero,
            UdpPersona.estatus == "A",
        ).first()
        if posible_duplicado_nombre:
            flash(
                f"Ya existe una persona con el mismo nombre: {posible_duplicado_nombre.nombre_completo}. Verifique.", "warning"
            )
        if es_valido:
            udp_persona = UdpPersona(
                udp_sexo_id=form.udp_sexo.data,
                udp_tipo_condicion_id=form.udp_tipo_condicion.data,
                nombres=nombres,
                apellido_primero=apellido_primero,
                apellido_segundo=apellido_segundo,
                curp=curp,
                nacimiento_fecha=nacimiento_fecha,
                observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
            )
            udp_persona.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo UDP Persona {udp_persona.nombre_completo}"),
                url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("udp_personas/new.jinja2", form=form)


@udp_personas.route("/udp_personas/edicion/<int:udp_persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(udp_persona_id):
    """Editar Persona"""
    udp_persona = UdpPersona.query.get_or_404(udp_persona_id)
    form = UdpPersonaForm()
    if form.validate_on_submit():
        es_valido = True
        nombres = safe_string(form.nombres.data, save_enie=True)
        apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
        apellido_segundo = safe_string(form.apellido_segundo.data, save_enie=True)
        curp = safe_string(form.curp.data)
        nacimiento_fecha = form.nacimiento_fecha.data
        if es_valido:
            udp_persona.udp_sexo_id = form.udp_sexo.data
            udp_persona.udp_tipo_condicion_id = form.udp_tipo_condicion.data
            udp_persona.nombres = nombres
            udp_persona.apellido_primero = apellido_primero
            udp_persona.apellido_segundo = apellido_segundo
            udp_persona.curp = curp
            udp_persona.nacimiento_fecha = nacimiento_fecha
            udp_persona.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
            udp_persona.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado UDP Persona {udp_persona.nombre_completo}"),
                url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.udp_sexo.data = udp_persona.udp_sexo_id
    form.udp_tipo_condicion.data = udp_persona.udp_tipo_condicion_id
    form.nombres.data = udp_persona.nombres
    form.apellido_primero.data = udp_persona.apellido_primero
    form.apellido_segundo.data = udp_persona.apellido_segundo
    form.curp.data = udp_persona.curp
    form.nacimiento_fecha.data = udp_persona.nacimiento_fecha
    form.observaciones.data = udp_persona.observaciones
    return render_template("udp_personas/edit.jinja2", form=form, udp_persona=udp_persona)


@udp_personas.route("/udp_personas/eliminar/<int:udp_persona_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(udp_persona_id):
    """Eliminar Persona"""
    udp_persona = UdpPersona.query.get_or_404(udp_persona_id)
    if udp_persona.estatus == "A":
        udp_persona.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado UDP Persona {udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_personas.detail", udp_persona_id=udp_persona.id))


@udp_personas.route("/udp_personas/recuperar/<int:udp_persona_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(udp_persona_id):
    """Recuperar Persona"""
    udp_persona = UdpPersona.query.get_or_404(udp_persona_id)
    if udp_persona.estatus == "B":
        udp_persona.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado UDP Persona {udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_personas.detail", udp_persona_id=udp_persona.id))

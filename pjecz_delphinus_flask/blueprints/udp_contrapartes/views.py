"""
UDP Contrapartes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_contrapartes.forms import UdpContraparteForm
from pjecz_delphinus_flask.blueprints.udp_contrapartes.models import UdpContraparte
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP CONTRAPARTES"

udp_contrapartes = Blueprint("udp_contrapartes", __name__, template_folder="templates")


@udp_contrapartes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@udp_contrapartes.route("/udp_contrapartes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Contrapartes"""
    draw, start, rows_per_page = get_datatable_parameters()
    consulta = UdpContraparte.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(UdpContraparte.nombres.contains(nombres))
    if "apellido_primero" in request.form:
        apellido_primero = safe_string(request.form["apellido_primero"], save_enie=True)
        if apellido_primero != "":
            consulta = consulta.filter(UdpContraparte.apellido_primero.contains(apellido_primero))
    if "apellido_segundo" in request.form:
        apellido_segundo = safe_string(request.form["apellido_segundo"], save_enie=True)
        if apellido_segundo != "":
            consulta = consulta.filter(UdpContraparte.apellido_segundo.contains(apellido_segundo))
    if "curp" in request.form:
        curp = safe_string(request.form["curp"])
        if curp != "":
            consulta = consulta.filter(UdpContraparte.curp.contains(curp))
    registros = (
        consulta.order_by(UdpContraparte.apellido_primero, UdpContraparte.apellido_segundo, UdpContraparte.nombres)
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
                    "url": url_for("udp_contrapartes.detail", udp_contraparte_id=resultado.id),
                },
                "curp": resultado.curp or "",
                "nacimiento_fecha": resultado.nacimiento_fecha.strftime("%Y-%m-%d") if resultado.nacimiento_fecha else "",
                "udp_sexo_nombre": resultado.udp_sexo.nombre,
            }
        )
    return output_datatable_json(draw, total, data)


@udp_contrapartes.route("/udp_contrapartes")
def list_active():
    """Listado de Contrapartes activas"""
    return render_template(
        "udp_contrapartes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Contrapartes",
        estatus="A",
    )


@udp_contrapartes.route("/udp_contrapartes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Contrapartes inactivas"""
    return render_template(
        "udp_contrapartes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Contrapartes eliminadas",
        estatus="B",
    )


@udp_contrapartes.route("/udp_contrapartes/<int:udp_contraparte_id>")
def detail(udp_contraparte_id):
    """Detalle de una Contraparte"""
    udp_contraparte = UdpContraparte.query.get_or_404(udp_contraparte_id)
    # Buscar personas activas que coincidan por (nombres y apellido_primero), CURP o fecha de nacimiento
    condiciones = [
        (UdpPersona.nombres == udp_contraparte.nombres) & (UdpPersona.apellido_primero == udp_contraparte.apellido_primero)
    ]
    if udp_contraparte.curp:
        condiciones.append(UdpPersona.curp == udp_contraparte.curp)
    if udp_contraparte.nacimiento_fecha:
        condiciones.append(UdpPersona.nacimiento_fecha == udp_contraparte.nacimiento_fecha)
    posibles_personas = (
        UdpPersona.query.filter(UdpPersona.estatus == "A")
        .filter(or_(*condiciones))
        .order_by(UdpPersona.apellido_primero, UdpPersona.apellido_segundo, UdpPersona.nombres)
        .all()
    )
    return render_template(
        "udp_contrapartes/detail.jinja2", udp_contraparte=udp_contraparte, posibles_personas=posibles_personas
    )


@udp_contrapartes.route("/udp_contrapartes/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Contraparte"""
    form = UdpContraparteForm()
    if form.validate_on_submit():
        nombres = safe_string(form.nombres.data, save_enie=True)
        apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
        curp = safe_string(form.curp.data)
        # Verificar CURP duplicado si tiene valor
        if curp:
            posible_duplicado = UdpContraparte.query.filter(UdpContraparte.curp == curp, UdpContraparte.estatus == "A").first()
            if posible_duplicado:
                flash(f"Ya existe una contraparte con CURP {curp}: {posible_duplicado.nombre_completo}. Verifique.", "warning")
        udp_contraparte = UdpContraparte(
            nombres=nombres,
            apellido_primero=apellido_primero,
            apellido_segundo=safe_string(form.apellido_segundo.data, save_enie=True),
            nacimiento_fecha=form.nacimiento_fecha.data,
            udp_sexo_id=form.udp_sexo.data,
            curp=curp,
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        udp_contraparte.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva contraparte {udp_contraparte.nombre_completo}"),
            url=url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("udp_contrapartes/new.jinja2", form=form)


@udp_contrapartes.route("/udp_contrapartes/edicion/<int:udp_contraparte_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(udp_contraparte_id):
    """Editar Contraparte"""
    udp_contraparte = UdpContraparte.query.get_or_404(udp_contraparte_id)
    form = UdpContraparteForm()
    if form.validate_on_submit():
        udp_contraparte.nombres = safe_string(form.nombres.data, save_enie=True)
        udp_contraparte.apellido_primero = safe_string(form.apellido_primero.data, save_enie=True)
        udp_contraparte.apellido_segundo = safe_string(form.apellido_segundo.data, save_enie=True)
        udp_contraparte.nacimiento_fecha = form.nacimiento_fecha.data
        udp_contraparte.udp_sexo_id = form.udp_sexo.data
        udp_contraparte.curp = safe_string(form.curp.data)
        udp_contraparte.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
        udp_contraparte.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada contraparte {udp_contraparte.nombre_completo}"),
            url=url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.nombres.data = udp_contraparte.nombres
    form.apellido_primero.data = udp_contraparte.apellido_primero
    form.apellido_segundo.data = udp_contraparte.apellido_segundo
    form.nacimiento_fecha.data = udp_contraparte.nacimiento_fecha
    form.udp_sexo.data = udp_contraparte.udp_sexo_id
    form.curp.data = udp_contraparte.curp
    form.observaciones.data = udp_contraparte.observaciones
    return render_template("udp_contrapartes/edit.jinja2", form=form, udp_contraparte=udp_contraparte)


@udp_contrapartes.route("/udp_contrapartes/eliminar/<int:udp_contraparte_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(udp_contraparte_id):
    """Eliminar Contraparte"""
    udp_contraparte = UdpContraparte.query.get_or_404(udp_contraparte_id)
    if udp_contraparte.estatus == "A":
        udp_contraparte.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada contraparte {udp_contraparte.nombre_completo}"),
            url=url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id))


@udp_contrapartes.route("/udp_contrapartes/recuperar/<int:udp_contraparte_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(udp_contraparte_id):
    """Recuperar Contraparte"""
    udp_contraparte = UdpContraparte.query.get_or_404(udp_contraparte_id)
    if udp_contraparte.estatus == "B":
        udp_contraparte.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada contraparte {udp_contraparte.nombre_completo}"),
            url=url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_contrapartes.detail", udp_contraparte_id=udp_contraparte.id))


@udp_contrapartes.route("/udp_contrapartes/select_json", methods=["GET", "POST"])
def select_json():
    """Proporcionar el JSON con los ids, nombres completos - CURP para elegir con un select"""
    consulta = UdpContraparte.query.filter_by(estatus="A")
    if "searchTerm" in request.args:
        search_term = safe_string(request.args.get("searchTerm", ""), save_enie=True)
        if len(search_term) >= 4:
            consulta = consulta.filter(
                UdpContraparte.curp.contains(search_term)
                | UdpContraparte.nombres.contains(search_term)
                | UdpContraparte.apellido_primero.contains(search_term)
                | UdpContraparte.apellido_segundo.contains(search_term)
            )
    consulta = consulta.order_by(UdpContraparte.apellido_primero, UdpContraparte.apellido_segundo, UdpContraparte.nombres)
    resultados = [{"id": c.id, "text": f"{c.nombre_completo} — {c.curp or 'Sin CURP'}"} for c in consulta.all()]
    return {"results": resultados, "pagination": {"more": False}}

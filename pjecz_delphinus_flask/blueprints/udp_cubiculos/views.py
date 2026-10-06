"""
UDP Cubículos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_cubiculos.forms import UdpCubiculoForm
from pjecz_delphinus_flask.blueprints.udp_cubiculos.models import UdpCubiculo
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.config.extensions import database
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP CUBICULOS"

udp_cubiculos = Blueprint("udp_cubiculos", __name__, template_folder="templates")


@udp_cubiculos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@udp_cubiculos.route("/udp_cubiculos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Cubículos"""
    draw, start, rows_per_page = get_datatable_parameters()
    consulta = UdpCubiculo.query
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], max_len=64)
        if nombre:
            consulta = consulta.filter(UdpCubiculo.nombre.contains(nombre))
    registros = consulta.order_by(UdpCubiculo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    data = [
        {
            "id": resultado.id,
            "detalle": {
                "nombre": resultado.nombre,
                "url": url_for("udp_cubiculos.detail", cubiculo_id=resultado.id),
            },
            "acciones": {
                "detalle_url": url_for("udp_cubiculos.detail", cubiculo_id=resultado.id),
                "editar_url": (
                    url_for("udp_cubiculos.edit", cubiculo_id=resultado.id)
                    if resultado.estatus == "A" and current_user.can_edit(MODULO)
                    else ""
                ),
            },
            "estado": resultado.estado,
        }
        for resultado in registros
    ]
    return output_datatable_json(draw, total, data)


@udp_cubiculos.route("/udp_cubiculos")
def list_active():
    """Listado de Cubículos activos"""
    return render_template(
        "udp_cubiculos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Cubículos",
        estatus="A",
    )


@udp_cubiculos.route("/udp_cubiculos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Cubículos inactivos"""
    return render_template(
        "udp_cubiculos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Cubículos inactivos",
        estatus="B",
    )


@udp_cubiculos.route("/udp_cubiculos/<int:cubiculo_id>")
def detail(cubiculo_id):
    """Detalle de un Cubículo"""
    cubiculo = UdpCubiculo.query.get_or_404(cubiculo_id)
    return render_template("udp_cubiculos/detail.jinja2", cubiculo=cubiculo)


@udp_cubiculos.route("/udp_cubiculos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Cubículo"""
    form = UdpCubiculoForm()
    if form.validate_on_submit():
        nombre = safe_string(form.nombre.data, max_len=64)
        if UdpCubiculo.query.filter_by(nombre=nombre).first():
            flash("El nombre del cubículo ya está registrado y debe ser único.", "warning")
        else:
            cubiculo = UdpCubiculo(nombre=nombre, estado="disponible")
            database.session.add(cubiculo)
            try:
                database.session.commit()
            except IntegrityError:
                database.session.rollback()
                flash("El nombre del cubículo ya está registrado y debe ser único.", "warning")
            else:
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(f"Nuevo cubículo {cubiculo.nombre}"),
                    url=url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)
    return render_template("udp_cubiculos/new.jinja2", form=form)


@udp_cubiculos.route("/udp_cubiculos/edicion/<int:cubiculo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(cubiculo_id):
    """Editar Cubículo"""
    cubiculo = UdpCubiculo.query.get_or_404(cubiculo_id)
    form = UdpCubiculoForm()
    if form.validate_on_submit():
        nombre = safe_string(form.nombre.data, max_len=64)
        cubiculo_existente = UdpCubiculo.query.filter_by(nombre=nombre).first()
        if cubiculo_existente is not None and cubiculo_existente.id != cubiculo.id:
            flash("El nombre del cubículo ya está registrado y debe ser único.", "warning")
        else:
            cubiculo.nombre = nombre
            database.session.add(cubiculo)
            try:
                database.session.commit()
            except IntegrityError:
                database.session.rollback()
                flash("El nombre del cubículo ya está registrado y debe ser único.", "warning")
            else:
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(f"Editado cubículo {cubiculo.nombre}"),
                    url=url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)
    if request.method == "GET":
        form.nombre.data = cubiculo.nombre
    return render_template("udp_cubiculos/edit.jinja2", form=form, cubiculo=cubiculo)


@udp_cubiculos.route("/udp_cubiculos/eliminar/<int:cubiculo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(cubiculo_id):
    """Eliminar Cubículo"""
    cubiculo = UdpCubiculo.query.get_or_404(cubiculo_id)
    if cubiculo.estado == "ocupado":
        flash("No es posible dar de baja un cubículo ocupado.", "warning")
        return redirect(url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id))
    if cubiculo.estatus == "A":
        cubiculo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado cubículo {cubiculo.nombre}"),
            url=url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id))


@udp_cubiculos.route("/udp_cubiculos/recuperar/<int:cubiculo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(cubiculo_id):
    """Recuperar Cubículo"""
    cubiculo = UdpCubiculo.query.get_or_404(cubiculo_id)
    if cubiculo.estatus == "B":
        cubiculo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado cubículo {cubiculo.nombre}"),
            url=url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("udp_cubiculos.detail", cubiculo_id=cubiculo.id))

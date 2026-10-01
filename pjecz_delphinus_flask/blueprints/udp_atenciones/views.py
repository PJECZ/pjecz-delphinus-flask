"""
UDP Atenciones, vistas
"""

import json
from datetime import datetime, time

from flask import Blueprint, flash, get_flashed_messages, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_atenciones.forms import UdpAtencionForm
from pjecz_delphinus_flask.blueprints.udp_atenciones.models import Estatus, UdpAtencion
from pjecz_delphinus_flask.blueprints.udp_atenciones.pdf import generar_resumen_pdf
from pjecz_delphinus_flask.blueprints.udp_atenciones.services import asignar_datos_iniciales, filtro_participacion
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.blueprints.usuarios.models import Usuario
from pjecz_delphinus_flask.config.extensions import database
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP ATENCIONES"

udp_atenciones = Blueprint("udp_atenciones", __name__, template_folder="templates")
ATENCIONES_PAGE_SIZE = 50


def get_contraparte(form: UdpAtencionForm) -> UdpPersona | None:
    """Obtener una contraparte existente o crearla desde el formulario."""
    if form.udp_contraparte.data:
        contraparte = UdpPersona.query.filter_by(id=form.udp_contraparte.data, estatus="A").first()
        if contraparte:
            return contraparte
        flash("La contraparte seleccionada no está disponible.", "warning")
        return None
    if not form.nueva_contraparte.data:
        flash("Seleccione una contraparte o registre una nueva.", "warning")
        return None
    required_fields = (
        (form.contraparte_nombres.data, "Nombres"),
        (form.contraparte_apellido_primero.data, "Apellido Primero"),
        (form.contraparte_udp_sexo.data, "Sexo"),
        (form.contraparte_udp_tipo_condicion.data, "Tipo de Condición"),
    )
    missing_fields = [label for value, label in required_fields if not value]
    if missing_fields:
        flash(f"Complete los campos requeridos de la contraparte: {', '.join(missing_fields)}.", "warning")
        return None
    return UdpPersona(
        nombres=safe_string(form.contraparte_nombres.data, save_enie=True),
        apellido_primero=safe_string(form.contraparte_apellido_primero.data, save_enie=True),
        apellido_segundo=safe_string(form.contraparte_apellido_segundo.data, save_enie=True),
        nacimiento_fecha=form.contraparte_nacimiento_fecha.data,
        udp_sexo_id=form.contraparte_udp_sexo.data,
        udp_tipo_condicion_id=form.contraparte_udp_tipo_condicion.data,
        curp=safe_string(form.contraparte_curp.data),
        observaciones=safe_string(form.contraparte_observaciones.data, save_enie=True, max_len=1024),
    )


def save_atencion_contraparte(udp_atencion: UdpAtencion, contraparte: UdpPersona) -> bool:
    """Guardar una atención y su contraparte en una sola transacción."""
    udp_atencion.contraparte = contraparte
    database.session.add_all((udp_atencion, contraparte))
    try:
        if udp_atencion.id is None:
            asignar_datos_iniciales(udp_atencion, udp_atencion.visita)
        database.session.commit()
    except (IntegrityError, ValueError) as error:
        database.session.rollback()
        mensaje = "No fue posible guardar la contraparte. Verifique que la CURP no esté duplicada."
        if isinstance(error, ValueError):
            mensaje = str(error)
        flash(mensaje, "warning")
        return False
    return True


def configurar_estatus(form: UdpAtencionForm) -> None:
    """Cargar estados funcionales activos en el formulario."""
    form.estatus_id.choices = [
        (str(estatus.id), estatus.nombre.title()) for estatus in Estatus.query.filter_by(estatus="A").order_by(Estatus.id)
    ]


def get_defensor(form: UdpAtencionForm) -> Usuario | None:
    """Resolver un defensor activo seleccionado en el formulario."""
    try:
        defensor_id = int(form.defensor.data)
    except TypeError, ValueError:
        defensor_id = None
    defensor = Usuario.query.filter_by(id=defensor_id, estatus="A").first() if defensor_id is not None else None
    if defensor is None or "DEFENSOR" not in defensor.get_roles():
        flash("Seleccione un defensor activo.", "warning")
        return None
    return defensor


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
    filtro = request.form.get("filtro")
    es_defensor = "DEFENSOR" in current_user.get_roles()
    if filtro == "asignados" and es_defensor:
        consulta = (
            consulta.join(UdpAtencion.usuario)
            .join(UdpAtencion.estatus_atencion)
            .filter(
                Usuario.email == current_user.email,
                Estatus.nombre == "asignado",
                Estatus.estatus == "A",
            )
        )
    if "estatus" in request.form:
        consulta = consulta.filter(UdpAtencion.estatus == request.form["estatus"])
    """ else:
        consulta = consulta.filter_by(estatus="A") """
    if "udp_persona_id" in request.form:
        consulta = consulta.filter(
            or_(
                UdpAtencion.udp_persona_id == request.form["udp_persona_id"],
                UdpAtencion.contraparte_id == request.form["udp_persona_id"],
            )
        )
    ordenamiento = [UdpAtencion.id.desc()]
    if filtro == "asignados" and es_defensor:
        ordenamiento = [UdpAtencion.fecha.desc().nullslast(), UdpAtencion.id.desc()]
    registros = consulta.order_by(*ordenamiento).offset(start).limit(rows_per_page).all()
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
                "folio": resultado.folio or "",
                "tipo_atencion": resultado.visita or "",
                "fecha_siguiente_cita": (
                    resultado.fecha_siguiente_cita.strftime("%Y-%m-%d") if resultado.fecha_siguiente_cita else ""
                ),
                "estatus_atencion": resultado.estatus_atencion.nombre if resultado.estatus_atencion else "",
            }
        )
    return output_datatable_json(draw, total, data)


@udp_atenciones.route("/udp_atenciones/relacionadas_json")
def relacionadas_json():
    """Listar atenciones de una persona o de una pareja seleccionada."""
    persona_ids = {}
    for field_name in ("udp_persona_id", "contraparte_id"):
        value = request.args.get(field_name)
        if value is None:
            continue
        try:
            persona_id = int(value)
        except ValueError:
            return jsonify(error="El identificador de persona no es válido."), 400
        if persona_id < 1:
            return jsonify(error="El identificador de persona no es válido."), 400
        persona_ids[field_name] = persona_id
    if not persona_ids:
        return jsonify(error="Seleccione al menos una persona."), 400

    ids = set(persona_ids.values())
    personas_activas = UdpPersona.query.filter(UdpPersona.id.in_(ids), UdpPersona.estatus == "A").all()
    if {persona.id for persona in personas_activas} != ids:
        return jsonify(error="Una de las personas seleccionadas no está disponible."), 404

    udp_persona_id = persona_ids.get("udp_persona_id")
    contraparte_id = persona_ids.get("contraparte_id")
    persona_id = udp_persona_id if udp_persona_id is not None else contraparte_id
    filtro = filtro_participacion(persona_id, contraparte_id if udp_persona_id is not None else None)
    consulta = (
        UdpAtencion.query.options(joinedload(UdpAtencion.udp_tipo_tramite))
        .filter(filtro)
        .order_by(UdpAtencion.fecha.desc().nullslast(), UdpAtencion.id.desc())
    )
    resultados = consulta.limit(ATENCIONES_PAGE_SIZE + 1).all()
    has_more = len(resultados) > ATENCIONES_PAGE_SIZE
    resultados = resultados[:ATENCIONES_PAGE_SIZE]
    data = []
    for atencion in resultados:
        if udp_persona_id is not None and contraparte_id is not None:
            participacion = "Ambos"
        elif atencion.udp_persona_id == persona_id:
            participacion = "Actor"
        else:
            participacion = "Contraparte"
        data.append(
            {
                "id": atencion.id,
                "folio": atencion.folio or "",
                "fecha": atencion.fecha.strftime("%Y-%m-%d") if atencion.fecha else "",
                "tipo": atencion.udp_tipo_tramite.nombre,
                "tipo_atencion": atencion.visita or "",
                "expediente": atencion.expediente or "",
                "participacion": participacion,
                "url": url_for("udp_atenciones.detail", udp_atencion_id=atencion.id),
            }
        )
    return jsonify(results=data, pagination={"more": has_more})


@udp_atenciones.route("/udp_atenciones")
def list_active():
    """Listado de Atenciones activas"""
    filtro = request.args.get("filtro")
    if filtro != "asignados" or "DEFENSOR" not in current_user.get_roles():
        filtro = None
    return render_template(
        "udp_atenciones/list.jinja2",
        filtros=json.dumps({"filtro": filtro} if filtro else {}),
        titulo="Atenciones",
        estatus="A",
        filtro=filtro,
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


@udp_atenciones.route("/udp_atenciones/<int:udp_atencion_id>/resumen.pdf")
def resumen_pdf(udp_atencion_id):
    """Generar en memoria el resumen PDF de una atención."""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    archivo_pdf = generar_resumen_pdf(udp_atencion)
    respuesta = send_file(
        archivo_pdf,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"resumen-atencion-{udp_atencion.id}.pdf",
        max_age=0,
    )
    respuesta.headers["Cache-Control"] = "private, no-store"
    return respuesta


@udp_atenciones.route("/udp_atenciones/nuevo/<int:udp_persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(udp_persona_id):
    """Nueva Atención"""
    udp_persona = UdpPersona.query.filter_by(id=udp_persona_id, estatus="A").first_or_404()
    form = UdpAtencionForm()
    is_inline_request = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    distrito_por_defecto = current_user.autoridad.distrito if current_user.autoridad else None
    autoridad_por_defecto = current_user.autoridad
    defensor_id = current_user.id if "DEFENSOR" in current_user.get_roles() else None

    def render_form_error(message):
        if is_inline_request:
            get_flashed_messages()
            return jsonify(error=message, errors=form.errors), 400
        return render_template(
            "udp_atenciones/new.jinja2",
            form=form,
            udp_persona=udp_persona,
            distrito_por_defecto=distrito_por_defecto,
            autoridad_por_defecto=autoridad_por_defecto,
            defensor_id=defensor_id,
        )

    if form.validate_on_submit():
        defensor = get_defensor(form)
        if defensor is None:
            return render_form_error("Seleccione un defensor activo.")
        if not form.visita.data:
            flash("Seleccione el tipo de atención.", "warning")
            return render_form_error("Seleccione el tipo de atención.")
        contraparte = get_contraparte(form)
        if not contraparte:
            return render_form_error("Seleccione una contraparte activa o registre una nueva.")
        udp_atencion = UdpAtencion(
            udp_persona_id=udp_persona.id,
            udp_tipo_tramite_id=form.udp_tipo_tramite.data,
            usuario_id=defensor.id,
            autoridad_id=form.autoridad.data,
            visita=form.visita.data,
            expediente=form.expediente.data,
            fecha_siguiente_cita=(
                datetime.combine(form.fecha_siguiente_cita.data, time.min) if form.fecha_siguiente_cita.data else None
            ),
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        if not save_atencion_contraparte(udp_atencion, contraparte):
            return render_form_error("No fue posible guardar la atención. Revise los datos e inténtelo de nuevo.")
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva atención para {udp_persona.nombre_completo}"),
            url=url_for("udp_personas.detail", udp_persona_id=udp_persona.id),
        )
        bitacora.save()
        if is_inline_request:
            return jsonify(message="La atención se guardó correctamente."), 201
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    if request.method == "POST" and is_inline_request:
        return render_form_error("Revise los campos del formulario.")
    return render_template(
        "udp_atenciones/new.jinja2",
        form=form,
        udp_persona=udp_persona,
        distrito_por_defecto=distrito_por_defecto,
        autoridad_por_defecto=autoridad_por_defecto,
        defensor_id=defensor_id,
    )


@udp_atenciones.route("/udp_atenciones/nuevo_fragmento")
@permission_required(MODULO, Permiso.CREAR)
def new_fragment():
    """Renderizar el formulario existente con actor y contraparte validados y preseleccionados."""
    try:
        udp_persona_id = int(request.args.get("udp_persona_id", ""))
        contraparte_id = int(request.args.get("contraparte_id", ""))
    except ValueError:
        return jsonify(error="Seleccione un actor y una contraparte válidos."), 400
    actor = UdpPersona.query.filter_by(id=udp_persona_id, estatus="A").first_or_404()
    contraparte = UdpPersona.query.filter_by(id=contraparte_id, estatus="A").first_or_404()
    form = UdpAtencionForm()
    form.udp_contraparte.choices = [(str(contraparte.id), contraparte.nombre_completo)]
    form.udp_contraparte.data = str(contraparte.id)
    defensor_id = current_user.id if "DEFENSOR" in current_user.get_roles() else None
    return render_template(
        "udp_atenciones/_form.jinja2",
        form=form,
        udp_persona=actor,
        contraparte=contraparte,
        inline_mode=True,
        distrito_por_defecto=current_user.autoridad.distrito if current_user.autoridad else None,
        autoridad_por_defecto=current_user.autoridad,
        defensor_id=defensor_id,
    )


@udp_atenciones.route("/udp_atenciones/edicion/<int:udp_atencion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(udp_atencion_id):
    """Editar Atención"""
    udp_atencion = UdpAtencion.query.get_or_404(udp_atencion_id)
    form = UdpAtencionForm()
    configurar_estatus(form)
    if form.validate_on_submit():
        defensor = get_defensor(form)
        if defensor is None:
            return render_template("udp_atenciones/edit.jinja2", form=form, udp_atencion=udp_atencion)
        contraparte = get_contraparte(form)
        if not contraparte:
            return render_template("udp_atenciones/edit.jinja2", form=form, udp_atencion=udp_atencion)
        udp_atencion.udp_tipo_tramite_id = form.udp_tipo_tramite.data
        udp_atencion.autoridad_id = form.autoridad.data
        udp_atencion.usuario_id = defensor.id
        udp_atencion.expediente = form.expediente.data
        udp_atencion.fecha_siguiente_cita = (
            datetime.combine(form.fecha_siguiente_cita.data, time.min) if form.fecha_siguiente_cita.data else None
        )
        try:
            estatus_id = int(form.estatus_id.data)
        except TypeError, ValueError:
            estatus_id = None
        estatus = Estatus.query.filter_by(id=estatus_id, estatus="A").first() if estatus_id is not None else None
        if estatus is None:
            flash("El estatus seleccionado no está disponible.", "warning")
            return render_template("udp_atenciones/edit.jinja2", form=form, udp_atencion=udp_atencion)
        udp_atencion.estatus_id = estatus.id
        udp_atencion.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
        if not save_atencion_contraparte(udp_atencion, contraparte):
            return render_template("udp_atenciones/edit.jinja2", form=form, udp_atencion=udp_atencion)
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
    if udp_atencion.contraparte:
        form.udp_contraparte.data = udp_atencion.contraparte_id
    form.expediente.data = udp_atencion.expediente
    form.fecha_siguiente_cita.data = udp_atencion.fecha_siguiente_cita.date() if udp_atencion.fecha_siguiente_cita else None
    form.estatus_id.data = str(udp_atencion.estatus_id) if udp_atencion.estatus_id else None
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

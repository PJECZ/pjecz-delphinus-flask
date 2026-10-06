"""
UDP Atenciones, vistas
"""

import json
from datetime import datetime, time

from flask import Blueprint, flash, get_flashed_messages, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from pjecz_delphinus_flask.blueprints.bitacoras.models import Bitacora
from pjecz_delphinus_flask.blueprints.modulos.models import Modulo
from pjecz_delphinus_flask.blueprints.permisos.models import Permiso
from pjecz_delphinus_flask.blueprints.udp_atenciones.forms import UdpAtencionForm, UdpAtencionNuevaForm
from pjecz_delphinus_flask.blueprints.udp_atenciones.models import Estatus, UdpAtencion
from pjecz_delphinus_flask.blueprints.udp_atenciones.pdf import generar_resumen_pdf
from pjecz_delphinus_flask.blueprints.udp_atenciones.services import (
    SUBSECUENTE,
    asignar_datos_iniciales,
    filtro_participacion,
)
from pjecz_delphinus_flask.blueprints.udp_cubiculos.models import UdpCubiculo
from pjecz_delphinus_flask.blueprints.udp_personas.models import UdpPersona
from pjecz_delphinus_flask.blueprints.udp_tipos_visitas.models import UdpTipoVisita
from pjecz_delphinus_flask.blueprints.usuarios.decorators import permission_required
from pjecz_delphinus_flask.blueprints.usuarios.models import Usuario
from pjecz_delphinus_flask.config.extensions import database
from pjecz_delphinus_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_delphinus_flask.lib.safe_string import safe_message, safe_string

MODULO = "UDP ATENCIONES"

udp_atenciones = Blueprint("udp_atenciones", __name__, template_folder="templates")
ATENCIONES_PAGE_SIZE = 50


def cubiculo_asignado_a_otra_atencion(cubiculo_id: int, udp_atencion_id: int | None = None) -> bool:
    """Verificar si otra atención activa ya ocupa el cubículo."""
    consulta = (
        select(UdpAtencion.id)
        .join(Estatus, UdpAtencion.estatus_id == Estatus.id)
        .where(
            UdpAtencion.id_cubiculo == cubiculo_id,
            Estatus.nombre == "asignado",
            Estatus.estatus == "A",
        )
    )
    if udp_atencion_id is not None:
        consulta = consulta.where(UdpAtencion.id != udp_atencion_id)
    return database.session.execute(consulta.limit(1)).scalar_one_or_none() is not None


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


def save_atencion_contraparte(
    udp_atencion: UdpAtencion,
    contraparte: UdpPersona,
    atencion_origen: UdpAtencion | None = None,
    cubiculo_id: str | None = None,
    estatus_anterior: str | None = None,
) -> bool:
    """Guardar una atención, su contraparte y el cubículo en una sola transacción."""
    cubiculo = None
    cubiculo_anterior = None
    if cubiculo_id:
        try:
            id_seleccionado = int(cubiculo_id)
        except ValueError:
            database.session.rollback()
            flash("Seleccione un cubículo disponible.", "warning")
            return False
        if udp_atencion.id is None:
            cubiculo = database.session.execute(
                select(UdpCubiculo)
                .where(UdpCubiculo.id == id_seleccionado, UdpCubiculo.estatus == "A")
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalar_one_or_none()
            if (
                cubiculo is None
                or cubiculo.estado != "disponible"
                or cubiculo_asignado_a_otra_atencion(id_seleccionado)
            ):
                database.session.rollback()
                flash("El cubículo seleccionado ya no está disponible. Seleccione otro cubículo.", "warning")
                return False
            udp_atencion.id_cubiculo = cubiculo.id
            cubiculo.estado = "ocupado"
        elif id_seleccionado != udp_atencion.id_cubiculo:
            estatus_seleccionado = database.session.get(Estatus, udp_atencion.estatus_id)
            if estatus_seleccionado is None or estatus_seleccionado.nombre != "asignado":
                database.session.rollback()
                flash("Solo se puede cambiar el cubículo de una atención asignada.", "warning")
                return False
            ids_cubiculos = {id_seleccionado}
            if udp_atencion.id_cubiculo is not None:
                ids_cubiculos.add(udp_atencion.id_cubiculo)
            cubiculos_bloqueados = database.session.execute(
                select(UdpCubiculo)
                .where(UdpCubiculo.id.in_(ids_cubiculos))
                .order_by(UdpCubiculo.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalars().all()
            cubiculos_por_id = {registro.id: registro for registro in cubiculos_bloqueados}
            cubiculo = cubiculos_por_id.get(id_seleccionado)
            if cubiculo is None or cubiculo.estatus != "A" or cubiculo.estado != "disponible":
                database.session.rollback()
                flash("El nuevo cubículo seleccionado ya no está disponible. Seleccione otro cubículo.", "warning")
                return False
            if cubiculo_asignado_a_otra_atencion(cubiculo.id, udp_atencion.id):
                database.session.rollback()
                flash("El cubículo seleccionado ya está asignado a otra atención.", "warning")
                return False
            if udp_atencion.id_cubiculo is not None:
                cubiculo_anterior = cubiculos_por_id.get(udp_atencion.id_cubiculo)
                if cubiculo_anterior is None or cubiculo_anterior.estado != "ocupado":
                    database.session.rollback()
                    flash("No fue posible validar el cubículo actual de la atención.", "warning")
                    return False
                if cubiculo_asignado_a_otra_atencion(cubiculo_anterior.id, udp_atencion.id):
                    database.session.rollback()
                    flash("No fue posible liberar el cubículo actual porque otra atención lo tiene asignado.", "warning")
                    return False
                cubiculo_anterior.estado = "disponible"
            cubiculo.estado = "ocupado"
            udp_atencion.id_cubiculo = cubiculo.id
    if udp_atencion.id is not None and udp_atencion.id_cubiculo is not None:
        estatus_seleccionado = database.session.get(Estatus, udp_atencion.estatus_id)
        if estatus_seleccionado is not None and estatus_seleccionado.nombre == "asignado":
            cubiculo_actual = database.session.execute(
                select(UdpCubiculo)
                .where(UdpCubiculo.id == udp_atencion.id_cubiculo)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).scalar_one_or_none()
            if (
                cubiculo_actual is None
                or cubiculo_actual.estado != "ocupado"
                or cubiculo_asignado_a_otra_atencion(cubiculo_actual.id, udp_atencion.id)
            ):
                database.session.rollback()
                flash("El cubículo actual no está ocupado correctamente por esta atención.", "warning")
                return False
    estatus_actual = database.session.get(Estatus, udp_atencion.estatus_id) if udp_atencion.id is not None else None
    if (
        udp_atencion.id is not None
        and estatus_anterior == "asignado"
        and estatus_actual is not None
        and estatus_actual.nombre == "cerrado"
        and udp_atencion.id_cubiculo is not None
    ):
        cubiculo_anterior = database.session.execute(
            select(UdpCubiculo)
            .where(UdpCubiculo.id == udp_atencion.id_cubiculo)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if (
            cubiculo_anterior is None
            or cubiculo_anterior.estado != "ocupado"
            or cubiculo_asignado_a_otra_atencion(cubiculo_anterior.id, udp_atencion.id)
        ):
            database.session.rollback()
            flash("No fue posible cerrar la atención porque el cubículo asociado no está ocupado correctamente.", "warning")
            return False
        cubiculo_anterior.estado = "disponible"
    udp_atencion.contraparte = contraparte
    database.session.add_all((udp_atencion, contraparte))
    if cubiculo is not None:
        database.session.add(cubiculo)
    if cubiculo_anterior is not None:
        database.session.add(cubiculo_anterior)
    try:
        if udp_atencion.id is None:
            asignar_datos_iniciales(udp_atencion, udp_atencion.visita, atencion_origen)
        database.session.commit()
    except (IntegrityError, ValueError) as error:
        database.session.rollback()
        mensaje = (
            "No fue posible guardar la atención. Verifique que la CURP no esté duplicada y que el cubículo siga disponible."
        )
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


def configurar_cubiculos_disponibles(
    form: UdpAtencionForm, cubiculo_actual: UdpCubiculo | None = None
) -> list[UdpCubiculo]:
    """Cargar cubículos disponibles y conservar el cubículo actual al editar."""
    cubiculos = (
        UdpCubiculo.query.filter_by(estatus="A", estado="disponible")
        .order_by(UdpCubiculo.nombre, UdpCubiculo.id)
        .all()
    )
    opciones = list(cubiculos)
    if cubiculo_actual is not None and cubiculo_actual not in opciones:
        opciones.append(cubiculo_actual)
        opciones.sort(key=lambda registro: (registro.nombre, registro.id))
    opcion_vacia = "Conservar cubículo actual" if cubiculo_actual is not None else "Sin cubículo"
    form.cubiculo_id.choices = [("", opcion_vacia)] + [(str(cubiculo.id), cubiculo.nombre) for cubiculo in opciones]
    return cubiculos


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


def get_datos_subsecuente(atencion_origen: UdpAtencion) -> dict[str, int | None]:
    """Obtener los identificadores de trámite, distrito y autoridad del origen."""
    autoridad = atencion_origen.autoridad
    return {
        "udp_tipo_tramite_id": atencion_origen.udp_tipo_tramite_id,
        "distrito_id": autoridad.distrito_id if autoridad else None,
        "autoridad_id": atencion_origen.autoridad_id,
    }


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
    if es_defensor and filtro != "todas":
        filtro = "asignados"
        consulta = (
            consulta.join(UdpAtencion.estatus_atencion)
            .filter(
                UdpAtencion.usuario_id == current_user.id,
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
    registros = (
        consulta.options(
            joinedload(UdpAtencion.cubiculo),
            joinedload(UdpAtencion.udp_tipo_tramite),
            joinedload(UdpAtencion.usuario),
            joinedload(UdpAtencion.estatus_atencion),
        )
        .order_by(*ordenamiento)
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
                    "id": resultado.id,
                    "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                    "url": url_for("udp_atenciones.detail", udp_atencion_id=resultado.id),
                },
                "udp_tipo_tramite_nombre": resultado.udp_tipo_tramite.nombre,
                "usuario_email": resultado.usuario.email,
                "cubiculo_nombre": resultado.cubiculo.nombre if resultado.cubiculo else "Sin asignar",
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
    es_defensor = "DEFENSOR" in current_user.get_roles()
    filtro = request.args.get("filtro")
    if es_defensor:
        if filtro not in {"asignados", "todas"}:
            filtro = "asignados"
    else:
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


@udp_atenciones.route("/udp_atenciones/<int:udp_atencion_origen_id>/subsecuente", methods=["GET", "POST"])
@udp_atenciones.route("/udp_atenciones/nuevo/<int:udp_persona_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(udp_persona_id=None, udp_atencion_origen_id=None):
    """Nueva Atención"""
    contexto_subsecuente = None
    if udp_atencion_origen_id is not None:
        atencion_origen = UdpAtencion.query.get_or_404(udp_atencion_origen_id)
        actor = UdpPersona.query.filter_by(id=atencion_origen.udp_persona_id, estatus="A").first()
        contraparte_origen = (
            UdpPersona.query.filter_by(id=atencion_origen.contraparte_id, estatus="A").first()
            if atencion_origen.contraparte_id
            else None
        )
        defensor_origen = Usuario.query.filter_by(id=atencion_origen.usuario_id, estatus="A").first()
        tipo_subsecuente = UdpTipoVisita.query.filter_by(nombre=SUBSECUENTE, estatus="A").first()
        if actor is None:
            flash("El actor de la atención original no está disponible.", "warning")
            return redirect(url_for("udp_atenciones.detail", udp_atencion_id=atencion_origen.id))
        if contraparte_origen is None:
            flash("La contraparte de la atención original no está disponible.", "warning")
            return redirect(url_for("udp_atenciones.detail", udp_atencion_id=atencion_origen.id))
        if defensor_origen is None or "DEFENSOR" not in defensor_origen.get_roles():
            flash("El defensor de la atención original no está disponible.", "warning")
            return redirect(url_for("udp_atenciones.detail", udp_atencion_id=atencion_origen.id))
        if tipo_subsecuente is None:
            flash("El tipo de atención Subsecuente no está disponible.", "warning")
            return redirect(url_for("udp_atenciones.detail", udp_atencion_id=atencion_origen.id))
        udp_persona = actor
        contexto_subsecuente = {
            "atencion_origen": atencion_origen,
            "contraparte": contraparte_origen,
            "defensor": defensor_origen,
            "tipo_visita": tipo_subsecuente,
            **get_datos_subsecuente(atencion_origen),
        }
    else:
        udp_persona = UdpPersona.query.filter_by(id=udp_persona_id, estatus="A").first_or_404()
    form = UdpAtencionNuevaForm()
    cubiculos_disponibles = configurar_cubiculos_disponibles(form)
    if contexto_subsecuente:
        if request.method == "GET":
            form.defensor.data = str(contexto_subsecuente["defensor"].id)
        form.udp_contraparte.data = str(contexto_subsecuente["contraparte"].id)
        form.visita.data = contexto_subsecuente["tipo_visita"].nombre
    is_inline_request = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if contexto_subsecuente:
        autoridad_origen = contexto_subsecuente["atencion_origen"].autoridad
        distrito_origen = autoridad_origen.distrito if autoridad_origen else None
        distrito_por_defecto = distrito_origen if distrito_origen and distrito_origen.estatus == "A" else None
        autoridad_por_defecto = (
            autoridad_origen if autoridad_origen and autoridad_origen.estatus == "A" and distrito_por_defecto else None
        )
    else:
        distrito_por_defecto = current_user.autoridad.distrito if current_user.autoridad else None
        autoridad_por_defecto = current_user.autoridad
    defensor_id = (
        contexto_subsecuente["defensor"].id
        if contexto_subsecuente
        else current_user.id if "DEFENSOR" in current_user.get_roles() else None
    )

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
            contexto_subsecuente=contexto_subsecuente,
            cubiculos_disponibles=cubiculos_disponibles,
        )

    if form.validate_on_submit():
        defensor = get_defensor(form)
        if defensor is None:
            return render_form_error("Seleccione un defensor activo.")
        tipo_visita = contexto_subsecuente["tipo_visita"].nombre if contexto_subsecuente else form.visita.data
        if not tipo_visita:
            flash("Seleccione el tipo de atención.", "warning")
            return render_form_error("Seleccione el tipo de atención.")
        contraparte = contexto_subsecuente["contraparte"] if contexto_subsecuente else get_contraparte(form)
        if not contraparte:
            return render_form_error("Seleccione una contraparte activa o registre una nueva.")
        udp_atencion = UdpAtencion(
            udp_persona_id=udp_persona.id,
            udp_tipo_tramite_id=form.udp_tipo_tramite.data,
            usuario_id=defensor.id,
            autoridad_id=form.autoridad.data,
            visita=tipo_visita,
            expediente=form.expediente.data,
            fecha_siguiente_cita=(
                datetime.combine(form.fecha_siguiente_cita.data, time.min) if form.fecha_siguiente_cita.data else None
            ),
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        atencion_origen = contexto_subsecuente["atencion_origen"] if contexto_subsecuente else None
        if not save_atencion_contraparte(udp_atencion, contraparte, atencion_origen, form.cubiculo_id.data):
            mensaje = "No fue posible guardar la atención. Revise los datos e inténtelo de nuevo."
            if is_inline_request:
                mensajes = get_flashed_messages()
                if mensajes:
                    mensaje = mensajes[-1]
            return render_form_error(mensaje)
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
        contexto_subsecuente=contexto_subsecuente,
        cubiculos_disponibles=cubiculos_disponibles,
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
    form = UdpAtencionNuevaForm()
    cubiculos_disponibles = configurar_cubiculos_disponibles(form)
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
        cubiculos_disponibles=cubiculos_disponibles,
    )


@udp_atenciones.route("/udp_atenciones/edicion/<int:udp_atencion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(udp_atencion_id):
    """Editar Atención"""
    udp_atencion = (
        UdpAtencion.query.filter_by(id=udp_atencion_id)
        .with_for_update()
        .execution_options(populate_existing=True)
        .first_or_404()
    )
    form = UdpAtencionForm()
    configurar_estatus(form)
    cubiculos_disponibles = configurar_cubiculos_disponibles(form, udp_atencion.cubiculo)
    if form.validate_on_submit():
        defensor = get_defensor(form)
        if defensor is None:
            return render_template(
                "udp_atenciones/edit.jinja2",
                form=form,
                udp_atencion=udp_atencion,
                cubiculos_disponibles=cubiculos_disponibles,
            )
        contraparte = get_contraparte(form)
        if not contraparte:
            return render_template(
                "udp_atenciones/edit.jinja2",
                form=form,
                udp_atencion=udp_atencion,
                cubiculos_disponibles=cubiculos_disponibles,
            )
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
        estatus_anterior = udp_atencion.estatus_atencion.nombre if udp_atencion.estatus_atencion else None
        estatus = Estatus.query.filter_by(id=estatus_id, estatus="A").first() if estatus_id is not None else None
        if estatus is None:
            flash("El estatus seleccionado no está disponible.", "warning")
            return render_template(
                "udp_atenciones/edit.jinja2",
                form=form,
                udp_atencion=udp_atencion,
                cubiculos_disponibles=cubiculos_disponibles,
            )
        udp_atencion.estatus_id = estatus.id
        udp_atencion.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
        if not save_atencion_contraparte(
            udp_atencion,
            contraparte,
            cubiculo_id=form.cubiculo_id.data,
            estatus_anterior=estatus_anterior,
        ):
            return render_template(
                "udp_atenciones/edit.jinja2",
                form=form,
                udp_atencion=udp_atencion,
                cubiculos_disponibles=cubiculos_disponibles,
            )
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
    if request.method == "GET" and udp_atencion.id_cubiculo is not None:
        form.cubiculo_id.data = str(udp_atencion.id_cubiculo)
    form.observaciones.data = udp_atencion.observaciones
    return render_template(
        "udp_atenciones/edit.jinja2",
        form=form,
        udp_atencion=udp_atencion,
        cubiculos_disponibles=cubiculos_disponibles,
    )


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

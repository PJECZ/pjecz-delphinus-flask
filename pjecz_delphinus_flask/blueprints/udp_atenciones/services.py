"""Reglas de negocio para atenciones."""

from datetime import datetime

from sqlalchemy import Integer, cast, func, select
from sqlalchemy.dialects.postgresql import insert

from pjecz_delphinus_flask.blueprints.udp_atenciones.models import Estatus, UdpAtencion, UdpAtencionFolio
from pjecz_delphinus_flask.config.extensions import database

PRIMERA_VEZ = "PRIMERA VEZ"
SUBSECUENTE = "SUBSECUENTE"


def _generar_folio(anio: int) -> str:
    """Incrementar el contador anual dentro de la transacción actual."""
    ultimo_numero = database.session.execute(
        select(func.max(cast(func.split_part(UdpAtencion.folio, "/", 1), Integer))).where(
            UdpAtencion.visita == PRIMERA_VEZ,
            UdpAtencion.folio.op("~")(rf"^[0-9]+/{anio}$"),
        )
    ).scalar_one()
    insertar_contador = insert(UdpAtencionFolio).values(anio=anio, ultimo_numero=ultimo_numero or 0)
    insertar_contador = insertar_contador.on_conflict_do_nothing(index_elements=[UdpAtencionFolio.anio])
    database.session.execute(insertar_contador)
    contador = database.session.execute(
        select(UdpAtencionFolio).where(UdpAtencionFolio.anio == anio).with_for_update()
    ).scalar_one()
    contador.ultimo_numero += 1
    return f"{contador.ultimo_numero}/{anio}"


def asignar_datos_iniciales(udp_atencion: UdpAtencion, tipo_atencion: str | None) -> None:
    """Asignar folio inicial y estado funcional a una atención nueva."""
    estatus_asignado = database.session.execute(
        select(Estatus).where(Estatus.nombre == "asignado", Estatus.estatus == "A")
    ).scalar_one_or_none()
    if estatus_asignado is None:
        raise ValueError("No existe el estatus funcional asignado.")
    udp_atencion.estatus_id = estatus_asignado.id

    tipo_atencion = (tipo_atencion or PRIMERA_VEZ).strip().upper()
    if tipo_atencion == SUBSECUENTE:
        consulta_inicial = select(UdpAtencion).where(
            UdpAtencion.udp_persona_id == udp_atencion.udp_persona_id,
            UdpAtencion.visita == PRIMERA_VEZ,
            UdpAtencion.folio.is_not(None),
            UdpAtencion.folio != "",
        )
        if udp_atencion.expediente:
            consulta_inicial = consulta_inicial.where(UdpAtencion.expediente == udp_atencion.expediente)
        atencion_inicial = database.session.execute(
            consulta_inicial.order_by(UdpAtencion.id.desc()).limit(1)
        ).scalar_one_or_none()
        if atencion_inicial is None:
            raise ValueError("No existe una primera atención para reutilizar el folio.")
        udp_atencion.folio = atencion_inicial.folio
        udp_atencion.atencion_inicial = atencion_inicial
        return

    if tipo_atencion != PRIMERA_VEZ:
        raise ValueError("El tipo de atención no es válido.")
    udp_atencion.folio = _generar_folio(datetime.now().year)
    database.session.add(udp_atencion)
    database.session.flush()
    udp_atencion.atencion_inicial_id = udp_atencion.id
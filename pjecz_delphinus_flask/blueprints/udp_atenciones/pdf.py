"""Generación de documentos PDF para atenciones."""

from datetime import datetime
from io import BytesIO
from pathlib import Path

from flask import current_app, render_template
from xhtml2pdf import pisa

from pjecz_delphinus_flask.blueprints.udp_atenciones.models import UdpAtencion

MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def _formatear_fecha(fecha: datetime) -> str:
    """Formatear una fecha en español sin depender del locale del servidor."""
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def _resolver_recurso(uri: str, rel: str | None) -> str:
    """Resolver recursos estáticos locales utilizados por xhtml2pdf."""
    static_url_path = current_app.static_url_path or "/static"
    prefijo = f"{static_url_path.rstrip('/')}/"
    if uri.startswith(prefijo):
        static_folder = Path(current_app.static_folder or "").resolve()
        recurso = (static_folder / uri[len(prefijo) :]).resolve()
        recurso.relative_to(static_folder)
        if recurso.is_file():
            return str(recurso)
        raise FileNotFoundError(f"No se encontró el recurso estático {uri}.")
    return uri


def generar_resumen_pdf(udp_atencion: UdpAtencion) -> BytesIO:
    """Renderizar el resumen de atención en memoria."""
    fecha_cita = udp_atencion.fecha_siguiente_cita
    tipo_atencion = (udp_atencion.visita or "").strip().upper()
    tipos_atencion = {"PRIMERA VEZ": "Primera vez", "SUBSECUENTE": "Subsecuente"}
    if tipo_atencion not in tipos_atencion:
        tipo_atencion = tipo_atencion.title() if tipo_atencion else "No disponible"

    html = render_template(
        "udp_atenciones/resumen_pdf.jinja2",
        persona=udp_atencion.udp_persona.nombre_completo if udp_atencion.udp_persona else "No disponible",
        expediente=udp_atencion.expediente or "No especificado",
        folio=udp_atencion.folio or "No disponible",
        tipo_atencion=tipos_atencion.get(tipo_atencion, tipo_atencion),
        fecha_cita=_formatear_fecha(fecha_cita) if fecha_cita else "Sin cita programada",
        defensor=udp_atencion.usuario.nombre if udp_atencion.usuario else "No asignado",
    )
    salida = BytesIO()
    resultado = pisa.CreatePDF(
        src=html,
        dest=salida,
        encoding="utf-8",
        link_callback=_resolver_recurso,
    )
    if resultado.err:
        raise RuntimeError("No fue posible generar el resumen PDF de la atención.")
    salida.seek(0)
    return salida
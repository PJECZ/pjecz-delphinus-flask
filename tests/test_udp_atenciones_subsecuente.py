from types import SimpleNamespace

import pytest

from pjecz_delphinus_flask.blueprints.udp_atenciones.models import UdpAtencion
from pjecz_delphinus_flask.blueprints.udp_atenciones import services
from pjecz_delphinus_flask.blueprints.udp_atenciones.views import get_datos_subsecuente


def test_subsecuente_context_includes_source_foreign_keys():
    atencion_origen = SimpleNamespace(
        udp_tipo_tramite_id=14,
        autoridad_id=29,
        autoridad=SimpleNamespace(distrito_id=6),
    )

    assert get_datos_subsecuente(atencion_origen) == {
        "udp_tipo_tramite_id": 14,
        "distrito_id": 6,
        "autoridad_id": 29,
    }


def test_subsecuente_context_leaves_district_empty_without_source_authority():
    atencion_origen = SimpleNamespace(udp_tipo_tramite_id=14, autoridad_id=None, autoridad=None)

    assert get_datos_subsecuente(atencion_origen) == {
        "udp_tipo_tramite_id": 14,
        "distrito_id": None,
        "autoridad_id": None,
    }


def test_subsecuente_reutiliza_el_folio_de_la_atencion_origen(monkeypatch):
    estatus_asignado = SimpleNamespace(id=4)
    monkeypatch.setattr(
        services,
        "database",
        SimpleNamespace(
            session=SimpleNamespace(execute=lambda query: SimpleNamespace(scalar_one_or_none=lambda: estatus_asignado))
        ),
    )
    atencion_inicial = UdpAtencion(udp_persona_id=12, visita="PRIMERA VEZ", folio="18/2026")
    atencion_origen = UdpAtencion(udp_persona_id=12, visita="SUBSECUENTE", atencion_inicial=atencion_inicial)
    nueva_atencion = UdpAtencion(udp_persona_id=12, visita="SUBSECUENTE")

    services.asignar_datos_iniciales(nueva_atencion, "SUBSECUENTE", atencion_origen)

    assert nueva_atencion.estatus_id == estatus_asignado.id
    assert nueva_atencion.folio == atencion_inicial.folio
    assert nueva_atencion.atencion_inicial is atencion_inicial


def test_subsecuente_rechaza_atencion_origen_sin_folio_inicial(monkeypatch):
    monkeypatch.setattr(
        services,
        "database",
        SimpleNamespace(
            session=SimpleNamespace(execute=lambda query: SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(id=4)))
        ),
    )
    atencion_origen = UdpAtencion(udp_persona_id=12, visita="SUBSECUENTE")
    nueva_atencion = UdpAtencion(udp_persona_id=12, visita="SUBSECUENTE")

    with pytest.raises(ValueError, match="primera atención válida"):
        services.asignar_datos_iniciales(nueva_atencion, "SUBSECUENTE", atencion_origen)

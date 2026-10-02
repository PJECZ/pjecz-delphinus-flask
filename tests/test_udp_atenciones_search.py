from pjecz_delphinus_flask.blueprints.udp_atenciones.services import filtro_participacion


def test_filter_matches_person_in_either_role():
    compiled = str(filtro_participacion(7).compile())

    assert "udp_atenciones.udp_persona_id =" in compiled
    assert "udp_atenciones.contraparte_id =" in compiled


def test_filter_matches_both_pair_orientations():
    expression = filtro_participacion(7, 12)
    compiled = str(expression.compile())
    parameters = set(expression.compile().params.values())

    assert compiled.count("udp_persona_id") == 2
    assert compiled.count("contraparte_id") == 2
    assert parameters == {7, 12}

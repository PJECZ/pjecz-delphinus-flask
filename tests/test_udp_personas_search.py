from types import SimpleNamespace

import pytest
from flask import Flask

from pjecz_delphinus_flask.blueprints.udp_personas import views


class FakeQuery:
    def __init__(self):
        self.filters = []
        self.executed = False

    def filter_by(self, **kwargs):
        assert kwargs == {"estatus": "A"}
        return self

    def filter(self, expression):
        self.filters.append(expression)
        return self

    def order_by(self, *columns):
        self.ordering = columns
        return self

    def all(self):
        self.executed = True
        return [
            SimpleNamespace(
                id=7,
                nombre_completo="AGUILAR LÓPEZ CARLOS",
                apellido_primero="AGUILAR",
                apellido_segundo="LÓPEZ",
                nombres="CARLOS",
                curp="CURP123",
            )
        ]


@pytest.fixture
def invoke_search(monkeypatch):
    app = Flask(__name__)
    query = FakeQuery()
    monkeypatch.setattr(views.UdpPersona, "query", query)

    def invoke(**params):
        with app.test_request_context("/udp_personas/select_json", query_string=params):
            response = views.select_json()
        return response, query

    return invoke


def get_filter_values(query):
    return [next(iter(expression.compile().params.values())).strip("%") for expression in query.filters]


def test_search_by_names_uses_partial_match_and_normalizes_case(invoke_search):
    response, query = invoke_search(nombres="carlos")

    assert response["results"][0]["id"] == 7
    assert response["results"][0]["nombres"] == "CARLOS"
    assert response["results"][0]["search_terms"] == {"nombres": "CARLOS"}
    assert get_filter_values(query) == ["CARLOS"]


@pytest.mark.parametrize(
    ("params", "expected_terms"),
    [
        ({"nombres": "Carlos", "apellido_primero": "Aguilar"}, ["CARLOS", "AGUILAR"]),
        ({"nombres": "Carlos", "apellido_segundo": "López"}, ["CARLOS", "LÓPEZ"]),
        ({"apellido_primero": "Aguilar", "apellido_segundo": "López"}, ["AGUILAR", "LÓPEZ"]),
        (
            {
                "nombres": "Carlos",
                "apellido_primero": "Aguilar",
                "apellido_segundo": "López",
                "curp": "CURP123",
            },
            ["CARLOS", "AGUILAR", "LÓPEZ", "CURP123"],
        ),
    ],
)
def test_search_applies_each_nonempty_field_as_and_filter(invoke_search, params, expected_terms):
    response, query = invoke_search(**params)

    assert response["results"]
    assert get_filter_values(query) == expected_terms


def test_search_by_curp_is_partial(invoke_search):
    _, query = invoke_search(curp="CURP1")

    assert get_filter_values(query) == ["CURP1"]


def test_empty_search_does_not_execute_query(invoke_search):
    response, query = invoke_search(nombres="", apellido_primero="", apellido_segundo="", curp="")

    assert response["results"] == []
    assert query.executed is False


def test_legacy_search_term_keeps_or_behavior(invoke_search):
    _, query = invoke_search(searchTerm="carlos")

    assert len(query.filters) == 1
    assert len(query.filters[0].clauses) == 4
    assert get_filter_values(query) == ["CARLOS"]
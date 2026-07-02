from app.scraper.indeed import fetch_indeed_offers
from app.scraper.infojobs import fetch_infojobs_offers, get_infojobs_config, search_infojobs_offers


REQUIRED_OFFER_FIELDS = {"titulo", "empresa", "ubicacion", "enlace", "fuente"}


def assert_valid_offer_structure(offers):
    assert isinstance(offers, list)
    assert offers

    offer = offers[0]
    assert REQUIRED_OFFER_FIELDS.issubset(offer.keys())

    for field in REQUIRED_OFFER_FIELDS:
        assert isinstance(offer[field], str)
        assert offer[field]


def test_infojobs_devuelve_estructura_valida_sin_llamada_real(monkeypatch):
    monkeypatch.delenv("INFOJOBS_CLIENT_ID", raising=False)
    monkeypatch.delenv("INFOJOBS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("INFOJOBS_REDIRECT_URI", raising=False)

    offers = fetch_infojobs_offers(query="python", limit=2)

    assert_valid_offer_structure(offers)
    assert offers[0]["fuente"] == "InfoJobs"
    assert len(offers) <= 2


def test_infojobs_lee_configuracion_desde_entorno(monkeypatch):
    monkeypatch.setenv("INFOJOBS_CLIENT_ID", "client-id")
    monkeypatch.setenv("INFOJOBS_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("INFOJOBS_REDIRECT_URI", "http://localhost:8000/callback")

    config = get_infojobs_config()

    assert config.client_id == "client-id"
    assert config.client_secret == "client-secret"
    assert config.redirect_uri == "http://localhost:8000/callback"
    assert config.has_credentials is True


def test_infojobs_busqueda_con_credenciales_usa_requests_mock(monkeypatch):
    monkeypatch.setenv("INFOJOBS_CLIENT_ID", "client-id")
    monkeypatch.setenv("INFOJOBS_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("INFOJOBS_REDIRECT_URI", "http://localhost:8000/callback")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {
                        "title": "Python Backend Developer",
                        "author": {"name": "JobRadar Labs"},
                        "city": "Madrid",
                        "teleworking": {"name": "Remoto"},
                        "salaryDescription": "No especificado",
                        "requirementMin": "APIs con FastAPI.",
                        "link": "https://www.infojobs.net/madrid/python-backend/of-test",
                        "published": "2026-06-30T10:00:00Z",
                    }
                ]
            }

    def fake_get(url, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.scraper.infojobs.requests.get", fake_get)

    offers = search_infojobs_offers(
        keyword="python",
        provincia="Madrid",
        modalidad="Remoto",
        limit=1,
    )

    assert_valid_offer_structure(offers)
    assert offers[0]["titulo"] == "Python Backend Developer"
    assert offers[0]["fuente"] == "InfoJobs"
    assert captured["params"]["q"] == "python"
    assert captured["params"]["province"] == "Madrid"
    assert captured["params"]["teleworking"] == "Remoto"
    assert captured["headers"]["Authorization"].startswith("Basic ")


def test_indeed_devuelve_estructura_valida_con_mock(monkeypatch):
    class FakeResponse:
        status_code = 403
        text = ""

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("app.scraper.indeed.requests.get", fake_get)

    offers = fetch_indeed_offers(query="python", limit=2)

    assert_valid_offer_structure(offers)
    assert offers[0]["fuente"] == "Indeed"
    assert len(offers) <= 2

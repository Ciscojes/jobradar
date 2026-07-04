from app.scraper.adzuna import fetch_adzuna_offers, get_adzuna_config, search_adzuna_offers
from app.scraper.indeed import fetch_indeed_offers


REQUIRED_OFFER_FIELDS = {"titulo", "empresa", "ubicacion", "enlace", "fuente"}


def assert_valid_offer_structure(offers):
    assert isinstance(offers, list)
    assert offers

    offer = offers[0]
    assert REQUIRED_OFFER_FIELDS.issubset(offer.keys())

    for field in REQUIRED_OFFER_FIELDS:
        assert isinstance(offer[field], str)
        assert offer[field]


def test_adzuna_devuelve_estructura_valida_sin_llamada_real(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)

    offers = fetch_adzuna_offers(query="python", limit=2)

    assert_valid_offer_structure(offers)
    assert offers[0]["fuente"] == "Adzuna"
    assert len(offers) <= 2


def test_adzuna_lee_configuracion_desde_entorno(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "app-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "app-key")
    monkeypatch.setenv("ADZUNA_COUNTRY", "es")

    config = get_adzuna_config()

    assert config.app_id == "app-id"
    assert config.app_key == "app-key"
    assert config.country == "es"
    assert config.has_credentials is True


def test_adzuna_busqueda_con_credenciales_usa_requests_mock(monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "app-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "app-key")
    monkeypatch.setenv("ADZUNA_COUNTRY", "es")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [
                    {
                        "title": "Python Backend Developer",
                        "company": {"display_name": "JobRadar Labs"},
                        "location": {"display_name": "Madrid"},
                        "salary_min": 30000,
                        "salary_max": 40000,
                        "contract_time": "full_time",
                        "description": "APIs con FastAPI.",
                        "redirect_url": "https://www.adzuna.es/details/python-backend-test",
                        "created": "2026-06-30T10:00:00Z",
                    }
                ]
            }

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.scraper.adzuna.requests.get", fake_get)

    offers = search_adzuna_offers(
        keyword="python",
        provincia="Madrid",
        limit=1,
    )

    assert_valid_offer_structure(offers)
    assert offers[0]["titulo"] == "Python Backend Developer"
    assert offers[0]["fuente"] == "Adzuna"
    assert captured["params"]["what"] == "python"
    assert captured["params"]["where"] == "Madrid"
    assert captured["params"]["app_id"] == "app-id"
    assert captured["params"]["app_key"] == "app-key"
    assert "/es/search/1" in captured["url"]


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

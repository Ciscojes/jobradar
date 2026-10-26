import asyncio
import sys
import json
from threading import Event
from types import SimpleNamespace

import pytest

from app import tracing
from scripts.evaluate_matching import evaluate_offline, main as evaluate_main


@pytest.fixture(autouse=True)
def reset_tracing(monkeypatch):
    monkeypatch.delenv("JOBRADAR_LANGSMITH_ENABLED", raising=False)
    monkeypatch.delenv("JOBRADAR_LANGSMITH_SAMPLE_RATE", raising=False)
    tracing._client.cache_clear()
    yield
    tracing._client.cache_clear()


def fake_sdk(monkeypatch, fail=None):
    records = []

    class Run:
        def __init__(self, **kwargs):
            self.data = kwargs
            records.append(self)

        def create_child(self, **kwargs):
            child = Run(**kwargs)
            child.parent = self
            return child

        def post(self):
            if fail == "post":
                raise RuntimeError("secret-in-sdk-error")

        def end(self, **kwargs):
            self.data.update(kwargs)

        def patch(self):
            if fail == "patch":
                raise RuntimeError("secret-in-sdk-error")

    class Client:
        def __init__(self, **kwargs):
            if fail == "client":
                raise RuntimeError("secret-in-sdk-error")
            self.options = kwargs

        def flush(self):
            if fail == "flush":
                raise RuntimeError("secret-in-sdk-error")

    monkeypatch.setitem(sys.modules, "langsmith", SimpleNamespace(Client=Client))
    monkeypatch.setitem(sys.modules, "langsmith.run_trees", SimpleNamespace(RunTree=Run))
    monkeypatch.setenv("JOBRADAR_LANGSMITH_ENABLED", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "synthetic-key")
    return records


def test_disabled_ignores_sdk_environment(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setitem(sys.modules, "langsmith", None)
    with tracing.span("test.operation"):
        assert tracing._client() is None


def test_missing_key_is_noop(monkeypatch):
    monkeypatch.setenv("JOBRADAR_LANGSMITH_ENABLED", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert tracing._client() is None


def test_nested_spans_capture_no_sensitive_arguments_or_results(monkeypatch):
    records = fake_sdk(monkeypatch)

    @tracing.traced("test.child")
    def operation(credentials):
        return {"email": "private@example.invalid", "token": credentials}

    with tracing.span("test.root"):
        assert operation("private-token")["token"] == "private-token"
    assert records[1].parent is records[0]
    for run in records:
        assert run.data["inputs"] == run.data["outputs"] == {}
        assert run.data["error"] is None
    assert tracing._client().options["hide_inputs"] is True
    assert tracing._client().options["hide_outputs"] is True
    assert tracing._client().options["hide_metadata"] is True
    assert tracing._parent.get() is None


def test_exception_is_preserved_and_redacted(monkeypatch):
    records = fake_sdk(monkeypatch)
    error = ValueError("password=secret; email=private@example.invalid")
    with pytest.raises(ValueError) as caught, tracing.span("test.failure"):
        raise error
    assert caught.value is error
    assert records[0].data["error"] == "operation_failed"
    assert tracing._parent.get() is None


@pytest.mark.parametrize("failure", ["client", "post", "patch"])
def test_sdk_failures_do_not_change_business_result(monkeypatch, caplog, failure):
    fake_sdk(monkeypatch, failure)
    with tracing.span("test.operation"):
        result = 42
    assert result == 42
    assert "secret-in-sdk-error" not in caplog.text


@pytest.mark.parametrize("rate", ["0", "invalid", "-1", "2", "nan"])
def test_sampling_disables_whole_tree(monkeypatch, rate):
    records = fake_sdk(monkeypatch)
    monkeypatch.setenv("JOBRADAR_LANGSMITH_SAMPLE_RATE", rate)
    with tracing.span("test.root"), tracing.span("test.child"):
        pass
    assert records == []


def test_concurrent_requests_have_independent_roots(monkeypatch):
    records = fake_sdk(monkeypatch)

    async def request():
        with tracing.span("test.request"):
            await asyncio.sleep(0)
            with tracing.span("test.child"):
                pass

    async def run():
        await asyncio.gather(request(), request())

    asyncio.run(run())
    assert records[2].parent is records[0]
    assert records[3].parent is records[1]
    assert tracing._parent.get() is None


def test_synthetic_matching_evaluation():
    assert evaluate_offline() == {"passed": 7, "total": 7, "accuracy": 1.0}


def test_upload_requires_separate_opt_in(monkeypatch):
    monkeypatch.setenv("JOBRADAR_LANGSMITH_EVALUATIONS_ENABLED", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "synthetic-key")
    monkeypatch.setattr(sys, "argv", ["evaluate_matching", "--upload"])
    monkeypatch.setitem(sys.modules, "langsmith", None)
    with pytest.raises(SystemExit) as error:
        evaluate_main()
    assert error.value.code == 2


def test_api_request_does_not_capture_url_query_or_headers(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    records = fake_sdk(monkeypatch)
    with TestClient(app) as client:
        response = client.get(
            "/health/live?email=private@example.invalid",
            headers={"Authorization": "Bearer private-token"},
        )
    assert response.status_code == 200
    assert len(records) == 1
    assert records[0].data["name"] == "api.request"
    assert records[0].data["inputs"] == records[0].data["outputs"] == {}


def test_real_sdk_drops_environment_metadata_before_transport(monkeypatch):
    sdk = pytest.importorskip("langsmith")
    captured = []
    updates = []
    # Capture after SDK transformations, before any network / background queue.
    monkeypatch.setattr(sdk.Client, "_create_run", lambda self, run, **kwargs: captured.append(run))
    monkeypatch.setattr(sdk.Client, "update_run", lambda self, *args, **kwargs: updates.append(kwargs))
    monkeypatch.setenv("JOBRADAR_LANGSMITH_ENABLED", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "synthetic-key")
    monkeypatch.setenv("LANGSMITH_PRIVATE_EMAIL", "private@example.invalid")
    # The SDK rejects endpoint + replicas during construction, before our
    # RunTree can explicitly disable replicas. Exercise serialization separately.
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)
    monkeypatch.delenv("LANGCHAIN_ENDPOINT", raising=False)
    monkeypatch.setenv("LANGSMITH_RUNS_ENDPOINTS", json.dumps([{
        "api_url": "https://replica.example.invalid", "api_key": "replica-token", "updates": {
            "inputs": {"password": "private-password"}, "error": "private-error"}
    }]))

    @tracing.traced("test.real_sdk_child")
    def operation(data):
        return data

    sensitive = {
        "password": "private-password", "token": "private-token", "cookie": "private-cookie",
        "email": "private@example.invalid", "cv": "private-cv", "name": "private-person",
    }
    with pytest.raises(ValueError), tracing.span("test.real_sdk"):
        assert operation(sensitive) is sensitive
        raise ValueError("private-error")
    assert len(captured) == 2
    assert captured[1]["parent_run_id"] == captured[0]["id"]
    for payload in captured:
        assert payload["inputs"] == {}
        assert payload["extra"] == {"metadata": {}, "runtime": {"sdk": "langsmith-py"}}
    assert updates[-1]["error"] == "operation_failed"
    serialized = json.dumps([captured, updates], default=str)
    for secret in [*sensitive.values(), "private-error", "replica-token"]:
        assert secret not in serialized


def test_conflicting_sdk_endpoints_fail_closed(monkeypatch):
    sdk = pytest.importorskip("langsmith")
    sent = []
    monkeypatch.setattr(sdk.Client, "_create_run", lambda *args, **kwargs: sent.append(kwargs))
    monkeypatch.setenv("JOBRADAR_LANGSMITH_ENABLED", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "synthetic-key")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    monkeypatch.setenv("LANGSMITH_RUNS_ENDPOINTS", '{"https://replica.example.invalid":"fake"}')
    with tracing.span("test.conflicting_configuration"):
        result = 42
    assert result == 42
    assert tracing._client() is None
    assert sent == []


@pytest.mark.parametrize("failure", ["client", "post", "patch", "flush"])
def test_api_and_worker_survive_sdk_failures(monkeypatch, failure):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.worker import run_worker

    fake_sdk(monkeypatch, failure)
    warnings = []
    monkeypatch.setattr(tracing.logger, "warning", warnings.append)
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
    calls = []

    def start():
        with tracing.span("test.worker_operation"):
            calls.append("start")

    scheduler = SimpleNamespace(start=start, shutdown=lambda: calls.append("shutdown"))
    run_worker(scheduler=scheduler, shutdown_event=SimpleNamespace(wait=lambda: None))
    assert calls == ["start", "shutdown"]
    assert warnings
    assert "secret-in-sdk-error" not in " ".join(warnings)


def test_flush_timeout_does_not_hold_worker_shutdown(monkeypatch):
    entered = Event()
    release = Event()

    def blocked_flush():
        entered.set()
        release.wait()

    fake_sdk(monkeypatch)
    warnings = []
    monkeypatch.setattr(tracing.logger, "warning", warnings.append)
    monkeypatch.setattr(tracing._client(), "flush", blocked_flush)
    monkeypatch.setattr(tracing, "_FLUSH_TIMEOUT_SECONDS", 0.01)
    try:
        tracing.flush_traces()
        assert entered.is_set()
        assert not release.is_set()
        assert "langsmith_flush_timeout" in warnings
    finally:
        release.set()

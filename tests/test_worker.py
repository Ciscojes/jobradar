from importlib import import_module

from fastapi.testclient import TestClient

from app.main import app


class FakeScheduler:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("start")

    def shutdown(self) -> None:
        self.calls.append("shutdown")


class FakeShutdownEvent:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def wait(self) -> None:
        self.calls.append("wait")


def test_worker_mantiene_scheduler_activo_hasta_recibir_parada():
    worker = import_module("app.worker")
    scheduler = FakeScheduler()
    shutdown_event = FakeShutdownEvent(scheduler.calls)

    worker.run_worker(scheduler=scheduler, shutdown_event=shutdown_event)

    assert scheduler.calls == ["start", "wait", "shutdown"]


def test_api_no_inicia_scheduler_embebido(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.scheduler.scheduler_service.start", lambda: calls.append("start")
    )
    monkeypatch.setattr(
        "app.services.scheduler.scheduler_service.shutdown", lambda: calls.append("shutdown")
    )

    with TestClient(app):
        pass

    assert calls == []


class FakeApscheduler:
    def __init__(self) -> None:
        self.running = False
        self.job_ids = []

    def add_job(self, function, trigger, **kwargs) -> None:
        self.job_ids.append(kwargs["id"])

    def start(self) -> None:
        self.running = True


def test_worker_procesa_colas_aunque_scraper_periodico_este_desactivado(monkeypatch):
    scheduler_module = import_module("app.services.scheduler")
    apscheduler = FakeApscheduler()
    service = scheduler_module.JobRadarScheduler()
    service.scheduler = apscheduler
    monkeypatch.setenv("SCRAPER_SCHEDULER_ENABLED", "false")

    service.start()

    assert apscheduler.running is True
    assert apscheduler.job_ids == [scheduler_module.MAINTENANCE_JOB_ID]

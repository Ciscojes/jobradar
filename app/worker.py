from threading import Event

from .observability import configure_logging
from .services.scheduler import JobRadarScheduler, scheduler_service


def run_worker(
    scheduler: JobRadarScheduler = scheduler_service,
    shutdown_event: Event | None = None,
) -> None:
    configure_logging()
    event = shutdown_event or Event()
    scheduler.start()
    try:
        event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()


def main() -> None:
    run_worker()


if __name__ == "__main__":
    main()

"""Opt-in LangSmith spans: never serialize application data or exceptions."""

import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache, wraps
from random import random
from threading import Thread


logger = logging.getLogger(__name__)
_parent = ContextVar("jobradar_langsmith_parent", default=None)
_FLUSH_TIMEOUT_SECONDS = 2.0


@lru_cache(maxsize=1)
def _client():
    # Deliberately independent of LANGSMITH_TRACING / LANGCHAIN_TRACING_V2.
    if os.getenv("JOBRADAR_LANGSMITH_ENABLED", "false").lower() != "true":
        return None
    if not os.getenv("LANGSMITH_API_KEY"):
        logger.warning("langsmith_missing_api_key")
        return None
    try:
        from langsmith import Client

        class PrivateClient(Client):
            @staticmethod
            def _insert_runtime_env(runs):
                # SDK 0.4.58 inserts env metadata AFTER hide_metadata is applied.
                # Keep this adapter pinned and covered by the real-SDK test.
                for run in runs:
                    run["extra"] = {"metadata": {}, "runtime": {"sdk": "langsmith-py"}}

        return PrivateClient(
            api_key=os.environ["LANGSMITH_API_KEY"],
            api_url=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
            hide_inputs=True,
            hide_outputs=True,
            hide_metadata=True,
            tracing_sampling_rate=1,
            timeout_ms=1000,
        )
    except Exception:
        # No exception text: SDK errors can include credentials / endpoints.
        logger.warning("langsmith_client_unavailable")
        return None


@contextmanager
def span(name: str):
    """Only pass static, developer-owned names. SDK failures are fail-open."""
    parent = _parent.get()
    client = _client()
    run = None
    if client is not None:
        try:
            rate = float(os.getenv("JOBRADAR_LANGSMITH_SAMPLE_RATE", "1"))
            if not 0 <= rate <= 1:
                raise ValueError("invalid sample rate")
            # Children inherit sampling; a sampled-out root disables descendants.
            if parent is not False and (parent is not None or random() < rate):
                from langsmith.run_trees import RunTree

                if parent is not None:
                    run = parent.create_child(name=name, run_type="chain", inputs={})
                else:
                    run = RunTree(
                        name=name,
                        run_type="chain",
                        inputs={},
                        project_name=os.getenv("LANGSMITH_PROJECT", "jobradar"),
                        client=client,
                        replicas=[],
                    )
                run.post()
        except Exception:
            run = None
            logger.warning("langsmith_span_unavailable")
    token = _parent.set(run if run is not None else False)
    failed = False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        _parent.reset(token)
        if run is not None:
            try:
                run.end(outputs={}, error="operation_failed" if failed else None)
                run.patch()
            except Exception:
                logger.warning("langsmith_span_finish_failed")


def traced(name: str):
    """Trace synchronous business operations without capturing args or results."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def flush_traces() -> None:
    """Best-effort shutdown flush; SDK queue.join() has no timeout of its own."""
    client = _client()
    if client is not None:
        def flush():
            try:
                client.flush()
            except Exception:
                logger.warning("langsmith_flush_failed")

        try:
            thread = Thread(target=flush, daemon=True, name="jobradar-langsmith-flush")
            thread.start()
            thread.join(timeout=_FLUSH_TIMEOUT_SECONDS)
            if thread.is_alive():
                logger.warning("langsmith_flush_timeout")
        except Exception:
            logger.warning("langsmith_flush_unavailable")

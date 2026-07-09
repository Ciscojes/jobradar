import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def request_json(url: str, token: str | None = None, timeout: int = 10) -> tuple[int, dict]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        return response.status, json.loads(payload) if payload else {}


def request_text(url: str, timeout: int = 10) -> int:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        response.read()
        return response.status


def post_json(url: str, payload: dict, timeout: int = 10) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def wait_for(name: str, callback, attempts: int, delay: float) -> None:
    last_error = None
    for _ in range(attempts):
        try:
            callback()
            print(f"ok: {name}")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"{name} no respondió: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test para JobRadar desplegado.")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--dashboard-url", default="http://localhost:8501")
    parser.add_argument("--email", default="smoke@example.com")
    parser.add_argument("--password", default="smoke-password")
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=2)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    dashboard_url = args.dashboard_url.rstrip("/")

    try:
        wait_for(
            "api health",
            lambda: request_json(f"{api_url}/health"),
            args.attempts,
            args.delay,
        )
        wait_for(
            "dashboard",
            lambda: request_text(dashboard_url),
            args.attempts,
            args.delay,
        )

        try:
            post_json(
                f"{api_url}/auth/register",
                {
                    "email": args.email,
                    "password": args.password,
                    "nombre": "Smoke Test",
                },
            )
            print("ok: registro smoke")
        except urllib.error.HTTPError as exc:
            if exc.code != 400:
                raise
            print("ok: usuario smoke ya existe")

        _, token_payload = post_json(
            f"{api_url}/auth/login",
            {"email": args.email, "password": args.password},
        )
        token = token_payload["access_token"]
        print("ok: login smoke")

        request_json(f"{api_url}/auth/me", token=token)
        print("ok: auth/me")

        request_json(f"{api_url}/notificaciones/canales", token=token)
        print("ok: notificaciones/canales")

        request_json(f"{api_url}/scheduler/status", token=token)
        print("ok: scheduler/status")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

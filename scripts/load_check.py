import argparse
import concurrent.futures
import statistics
import time
import urllib.request


def request_once(url: str, timeout: float) -> tuple[bool, float]:
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
            ok = response.status < 500
    except Exception:
        ok = False
    return ok, (time.perf_counter() - started_at) * 1000


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0
    position = min(int(len(values) * fraction), len(values) - 1)
    return sorted(values)[position]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de carga HTTP acotada para staging.")
    parser.add_argument("--url", default="http://localhost:8000/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=1000)
    args = parser.parse_args()

    if args.requests < 1 or args.concurrency < 1:
        parser.error("requests y concurrency deben ser positivos")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(
            executor.map(
                lambda _: request_once(args.url, args.timeout),
                range(args.requests),
            )
        )

    latencies = [latency for _, latency in results]
    failures = sum(not ok for ok, _ in results)
    p95 = percentile(latencies, 0.95)
    print(
        f"requests={len(results)} failures={failures} "
        f"median_ms={statistics.median(latencies):.2f} p95_ms={p95:.2f}"
    )
    return 1 if failures or p95 > args.max_p95_ms else 0


if __name__ == "__main__":
    raise SystemExit(main())

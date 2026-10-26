"""Synthetic alert-matching regression evaluation; offline unless --upload is set."""

import argparse
import json
import os
from types import SimpleNamespace

from app.services.ingestion import offer_matches_alert


CASES = [
    ({"titulo": "PYTHON developer", "ubicacion": "Madrid", "modalidad": "Remoto"},
     {"termino": "python", "ubicacion": "Madrid", "modalidad": "Remoto", "activo": True}, True),
    ({"titulo": "Java developer"},
     {"termino": "python", "activo": True}, False),
    ({"title": "Python engineer", "location": "Barcelona"},
     {"termino": "python", "ubicacion": "Madrid", "activo": True}, False),
    ({"title": "Python engineer", "modalidad": "Presencial"},
     {"termino": "python", "modalidad": "Remoto", "activo": True}, False),
    ({"descripcion": "Python automation"},
     {"termino": "python", "activo": True}, True),
    ({"title": "Python engineer"},
     {"termino": "python", "activo": False}, False),
    ({"company": "Synthetic Python company"},
     {"termino": "python", "ubicacion": "Cualquiera", "activo": True}, True),
]


def predict(inputs):
    alert = {"ubicacion": None, "modalidad": None, **inputs["alert"]}
    return {"match": offer_matches_alert(inputs["offer"], SimpleNamespace(**alert))}


def accuracy(outputs, reference_outputs):
    return {"key": "matching_accuracy", "score": outputs["match"] == reference_outputs["match"]}


def evaluate_offline():
    passed = sum(
        predict({"offer": offer, "alert": alert})["match"] == expected
        for offer, alert, expected in CASES
    )
    return {"passed": passed, "total": len(CASES), "accuracy": passed / len(CASES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="Upload synthetic data to LangSmith")
    args = parser.parse_args()
    result = evaluate_offline()
    print(json.dumps(result))
    if result["passed"] != result["total"]:
        raise SystemExit(1)
    if args.upload:
        if os.getenv("JOBRADAR_LANGSMITH_EVALUATIONS_ENABLED", "false").lower() != "true":
            parser.error("--upload requires JOBRADAR_LANGSMITH_EVALUATIONS_ENABLED=true")
        if not os.getenv("LANGSMITH_API_KEY"):
            parser.error("--upload requires LANGSMITH_API_KEY")
        from langsmith import Client
        from uuid import uuid4

        client = Client()
        dataset = client.create_dataset(f"jobradar-synthetic-matching-{uuid4().hex}")
        client.create_examples(
            inputs=[{"offer": offer, "alert": alert} for offer, alert, _ in CASES],
            outputs=[{"match": expected} for _, _, expected in CASES],
            dataset_id=dataset.id,
        )
        results = client.evaluate(
            predict, data=dataset.name, evaluators=[accuracy],
            experiment_prefix="jobradar-matching", max_concurrency=1,
        )
        results.wait()
        client.flush()


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from research_command_center_sdk import ResearchCommandCenterClient
    from scripts.run_study_material_full_lifecycle import (
        failures_for_scores,
        generate_study_guide,
        rubric_scores,
    )

    args = parse_args()
    client = ResearchCommandCenterClient(
        base_url=args.api_base_url,
        timeout_seconds=args.timeout_seconds,
    )
    suite = client.get_eval_suite(args.eval_suite_id) if args.eval_suite_id else latest_eval_suite(client)
    model = client.get_model(args.model_version_id) if args.model_version_id else latest_model_version(client)

    outputs = []
    for case in suite["cases"]:
        output_text = generate_study_guide(
            variant_name=args.variant,
            prompt=case["prompt_text"],
            expected_topics=case["expected_topics"],
        )
        scores = rubric_scores(
            text=output_text,
            expected_topics=case["expected_topics"],
            required_sections=case["required_sections"],
        )
        outputs.append(
            {
                "eval_case_id": case["eval_case_id"],
                "prompt_text": case["prompt_text"],
                "output_text": output_text,
                "score": scores["overall"],
                "scores": scores,
                "scoring_method": "study_guide_rubric_v1",
                "failures": failures_for_scores(scores=scores, output_text=output_text),
            }
        )

    now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    external_eval_run_id = args.external_eval_run_id or (
        f"sdk-sample-{model['model_version_id']}-{suite['eval_suite_id']}-{args.variant}-{now}"
    )
    result = client.submit_eval_run(
        eval_suite_id=suite["eval_suite_id"],
        model_version_id=model["model_version_id"],
        program_id=suite.get("program_id") or model.get("program_id"),
        experiment_id=suite.get("experiment_id") or model.get("experiment_id"),
        outputs=outputs,
        scoring_method="study_guide_rubric_v1",
        evaluator_name="sdk_sample_eval",
        evaluator_version="v1",
        eval_job_uri="scripts/run_sdk_sample_eval.py",
        external_eval_run_id=external_eval_run_id,
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "variant": args.variant,
        },
        notes="SDK-first sample eval submission using the existing study-guide sample suite.",
        created_by_user_id=args.created_by_user_id,
    )
    print(
        "created eval_run_id={eval_run_id} model_version_id={model_version_id} "
        "outputs={output_count} failures={failure_count} external_eval_run_id={external_eval_run_id}".format(
            **result,
            external_eval_run_id=external_eval_run_id,
        )
    )


def latest_eval_suite(client: Any) -> dict[str, Any]:
    response = client.list_eval_suites(limit=200)
    items = response.get("items") or []
    if not items:
        raise SystemExit("No eval suites found. Create one with client.create_eval_suite first.")
    latest = max(items, key=lambda item: int(item["eval_suite_id"]))
    return client.get_eval_suite(latest["eval_suite_id"])


def latest_model_version(client: Any) -> dict[str, Any]:
    response = client.list_models()
    items = response.get("items") or []
    if not items:
        raise SystemExit("No model versions found. Register a checkpoint as a model version first.")
    latest = max(items, key=lambda item: int(item["model_version_id"]))
    return client.get_model(latest["model_version_id"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit an SDK-first sample eval run against existing local sample data.",
    )
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--eval-suite-id", type=int)
    parser.add_argument("--model-version-id", type=int)
    parser.add_argument(
        "--variant",
        default="outline_first_with_failure_corrections",
        choices=["control", "outline_first", "outline_first_with_failure_corrections"],
    )
    parser.add_argument("--external-eval-run-id")
    parser.add_argument("--created-by-user-id", default="Lena Keys")
    return parser.parse_args()


if __name__ == "__main__":
    main()

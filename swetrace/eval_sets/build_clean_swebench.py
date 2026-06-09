import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import typer

DEFAULT_SWEBENCH_TEST = Path(
    "/data/yiyuldx/swe/cache/swebench_lite/data/test-00000-of-00001.parquet"
)
DEFAULT_TRAINING_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/v0.2")
DEFAULT_OUT = Path("/data/yiyuldx/swe/eval_sets/qwen_baseline_v0")

app = typer.Typer(add_completion=False)


def build_clean_swebench_eval_set(
    *,
    swebench: Path = DEFAULT_SWEBENCH_TEST,
    training_dataset: Path = DEFAULT_TRAINING_DATASET,
    out: Path = DEFAULT_OUT,
    limit: int = 20,
    seed: int = 20260609,
    version: str = "qwen-baseline-v0",
) -> dict[str, Any]:
    df = pd.read_parquet(swebench)
    used_task_ids = _dataset_task_ids(training_dataset)
    clean_rows = [
        _swebench_row_to_eval_task(row)
        for row in df.to_dict(orient="records")
        if str(row.get("instance_id") or "") not in used_task_ids
    ]
    if len(clean_rows) < limit:
        raise ValueError(
            f"Not enough clean SWE-bench tasks: requested {limit}, available {len(clean_rows)}"
        )

    rng = random.Random(seed)
    selected = rng.sample(clean_rows, limit)
    selected.sort(key=lambda row: row["instance_id"])

    out.mkdir(parents=True, exist_ok=True)
    tasks_path = out / "tasks.jsonl"
    _write_jsonl(tasks_path, selected)

    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "clean held-out eval set for Qwen base vs LoRA comparisons",
        "source": {
            "swebench": str(swebench),
            "split": "test",
            "total_rows": int(len(df)),
        },
        "filters": {
            "exclude_task_ids_seen_in_training_dataset": str(training_dataset),
            "selection": "deterministic random sample sorted by instance_id",
            "seed": seed,
            "limit": limit,
        },
        "counts": {
            "source_total": int(len(df)),
            "excluded_seen_in_training": int(len(used_task_ids & set(df["instance_id"].astype(str)))),
            "clean_pool": len(clean_rows),
            "selected": len(selected),
        },
        "selected_task_ids": [row["instance_id"] for row in selected],
        "files": {
            "tasks": str(tasks_path),
            "manifest": str(out / "manifest.json"),
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


@app.command()
def main(
    swebench: Path = typer.Option(DEFAULT_SWEBENCH_TEST, exists=True, readable=True),
    training_dataset: Path = typer.Option(DEFAULT_TRAINING_DATASET, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_OUT),
    limit: int = typer.Option(20, min=1),
    seed: int = typer.Option(20260609),
    version: str = typer.Option("qwen-baseline-v0"),
) -> None:
    typer.echo(
        json.dumps(
            build_clean_swebench_eval_set(
                swebench=swebench,
                training_dataset=training_dataset,
                out=out,
                limit=limit,
                seed=seed,
                version=version,
            ),
            ensure_ascii=False,
        )
    )


def _dataset_task_ids(dataset: Path) -> set[str]:
    task_ids: set[str] = set()
    for name in (
        "sft_patch.jsonl",
        "sft_plan.jsonl",
        "dpo_main.jsonl",
        "debug_cases.jsonl",
        "reward_logs.jsonl",
        "excluded.jsonl",
    ):
        path = dataset / name
        if not path.exists():
            continue
        for row in _read_jsonl(path):
            task_id = _row_task_id(row)
            if task_id:
                task_ids.add(task_id)
    return task_ids


def _row_task_id(row: dict[str, Any]) -> str | None:
    for value in (
        row.get("task_id"),
        row.get("instance_id"),
        row.get("meta", {}).get("task_id") if isinstance(row.get("meta"), dict) else None,
        row.get("meta", {}).get("instance_id") if isinstance(row.get("meta"), dict) else None,
    ):
        if isinstance(value, str) and value:
            return value
    return None


def _swebench_row_to_eval_task(row: dict[str, Any]) -> dict[str, Any]:
    instance_id = str(row["instance_id"])
    return {
        "instance_id": instance_id,
        "task_id": instance_id,
        "repo": str(row.get("repo") or ""),
        "base_commit": str(row.get("base_commit") or ""),
        "problem_statement": str(row.get("problem_statement") or ""),
        "gold_patch": str(row.get("patch") or ""),
        "test_patch": str(row.get("test_patch") or ""),
        "source": "SWE-bench_Lite",
        "split": "test",
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    app()

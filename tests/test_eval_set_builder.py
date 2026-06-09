import json
from pathlib import Path

import pandas as pd

from swetrace.eval_sets.build_clean_swebench import build_clean_swebench_eval_set


def test_build_clean_swebench_eval_set_excludes_training_tasks(tmp_path) -> None:
    swebench = tmp_path / "swebench.parquet"
    rows = []
    for index in range(5):
        rows.append(
            {
                "instance_id": f"repo__project-{index}",
                "repo": "repo/project",
                "base_commit": f"commit-{index}",
                "problem_statement": f"Fix issue {index}",
                "patch": f"gold patch {index}",
                "test_patch": f"test patch {index}",
            }
        )
    pd.DataFrame(rows).to_parquet(swebench)

    training = tmp_path / "datasets" / "v0.2"
    training.mkdir(parents=True)
    (training / "sft_patch.jsonl").write_text(
        json.dumps({"task_id": "repo__project-1"}) + "\n"
    )
    (training / "dpo_main.jsonl").write_text(
        json.dumps({"meta": {"task_id": "repo__project-3"}}) + "\n"
    )
    (training / "reward_logs.jsonl").write_text(
        json.dumps({"task_id": "repo__project-4"}) + "\n"
    )

    out = tmp_path / "eval_sets" / "qwen_baseline_v0"
    manifest = build_clean_swebench_eval_set(
        swebench=swebench,
        training_dataset=training,
        out=out,
        limit=2,
        seed=7,
        version="qwen-baseline-v0-test",
    )

    tasks = [json.loads(line) for line in (out / "tasks.jsonl").read_text().splitlines()]
    selected_ids = {row["instance_id"] for row in tasks}

    assert manifest["counts"]["selected"] == 2
    assert manifest["counts"]["excluded_seen_in_training"] == 3
    assert selected_ids <= {"repo__project-0", "repo__project-2"}
    assert manifest["version"] == "qwen-baseline-v0-test"
    assert manifest["files"]["tasks"].endswith("tasks.jsonl")


def test_build_clean_swebench_eval_set_fails_when_pool_is_too_small(tmp_path) -> None:
    swebench = tmp_path / "swebench.parquet"
    pd.DataFrame(
        [
            {
                "instance_id": "repo__project-1",
                "repo": "repo/project",
                "base_commit": "commit",
                "problem_statement": "Fix it",
                "patch": "gold",
                "test_patch": "tests",
            }
        ]
    ).to_parquet(swebench)
    training = tmp_path / "datasets" / "v0.2"
    training.mkdir(parents=True)
    (training / "sft_patch.jsonl").write_text("")

    try:
        build_clean_swebench_eval_set(
            swebench=swebench,
            training_dataset=training,
            out=tmp_path / "out",
            limit=2,
        )
    except ValueError as exc:
        assert "Not enough clean SWE-bench tasks" in str(exc)
    else:
        raise AssertionError("expected ValueError")

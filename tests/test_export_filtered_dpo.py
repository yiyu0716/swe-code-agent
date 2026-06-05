import json
import subprocess
import sys
from pathlib import Path

from swetrace.data_builder.export_filtered_dpo import export_filtered_dpo


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_run(
    runs: Path,
    run_id: str,
    task_id: str,
    *,
    gold_patch: str | None = "gold patch",
    agent_patch: str = "agent patch",
    resolved: bool = False,
    status: str = "failed",
) -> None:
    run_dir = runs / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "source": "swebench_lite",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": f"Fix {task_id}.",
                "test_command": "mini-swe-agent managed evaluation",
                "expected_files": ["src/file.py"],
                "gold_patch": gold_patch,
            }
        )
    )
    (run_dir / "patch.diff").write_text(agent_patch)
    (run_dir / "test.log").write_text("1 failed\n")
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task_id": task_id,
                "agent": "mini-swe-agent",
                "status": status,
                "patch_apply": True,
                "tests_passed": resolved,
                "resolved": resolved,
            }
        )
    )


def _annotation(
    run_id: str,
    task_id: str,
    *,
    patch_quality: str,
    sft_usable: bool = False,
    dpo_usable: bool = True,
) -> dict:
    return {
        "run_id": run_id,
        "task_id": task_id,
        "auto_primary_failure": "PatchError.IncompleteFix",
        "auto_severity": 3,
        "human_failure": "PatchError.IncompleteFix",
        "patch_quality": patch_quality,
        "sft_usable": sft_usable,
        "dpo_usable": dpo_usable,
        "notes": f"{patch_quality} note",
        "reviewer": "test",
    }


def test_export_filtered_dpo_splits_main_hard_negative_and_sft_sanity(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(runs, "close-run", "task-close", agent_patch="close agent")
    _write_run(runs, "partial-run", "task-partial", agent_patch="partial agent")
    _write_run(runs, "poor-run", "task-poor", agent_patch="poor agent")
    _write_run(runs, "env-run", "task-env", agent_patch="", status="env_error")
    _write_run(
        runs,
        "sft-run",
        "task-sft",
        gold_patch=None,
        agent_patch="resolved patch",
        resolved=True,
        status="resolved",
    )
    annotations = tmp_path / "manual_annotations.jsonl"
    annotations.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                _annotation("close-run", "task-close", patch_quality="close"),
                _annotation("partial-run", "task-partial", patch_quality="partial"),
                _annotation("poor-run", "task-poor", patch_quality="poor"),
                _annotation("env-run", "task-env", patch_quality="env_only", dpo_usable=False),
                _annotation(
                    "sft-run",
                    "task-sft",
                    patch_quality="close",
                    sft_usable=True,
                    dpo_usable=False,
                ),
            ]
        )
        + "\n"
    )

    summary = export_filtered_dpo(
        annotations=annotations,
        runs=runs,
        out=tmp_path / "datasets" / "v0.1",
        version="v0.1-test",
    )

    assert summary["dpo_main"] == 2
    assert summary["dpo_hard_negative"] == 1
    assert summary["sft_sanity"] == 1
    assert summary["excluded"] == 1
    main_rows = [
        json.loads(line)
        for line in (tmp_path / "datasets" / "v0.1" / "dpo_main.jsonl").read_text().splitlines()
    ]
    hard_rows = [
        json.loads(line)
        for line in (
            tmp_path / "datasets" / "v0.1" / "dpo_hard_negative.jsonl"
        ).read_text().splitlines()
    ]
    sft_rows = [
        json.loads(line)
        for line in (tmp_path / "datasets" / "v0.1" / "sft_sanity.jsonl").read_text().splitlines()
    ]
    manifest = json.loads((tmp_path / "datasets" / "v0.1" / "manifest.json").read_text())

    assert {row["meta"]["patch_quality"] for row in main_rows} == {"close", "partial"}
    assert hard_rows[0]["meta"]["patch_quality"] == "poor"
    assert main_rows[0]["chosen"] == "gold patch"
    assert main_rows[0]["rejected"] in {"close agent", "partial agent"}
    assert sft_rows[0]["output"] == "resolved patch"
    assert manifest["version"] == "v0.1-test"
    assert manifest["counts"]["dpo_main"] == 2


def test_export_filtered_dpo_cli_writes_versioned_files(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(runs, "close-run", "task-close", agent_patch="close agent")
    annotations = tmp_path / "manual_annotations.jsonl"
    annotations.write_text(
        json.dumps(_annotation("close-run", "task-close", patch_quality="close")) + "\n"
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.data_builder.export_filtered_dpo",
            "--annotations",
            str(annotations),
            "--runs",
            str(runs),
            "--out",
            str(tmp_path / "datasets" / "v0.1"),
            "--version",
            "v0.1-cli",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["dpo_main"] == 1
    assert (tmp_path / "datasets" / "v0.1" / "dpo_main.jsonl").exists()
    assert (tmp_path / "datasets" / "v0.1" / "manifest.json").exists()

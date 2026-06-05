import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(add_completion=False)


@dataclass(frozen=True)
class PredictionRow:
    run_id: str
    task_id: str
    prediction: dict[str, str]


@dataclass(frozen=True)
class PredictionShard:
    index: int
    rows: list[PredictionRow]


def write_local_dataset_json(dataset: Path, splits: list[str], out: Path) -> dict[str, str | int]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - exercised only on incomplete envs.
        raise typer.BadParameter("Reading SWE-bench parquet requires pandas/pyarrow.") from exc

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for split in splits:
        parquet_path = dataset / "data" / f"{split}-00000-of-00001.parquet"
        if not parquet_path.exists():
            raise typer.BadParameter(f"Missing SWE-bench parquet: {parquet_path}")
        frame = pd.read_parquet(parquet_path)
        for row in frame.to_dict(orient="records"):
            instance_id = str(row["instance_id"])
            if instance_id in seen:
                continue
            seen.add(instance_id)
            rows.append(_jsonable(row))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    return {"instances": len(rows), "out": str(out)}


def build_prediction_shards(
    runs: Path,
    model_prefix: str = "swetrace-mini-swe-agent-deepseek",
) -> list[PredictionShard]:
    shards: list[list[PredictionRow]] = []
    task_ids_by_shard: list[set[str]] = []
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        report_path = run_dir / "report.json"
        patch_path = run_dir / "patch.diff"
        if not report_path.exists() or not patch_path.exists():
            continue
        patch = patch_path.read_text(errors="replace")
        if not patch.strip():
            continue
        report = json.loads(report_path.read_text())
        task_id = str(report.get("task_id") or "")
        run_id = str(report.get("run_id") or run_dir.name)
        if not task_id or task_id.startswith("fake-"):
            continue
        row = PredictionRow(
            run_id=run_id,
            task_id=task_id,
            prediction={
                "instance_id": task_id,
                "model_name_or_path": f"{model_prefix}/{run_id}",
                "model_patch": patch,
            },
        )
        for index, task_ids in enumerate(task_ids_by_shard):
            if task_id in task_ids:
                continue
            shards[index].append(row)
            task_ids.add(task_id)
            break
        else:
            shards.append([row])
            task_ids_by_shard.append({task_id})
    return [PredictionShard(index=index, rows=rows) for index, rows in enumerate(shards)]


def write_prediction_shards(
    runs: Path,
    out_dir: Path,
    model_prefix: str = "swetrace-mini-swe-agent-deepseek",
    official_run_prefix: str = "swetrace_official",
) -> dict[str, Any]:
    shards = build_prediction_shards(runs, model_prefix=model_prefix)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    prediction_paths: list[str] = []
    for shard in shards:
        path = out_dir / f"shard_{shard.index:02d}.jsonl"
        prediction_paths.append(str(path))
        with path.open("w") as fh:
            for row in shard.rows:
                fh.write(json.dumps(row.prediction, ensure_ascii=False) + "\n")
                manifest_rows.append(
                    {
                        "run_id": row.run_id,
                        "task_id": row.task_id,
                        "model_name_or_path": row.prediction["model_name_or_path"],
                        "prediction_path": str(path),
                        "shard": shard.index,
                    }
                )
    manifest = {
        "official_run_prefix": official_run_prefix,
        "model_prefix": model_prefix,
        "runs": len(manifest_rows),
        "shards": len(shards),
        "prediction_paths": prediction_paths,
        "rows": manifest_rows,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {k: manifest[k] for k in ("runs", "shards", "prediction_paths")}


def official_image_for_instance(instance_id: str, tag: str = "latest") -> str:
    image_instance = instance_id.replace("__", "_1776_").lower()
    return f"swebench/sweb.eval.x86_64.{image_instance}:{tag}"


def mirror_proxy_dockerfile(
    source_image: str,
    http_proxy: str,
    pip_index_url: str,
    pip_trusted_host: str,
) -> str:
    pip_conf = (
        "[global]\n"
        f"index-url = {pip_index_url}\n"
        f"trusted-host = {pip_trusted_host}\n"
        "timeout = 120\n"
        "retries = 8\n"
    )
    return "\n".join(
        [
            f"FROM {source_image}",
            f"ENV HTTP_PROXY={http_proxy}",
            f"ENV HTTPS_PROXY={http_proxy}",
            f"ENV http_proxy={http_proxy}",
            f"ENV https_proxy={http_proxy}",
            "ENV NO_PROXY=localhost,127.0.0.1,::1",
            "ENV no_proxy=localhost,127.0.0.1,::1",
            f"RUN printf {json.dumps(pip_conf)} > /etc/pip.conf",
            "",
        ]
    )


def pip_proxy_dockerfile(
    source_image: str,
    http_proxy: str,
    pip_index_url: str,
    pip_trusted_host: str,
) -> str:
    pip_conf = (
        "[global]\n"
        f"index-url = {pip_index_url}\n"
        f"trusted-host = {pip_trusted_host}\n"
        f"proxy = {http_proxy}\n"
        "timeout = 120\n"
        "retries = 8\n"
    )
    return "\n".join(
        [
            f"FROM {source_image}",
            f"RUN printf {json.dumps(pip_conf)} > /etc/pip.conf",
            "",
        ]
    )


def parse_official_report(official_root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    official_run_id = str(manifest["official_run_id"])
    rows = []
    for item in manifest.get("rows", []):
        task_id = str(item["task_id"])
        model_dir = str(item["model_name_or_path"]).replace("/", "__")
        report_path = (
            official_root
            / "logs"
            / "run_evaluation"
            / official_run_id
            / model_dir
            / task_id
            / "report.json"
        )
        if report_path.exists():
            report = json.loads(report_path.read_text()).get(task_id, {})
            tests_status = report.get("tests_status") or {}
            rows.append(
                {
                    "run_id": item["run_id"],
                    "task_id": task_id,
                    "official_run_id": official_run_id,
                    "completed": True,
                    "patch_exists": bool(report.get("patch_exists")),
                    "patch_successfully_applied": bool(report.get("patch_successfully_applied")),
                    "resolved": bool(report.get("resolved")),
                    "fail_to_pass_success": len(
                        ((tests_status.get("FAIL_TO_PASS") or {}).get("success") or [])
                    ),
                    "fail_to_pass_failure": len(
                        ((tests_status.get("FAIL_TO_PASS") or {}).get("failure") or [])
                    ),
                    "pass_to_pass_success": len(
                        ((tests_status.get("PASS_TO_PASS") or {}).get("success") or [])
                    ),
                    "pass_to_pass_failure": len(
                        ((tests_status.get("PASS_TO_PASS") or {}).get("failure") or [])
                    ),
                    "report_path": str(report_path),
                }
            )
        else:
            rows.append(
                {
                    "run_id": item["run_id"],
                    "task_id": task_id,
                    "official_run_id": official_run_id,
                    "completed": False,
                    "patch_exists": False,
                    "patch_successfully_applied": False,
                    "resolved": False,
                    "fail_to_pass_success": 0,
                    "fail_to_pass_failure": 0,
                    "pass_to_pass_success": 0,
                    "pass_to_pass_failure": 0,
                    "report_path": str(report_path),
                }
            )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def import_run_statuses(statuses: Path, runs: Path) -> dict[str, int]:
    rows = [json.loads(line) for line in statuses.read_text().splitlines() if line.strip()]
    written = 0
    missing = 0
    for row in rows:
        run_dir = runs / str(row["run_id"])
        if not run_dir.exists():
            missing += 1
            continue
        completed = bool(row.get("completed"))
        patch_applied = bool(row.get("patch_successfully_applied"))
        resolved = bool(row.get("resolved"))
        payload = {
            "source": "swebench_official",
            "run_id": row["run_id"],
            "task_id": row["task_id"],
            "official_run_id": row["official_run_id"],
            "completed": completed,
            "patch_exists": bool(row.get("patch_exists")),
            "patch_successfully_applied": patch_applied,
            "tests_passed": completed and patch_applied and resolved,
            "resolved": resolved,
            "fail_to_pass_success": int(row.get("fail_to_pass_success") or 0),
            "fail_to_pass_failure": int(row.get("fail_to_pass_failure") or 0),
            "pass_to_pass_success": int(row.get("pass_to_pass_success") or 0),
            "pass_to_pass_failure": int(row.get("pass_to_pass_failure") or 0),
            "report_path": row.get("report_path"),
        }
        (run_dir / "official_eval.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )
        written += 1
    return {"rows": len(rows), "written": written, "missing_runs": missing}


@app.command("write-dataset-json")
def write_dataset_json_command(
    dataset: Path = typer.Option(..., exists=True, file_okay=False, help="SWE-bench parquet root."),
    out: Path = typer.Option(..., help="Official harness JSON dataset path."),
    splits: list[str] = typer.Option(["dev", "test"], help="Parquet splits to combine."),
) -> None:
    typer.echo(json.dumps(write_local_dataset_json(dataset, splits, out), ensure_ascii=False))


@app.command("write-predictions")
def write_predictions_command(
    runs: Path = typer.Option(..., exists=True, file_okay=False, help="SWE-Trace runs root."),
    out_dir: Path = typer.Option(..., help="Prediction shard output directory."),
    model_prefix: str = typer.Option("swetrace-mini-swe-agent-deepseek", help="Model name prefix."),
    official_run_prefix: str = typer.Option("swetrace_official", help="Official run id prefix."),
) -> None:
    typer.echo(
        json.dumps(
            write_prediction_shards(
                runs=runs,
                out_dir=out_dir,
                model_prefix=model_prefix,
                official_run_prefix=official_run_prefix,
            ),
            ensure_ascii=False,
        )
    )


@app.command("build-pip-proxy-image")
@app.command("build-mirror-proxy-image")
def build_mirror_proxy_image_command(
    instance_id: str = typer.Option(..., help="SWE-bench instance id."),
    tag: str = typer.Option("pip-proxy", help="Target image tag."),
    http_proxy: str = typer.Option("http://10.32.192.70:7890", help="HTTP/HTTPS proxy."),
    pip_index_url: str = typer.Option(
        "https://pypi.tuna.tsinghua.edu.cn/simple", help="Pip index URL."
    ),
    pip_trusted_host: str = typer.Option("pypi.tuna.tsinghua.edu.cn", help="Pip trusted host."),
    work_dir: Path = typer.Option(
        Path("/data/yiyuldx/swe/tmp/swebench_image_mirror_proxy"),
        help="Temporary Docker build directory.",
    ),
    dry_run: bool = typer.Option(False, help="Write Dockerfile but do not build."),
) -> None:
    source = official_image_for_instance(instance_id)
    target = official_image_for_instance(instance_id, tag=tag)
    work_dir.mkdir(parents=True, exist_ok=True)
    dockerfile = work_dir / "Dockerfile"
    dockerfile.write_text(
        pip_proxy_dockerfile(
            source_image=source,
            http_proxy=http_proxy,
            pip_index_url=pip_index_url,
            pip_trusted_host=pip_trusted_host,
        )
    )
    if dry_run:
        returncode = None
        status = "planned"
    else:
        completed = subprocess.run(
            ["docker", "build", "-t", target, str(work_dir)],
            text=True,
            capture_output=True,
            check=False,
        )
        returncode = completed.returncode
        status = "built" if completed.returncode == 0 else "failed"
        if completed.returncode != 0:
            raise typer.Exit(completed.returncode)
    typer.echo(
        json.dumps(
            {
                "instance_id": instance_id,
                "source": source,
                "target": target,
                "status": status,
                "returncode": returncode,
                "dockerfile": str(dockerfile),
            },
            ensure_ascii=False,
        )
    )


@app.command("parse-reports")
def parse_reports_command(
    official_root: Path = typer.Option(..., exists=True, file_okay=False, help="Official eval root."),
    manifest: Path = typer.Option(..., exists=True, readable=True, help="Prediction manifest JSON."),
    official_run_id: str = typer.Option(..., help="Official harness run id."),
    out: Path = typer.Option(..., help="Output JSONL status path."),
) -> None:
    payload = json.loads(manifest.read_text())
    payload["official_run_id"] = official_run_id
    rows = parse_official_report(official_root, payload)
    write_jsonl(out, rows)
    typer.echo(
        json.dumps(
            {
                "rows": len(rows),
                "completed": sum(row["completed"] for row in rows),
                "resolved": sum(row["resolved"] for row in rows),
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )


@app.command("import-statuses")
def import_statuses_command(
    statuses: Path = typer.Option(..., exists=True, readable=True, help="Run status JSONL path."),
    runs: Path = typer.Option(..., exists=True, file_okay=False, help="SWE-Trace runs root."),
) -> None:
    typer.echo(json.dumps(import_run_statuses(statuses, runs), ensure_ascii=False))


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for key, value in row.items():
        if hasattr(value, "item"):
            value = value.item()
        output[key] = value
    return output


if __name__ == "__main__":
    app()

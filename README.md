# SWE-Trace

SWE-Trace is a two-week sprint project for Code Agent post-training data and evaluation.

The project focuses on collecting real Code Agent trajectories, diagnosing failure modes,
building SFT/DPO/RLVR-style datasets, and running small-scale post-training validation.

## Current MVP

The first runnable skeleton is in place:

- Pydantic schemas for tasks, trajectory steps, run reports, and failure labels.
- Run artifact storage under `runs/<run_id>/`.
- A `fake` adapter that produces replayable trajectory, patch, test log, and report files.
- Single-task and batch CLIs.
- Failure taxonomy helpers.
- SFT-plan, SFT-patch, SFT-debug, DPO pair, and reward-log builders.
- Evaluation summary metrics.

## Quickstart

Use the workspace environment:

```bash
cd /root/swe
/root/swe/.venv/bin/python -m pytest -q
```

Run one fake task:

```bash
./scripts/run_fake.sh
```

Run the fake batch and write `outputs/reports/summary.csv`:

```bash
./scripts/run_fake_batch.sh
```

Build JSONL datasets from run artifacts:

```bash
./scripts/build_fake_data.sh
```

Run a mini-SWE-agent smoke task after installing `mini-extra`:

```bash
./scripts/run_mini_smoke.sh
```

If `mini-extra` is not installed globally, the script falls back to:

```bash
uvx --from mini-swe-agent mini-extra
```

The real-agent adapter can also be driven directly with a command template:

```bash
/root/swe/.venv/bin/python -m swetrace.collect.run_task \
  --task examples/swebench_lite_task.json \
  --agent mini-swe-agent \
  --out runs \
  --command-template 'mini-extra swebench-single --instance {task_id} --model gpt-4.1-mini --output {traj_path} --exit-immediately'
```

The adapter passes `{traj_path}` as the mini-SWE-agent output file and also supports `{raw_dir}`
for custom wrappers. It then normalizes messages/tool calls into `trajectory.jsonl`, extracts
the final patch into `patch.diff`, stores test output in `test.log`, and writes `report.json`.

If Hugging Face dataset loading fails, cache SWE-bench Lite through the mirror:

```bash
./scripts/download_swebench_lite.sh
```

Then run a local-subset smoke:

```bash
SWETRACE_MINI_SUBSET=/root/swe/cache/swebench_lite \
SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 \
./scripts/run_mini_smoke.sh
```

Current smoke status: mini-SWE-agent 2.3.0 starts successfully through `uvx`. The Hugging Face
dataset access issue can be bypassed by downloading the parquet files through `hf-mirror.com`
and passing the local cache as `--subset`. The next external blocker is Docker image startup for
the SWE-bench evaluation container.

## Local Progress Report

The progress page is generated at:

```text
reports/progress.html
```

During active development it is served from the workspace with:

```bash
/root/swe/.venv/bin/python -m http.server 20038 --bind 0.0.0.0 -d /root/swe/reports
```

Open it from the local computer at:

```text
http://172.25.12.121:20038/
```

## Repository Policy

Do not commit local environments, run artifacts, PDFs, model checkpoints, or training logs.
Only source code, project docs, report templates, and reproducible configuration belong in git.

# SWE-Trace

SWE-Trace is a two-week sprint project for Code Agent post-training data and evaluation.

The project focuses on collecting real Code Agent trajectories, diagnosing failure modes,
building SFT/DPO/RLVR-style datasets, and running small-scale post-training validation.

## Current MVP

The first runnable skeleton is in place:

- Pydantic schemas for tasks, trajectory steps, run reports, and failure labels.
- Run artifact storage under `/data/yiyuldx/swe/runs/<run_id>/`.
- A `fake` adapter that produces replayable trajectory, patch, test log, and report files.
- Single-task and batch CLIs.
- Failure taxonomy helpers.
- SFT-plan, SFT-patch, SFT-debug, DPO pair, and reward-log builders.
- Gold-patch vs agent-patch DPO pair construction for SWE-bench tasks.
- Evaluation summary metrics.

## Quickstart

Use the workspace environment:

```bash
cd /home/yiyuldx/swe
/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Run one fake task:

```bash
./scripts/run_fake.sh
```

Run the fake batch and write `/data/yiyuldx/swe/outputs/reports/summary.csv`:

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
uvx --from mini-swe-agent --with socksio mini-extra
```

The real-agent adapter can also be driven directly with a command template:

```bash
/home/yiyuldx/birdNet/.venv/bin/python -m swetrace.collect.run_task \
  --task examples/swebench_lite_task.json \
  --agent mini-swe-agent \
  --out /data/yiyuldx/swe/runs \
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
SWETRACE_MINI_SUBSET=/data/yiyuldx/swe/cache/swebench_lite \
SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 \
./scripts/run_mini_smoke.sh
```

Current smoke status: mini-SWE-agent 2.3.0 starts successfully through `uvx` with `socksio`.
The Hugging Face dataset access issue is bypassed by downloading parquet files through
`hf-mirror.com` and passing the local cache as `--subset`. Docker is reachable through
`sg docker` in the current Codex process, and real sqlfluff/marshmallow SWE-bench Lite
trajectories have been collected with DeepSeek via LiteLLM.

## Data Layout

Keep source code and lightweight docs in:

```text
/home/yiyuldx/swe
```

Keep all large or generated data in:

```text
/data/yiyuldx/swe
```

Current script defaults use:

- `/data/yiyuldx/swe/cache` for downloaded parquet/cache files.
- `/data/yiyuldx/swe/runs` for normalized run artifacts.
- `/data/yiyuldx/swe/outputs` for datasets, reports, task selections, image manifests, and review queues.

Check whether the current machine can run SWE-bench Docker testbeds:

```bash
./scripts/check_docker.sh
```

Current environment status: Docker is installed and reachable from a shell with the `docker`
group. In this Codex session, use `sg docker -c '<command>'` for Docker commands because the
process group was created before the group membership refresh. Docker's data root has been
moved to `/data/yiyuldx/docker`.

## Real SWE-bench Lite Batch Pipeline

Select tasks from the local SWE-bench Lite parquet cache:

```bash
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python \
SWETRACE_TASK_REPO=sqlfluff/sqlfluff \
SWETRACE_TASK_LIMIT=5 \
SWETRACE_SKIP_EXISTING_RUNS=/data/yiyuldx/swe/runs \
./scripts/select_swebench_tasks.sh
```

Preview or pre-pull the SWE-bench Docker images:

```bash
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python \
SWETRACE_DRY_RUN=1 \
./scripts/prepare_swebench_images.sh
```

For actual pulls from this Codex process, wrap with `sg docker`:

```bash
sg docker -c 'SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/prepare_swebench_images.sh'
```

Run individual real-agent tasks with:

```bash
sg docker -c 'HTTP_PROXY=http://10.32.192.70:7890 HTTPS_PROXY=http://10.32.192.70:7890 http_proxy=http://10.32.192.70:7890 https_proxy=http://10.32.192.70:7890 SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python SWETRACE_MINI_MODEL=deepseek/deepseek-chat SWETRACE_MINI_SUBSET=/data/yiyuldx/swe/cache/swebench_lite SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 SWETRACE_MINI_TIMEOUT_SECONDS=600 ./scripts/run_mini_smoke.sh'
```

Build training/debug/reward outputs and human review queue:

```bash
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/recover_mini_runs.sh
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/enrich_swebench_run_tasks.sh
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/build_fake_data.sh
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/auto_label_runs.sh
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/build_review_queue.sh
```

Current real-run status:

- 18 unique SWE-bench Lite dev task IDs have been attempted.
- 19 raw mini-SWE-agent trajectories have been normalized into SWE-Trace artifacts.
- The current pvlib and astroid dev candidates have been collected.
- `/data/yiyuldx/swe/outputs/datasets` currently contains 24 SFT-plan rows, 18 SFT-patch rows, 18 SFT-debug rows, 24 reward logs, and 17 gold-vs-agent DPO pairs.
- The adapter preserves partial trajectories when the outer command times out.
- The manual review queue is written to `/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl`.
Current broader-batch note: Docker image pulls are now stored on `/data`; network/registry
speed is the main limiter for expanding into more repos.

## Local Progress Report

The progress page is generated at:

```text
reports/progress.html
```

During active development it is served from the workspace with:

```bash
/home/yiyuldx/birdNet/.venv/bin/python -m http.server 20038 --bind 0.0.0.0 -d /home/yiyuldx/swe/reports
```

Open it from the local computer at:

```text
http://127.0.0.1:20038/progress.html
```

## Repository Policy

Do not commit local environments, run artifacts, PDFs, model checkpoints, or training logs.
Only source code, project docs, report templates, and reproducible configuration belong in git.

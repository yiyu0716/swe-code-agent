# SWE-Trace Handoff

Last updated: 2026-06-05 02:14 CST

## Current Machine Status

Current repository root:

```bash
/home/yiyuldx/swe
```

Large/generated data root:

```bash
/data/yiyuldx/swe
```

Keep `/home/yiyuldx/swe` for source code and lightweight docs only. Put downloaded datasets,
run artifacts, generated datasets, task selections, image manifests, and manual review queues under
`/data/yiyuldx/swe`.

Current Python environment:

```bash
/home/yiyuldx/birdNet/.venv
```

Current verified status:

```text
30 passed
```

Docker is installed and reachable. In this Codex process, wrap Docker commands with `sg docker -c`
because the shell process predates the docker group refresh. Docker's `data-root` is now
`/data/yiyuldx/docker`.

## Project Positioning

This repository is the first MVP of **SWE-Trace / SWE-Code-Agent**.

The project is aimed at LLM/code-agent internship directions:

- Agent post-training
- SFT data construction
- Code Agent evaluation
- LLM data engineering
- AI Coding application algorithms

The key positioning is not "build another coding agent from scratch". The sharper project story is:

> Build a trajectory collection, failure diagnosis, data construction, and evaluation pipeline for code agents, then use it to generate SFT/DPO/reward-style data and validate a small post-training loop.

## Current State

GitHub repository:

```text
https://github.com/yiyu0716/swe-code-agent.git
```

Current branch status should be checked with:

```bash
git status --short --branch
git log --oneline -1
```

Local Python environment:

```bash
/home/yiyuldx/birdNet/.venv
```

Do not commit virtualenvs, credentials, or generated run data.

## Implemented MVP

Core package:

- `swetrace/schema/`
  - `TaskSpec`
  - `TrajectoryStep`
  - `RunReport`
  - `FailureLabel`
- `swetrace/artifacts/RunStore`
- `swetrace/adapters/fake.py`
- `swetrace/adapters/mini_swe_agent.py`
- `swetrace/eval/`
- `swetrace/labeling/`
- `swetrace/data_builder/`

CLIs:

```bash
python -m swetrace.collect.run_task
python -m swetrace.collect.run_batch
python -m swetrace.data_builder.build_from_runs
python -m swetrace.labeling.auto_label_runs
python -m swetrace.labeling.annotate_review
python -m swetrace.collect.recover_mini_runs
python -m swetrace.collect.enrich_swebench_run_tasks
```

Scripts:

```bash
./scripts/run_fake.sh
./scripts/run_fake_batch.sh
./scripts/build_fake_data.sh
./scripts/auto_label_runs.sh
./scripts/annotate_review.sh
./scripts/run_mini_smoke.sh
./scripts/download_swebench_lite.sh
./scripts/recover_mini_runs.sh
./scripts/enrich_swebench_run_tasks.sh
./scripts/check_docker.sh
./scripts/serve_progress.sh
```

Data builders already exist for:

- SFT plan samples
- SFT patch samples
- SFT debug samples
- DPO pairs
- Gold-patch vs agent-patch DPO pairs for SWE-bench tasks
- Reward logs

Failure taxonomy and rule-based auto-labeling exist, including environment failures such as dataset download and Docker/container errors.

## Verified Data Status

Current generated data is under `/data/yiyuldx/swe`:

- 30 normalized reports in `/data/yiyuldx/swe/runs`.
- 29 mini-SWE-agent reports plus 1 fake baseline.
- 25 raw mini-SWE-agent `.traj.json` files normalized into SWE-Trace artifacts.
- 24 unique mini-SWE-agent task IDs attempted.
- 24 agent patch artifacts.
- 29 manual review queue items.
- 1 manual annotation smoke row in `/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl`.
- Dataset rows: SFT plan 30, SFT patch 24, SFT debug 24, reward logs 30, DPO pairs 23.
- Current SWE-bench Lite dev candidates are exhausted after collecting sqlfluff, marshmallow, pvlib, astroid, pyvista, and pydicom tasks.

These generated files are ignored by git and should stay under `/data/yiyuldx/swe`.

## mini-SWE-agent Status

The `MiniSweAgentAdapter` can:

- Render a command template.
- Support placeholders such as `{task_id}`, `{raw_dir}`, and `{traj_path}`.
- Call `mini-extra` or `uvx --from mini-swe-agent mini-extra`.
- Parse `*.traj.json`.
- Normalize artifacts into:
  - `raw_agent.log`
  - `trajectory.jsonl`
  - `patch.diff`
  - `test.log`
  - `report.json`

Observed mini-SWE-agent version in the original environment:

```text
2.3.0
```

Smoke command with Docker:

```bash
SWETRACE_MINI_SUBSET=/data/yiyuldx/swe/cache/swebench_lite \
SWETRACE_MINI_INSTANCE=sqlfluff__sqlfluff-1625 \
./scripts/run_mini_smoke.sh
```

After a real `.traj.json` is produced, inspect whether the parser matches the true trajectory schema. If it differs from the fixture, adjust `swetrace/adapters/mini_swe_agent.py` and add a regression fixture in `tests/fixtures/`.

## SWE-bench Lite Data

Direct Hugging Face dataset loading was unreliable in the original environment.

The mirror download script works:

```bash
./scripts/download_swebench_lite.sh
```

Expected local cache:

```text
/data/yiyuldx/swe/cache/swebench_lite/data/dev-00000-of-00001.parquet
/data/yiyuldx/swe/cache/swebench_lite/data/test-00000-of-00001.parquet
```

The local dataset was verified readable on the original machine:

- `dev`: 23 examples
- first dev instance: `sqlfluff__sqlfluff-1625`
- `test`: 300 examples

The cache directory is ignored by git and is not required in the source package.

## Current Limiter

Docker works and its data root is on `/data/yiyuldx/docker`. The root filesystem remains
near full because the old `/var/lib/docker` copy has not been removed yet, but new Docker
layers now land on `/data`. The local SWE-bench Lite dev split has no remaining unattempted
tasks when skipping existing runs. The next limiter is data quality: review labels, patch
quality, and train/eval inclusion decisions before expanding to larger splits.

Docker preflight:

```bash
./scripts/check_docker.sh
```

On this machine, the current Codex process should wrap Docker commands with `sg docker -c`.

## Target Machine Recommendation

This host can continue once Docker storage is moved/pruned. A GPU becomes useful later for
Qwen-Coder LoRA/QLoRA post-training, but SWE-bench collection mainly needs Docker, disk,
CPU, RAM, and stable network/proxy.

Minimum practical setup:

- Linux host or container with Docker socket access
- Python 3.12+
- `uv` or standard venv/pip
- Git
- Enough disk for Docker images and checked-out repos
- API key/model access configured outside the repo

## Restore on Target Machine

From GitHub on this machine:

```bash
git clone https://github.com/yiyu0716/swe-code-agent.git /home/yiyuldx/swe
cd /home/yiyuldx/swe
```

Use the existing environment:

```bash
/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Verify:

```bash
/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Serve progress report:

```bash
./scripts/serve_progress.sh
```

Open from local computer using the target server IP and one of the forwarded ports, usually:

```text
http://<server-ip>:20038/
```

## Immediate Next Steps

1. Run full verification with `/home/yiyuldx/birdNet/.venv/bin/python -m pytest -q`.
2. Run `sg docker -c './scripts/check_docker.sh'`.
3. Manually review `/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl`.
4. Continue using `scripts/annotate_review.sh` to record human labels, patch quality, and train/eval inclusion decisions under `/data/yiyuldx/swe/outputs/reports`.
5. Use the reviewed data to write a first data quality report and update filtering rules.
6. Optionally expand beyond Lite dev after the review loop is useful.
7. Keep updating `reports/progress.html` and push GitHub.

## Git and Commit Requirements

Keep GitHub synced.

Commit messages should follow the Lore protocol from `AGENTS.md`:

```text
<intent line>

<body>

Constraint: ...
Rejected: ...
Confidence: high
Scope-risk: narrow
Tested: ...
Not-tested: ...
```

Do not commit:

- `.venv/`
- `.omx/`
- `.pytest_cache/`
- `runs/`
- `outputs/`
- `cache/`
- `checkpoints/`
- `models/`
- `wandb/`
- `mlruns/`
- secrets or API keys

## Security Note

A model-service token was accidentally printed in the shell during the original work session. It was not committed. Do not copy shell history or `.omx` logs into the project package. Rotate that token if it has not already been rotated.

## What to Tell the Next Agent

Continue from the current source tree. Do not restart the project design from scratch. The next valuable milestone is reviewing more queue items with the annotation CLI, then generating a first data-quality report so the collected real trajectories become usable training/debug data.

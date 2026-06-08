# SWE-Trace Handoff

Last updated: 2026-06-06 19:03 CST

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
65 passed
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
python -m swetrace.labeling.review_server
python -m swetrace.collect.recover_mini_runs
python -m swetrace.collect.enrich_swebench_run_tasks
python -m swetrace.collect.audit_swebench_closure
```

Scripts:

```bash
./scripts/run_fake.sh
./scripts/run_fake_batch.sh
./scripts/build_fake_data.sh
./scripts/build_official_v02.sh
./scripts/auto_label_runs.sh
./scripts/annotate_review.sh
./scripts/serve_review_ui.sh
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

- 108 non-fake runs have `official_eval.json`.
- 103 runs completed official SWE-bench evaluation.
- 42 runs are official resolved; after exact patch-output dedupe, 41 rows enter v0.2 SFT.
- 61 official unresolved runs are DPO/debug candidates; after exact pair dedupe, 60 rows enter v0.2 DPO/debug.
- 5 old `psf/requests` runs are still pending and excluded from training labels.
- 103 completed official labels have been backfilled into `runs/*/report.json` main fields.
- The old mini-SWE-agent labels are preserved under `legacy_*` fields.
- Current report/official audit is clean: `report_official_mismatch=0`.
- v0.2 dataset rows: SFT plan 41, SFT patch 41, DPO main 60, debug cases 60, reward logs 103, excluded 27.
- v0.2 DPO chosen sources: `agent_resolved_patch=1`, `swebench_gold_patch=59`.
- `train_ready=true` because the current gate is `SFT >= 30` and `DPO >= 60`.
- Qwen2.5-Coder-7B-Instruct is local at `/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct`.
- SFT/DPO tokenizer-level dry-run smoke has passed and writes training snapshots/metrics to `/data/yiyuldx/swe/outputs/training`.
- `reports/training_dashboard.html` and `/api/training-runs` / `/api/training-metrics` expose smoke metrics in the local review server.
- Do not treat this as formal training: no model weights have been updated yet.
- Current dependency caveat: `trl 1.5.1` DPOTrainer import expects `torch.distributed.fsdp.FSDPModule`, which is not present in `torch 2.5.1+cu121`; formal DPO needs a version pin/compatibility fix first.
- Local Docker has 94 SWE-bench official `latest` images with corresponding Mini run and official eval records.
- Current closure audit is clean: `missing_mini=0`, `missing_official=0`, `nonempty_patch_missing_official=0`.

These generated files are ignored by git and should stay under `/data/yiyuldx/swe`.

Training data source of truth:

```text
/data/yiyuldx/swe/outputs/datasets/v0.2
```

Use `./scripts/build_official_v02.sh` after each closed batch to rebuild this dataset from
completed official SWE-bench results. Old root JSONL files from 2026-06-05 were archived under
`/data/yiyuldx/swe/outputs/datasets/legacy_root_20260605`; do not train on those root JSONL
files, on v0.1 filtered samples, or on `build_fake_data.sh` legacy outputs.

`./scripts/build_fake_data.sh` now writes only to
`/data/yiyuldx/swe/outputs/datasets/legacy_build_from_runs` by default and is for parser/debug
smoke checks, not the real training set.

Hard data rule:

```text
Every downloaded SWE-bench task/image must be closed by Mini collection and official
SWE-bench evaluation before it is counted as usable training data.
```

Official status import rule:

```text
`python -m swetrace.eval.swebench_official import-statuses` writes `official_eval.json`
and automatically backfills completed official labels into `report.json`. Do not rely on
legacy mini labels for training success/failure decisions.
```

Use this audit after every expansion batch:

```bash
sg docker -c 'cd /home/yiyuldx/swe && /home/yiyuldx/birdNet/.venv/bin/python -m swetrace.collect.audit_swebench_closure --runs /data/yiyuldx/swe/runs'
```

If the audit reports `tasks_missing_mini_run`, `tasks_without_official_eval`, or
`nonempty_patch_missing_official`, finish Mini collection and official evaluation for those
instances before selecting more tasks.

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
tasks when skipping existing runs. The current v0.2 data has crossed the initial training
threshold with enough official resolved SFT samples and official unresolved + gold-patch DPO
rows. The current limiter is no longer raw DPO count; it is freezing a reproducible training
snapshot and running a small SFT/DPO smoke before training.

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
3. For every newly downloaded SWE-bench image/task, run Mini collection, official evaluation, import `official_eval.json` with `swetrace.eval.swebench_official import-statuses`, rebuild v0.2 with `./scripts/build_official_v02.sh`, then run `swetrace.collect.audit_swebench_closure`.
4. Freeze the current `/data/yiyuldx/swe/outputs/datasets/v0.2` snapshot for training, then run data-format smoke checks and a small SFT/DPO training dry run.
5. Continue SWE-bench Lite test split expansion only in closed batches: Mini collection, official evaluation, import/backfill, v0.2 rebuild, and closure audit.
6. Keep reports updated, especially `reports/progress.html` and `reports/data_quality_report.html`.
7. Push source/report changes to GitHub; never commit `/data` artifacts or credentials.

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

Continue from the current source tree. Do not restart the project design from scratch. The current v0.2 data has reached `train_ready=true` with `SFT patch=41` and `DPO main=60` after exact training-row dedupe. Qwen tokenizer-level SFT/DPO dry-run smoke and the training dashboard are in place; no formal training has started. The next valuable milestone is resolving the DPOTrainer dependency pin and, after explicit user confirmation, running a small SFT LoRA experiment with metrics written to `/data/yiyuldx/swe/outputs/training`, while keeping the download -> Mini -> official eval -> v0.2 rebuild closure gate for every future expansion batch.

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

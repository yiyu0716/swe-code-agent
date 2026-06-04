# SWE-Trace Handoff

Last updated: 2026-06-04 07:29 UTC

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

Repository root:

```bash
/root/swe
```

GitHub repository:

```text
https://github.com/yiyu0716/swe-code-agent.git
```

Latest known commit before this handoff:

```text
1905510 Document Docker preflight blocker
```

Local Python environment on the original machine:

```bash
/root/swe/.venv
```

Do not rely on the original `.venv` after migration. Recreate it on the target machine.

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
```

Scripts:

```bash
./scripts/run_fake.sh
./scripts/run_fake_batch.sh
./scripts/build_fake_data.sh
./scripts/auto_label_runs.sh
./scripts/run_mini_smoke.sh
./scripts/download_swebench_lite.sh
./scripts/check_docker.sh
./scripts/serve_progress.sh
```

Data builders already exist for:

- SFT plan samples
- SFT patch samples
- SFT debug samples
- DPO pairs
- Reward logs

Failure taxonomy and rule-based auto-labeling exist, including environment failures such as dataset download and Docker/container errors.

## Verified Status

Last verified before packaging:

```bash
/root/swe/.venv/bin/python -m pytest -q
```

Expected result:

```text
19 passed
```

The fake pipeline has produced sample `runs/` and `outputs/`, but those directories are ignored by git and should be regenerated on the target machine when needed.

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

Smoke command once Docker is available:

```bash
SWETRACE_MINI_SUBSET=/root/swe/cache/swebench_lite \
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
cache/swebench_lite/data/dev-00000-of-00001.parquet
cache/swebench_lite/data/test-00000-of-00001.parquet
```

The local dataset was verified readable on the original machine:

- `dev`: 23 examples
- first dev instance: `sqlfluff__sqlfluff-1625`
- `test`: 300 examples

The cache directory is ignored by git and is not required in the source package.

## Current Blocker

Docker is not available in the original container:

- `docker` binary: missing
- `/var/run/docker.sock`: missing
- `podman`: missing
- `nerdctl`: missing

This blocks real SWE-bench execution because mini-SWE-agent/SWE-bench needs isolated Docker testbeds to run repository-specific tests.

Docker preflight:

```bash
./scripts/check_docker.sh
```

On a usable target machine, this should find Docker, reach the daemon, and successfully run `hello-world` or the image configured via `SWETRACE_DOCKER_TEST_IMAGE`.

## Target Machine Recommendation

The user's 3090 machine is a good next host.

Why:

- Docker availability matters more than GPU for SWE-bench execution.
- A 3090 is useful later for Qwen-Coder LoRA/QLoRA post-training.
- CPU, RAM, disk, and Docker daemon stability are needed for batch SWE-bench evaluation.

Minimum practical target setup:

- Linux host or container with Docker socket access
- Python 3.12+
- `uv` or standard venv/pip
- Git
- Enough disk for Docker images and checked-out repos
- API key/model access configured outside the repo

## Restore on Target Machine

From a compressed package:

```bash
mkdir -p /root/swe
tar -xzf swe-code-agent-handoff-*.tar.gz -C /root/swe --strip-components=1
cd /root/swe
```

Or from GitHub:

```bash
git clone https://github.com/yiyu0716/swe-code-agent.git /root/swe
cd /root/swe
```

Create environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m pip install -U pytest datasets pyarrow
```

Verify:

```bash
.venv/bin/python -m pytest -q
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

1. Recreate the Python environment on the 3090 machine.
2. Run the test suite.
3. Run `./scripts/check_docker.sh`.
4. Download SWE-bench Lite through the mirror.
5. Run the local-subset mini-SWE-agent smoke.
6. If Docker works and a real trajectory appears, fix any parser mismatch.
7. Run 5-10 SWE-bench Lite dev tasks.
8. Build SFT/debug/reward outputs from real runs.
9. Add an annotation CLI for human failure labels.
10. Keep updating `reports/progress.html`, commit with Lore protocol, and push to GitHub.

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

Continue from the current source tree. Do not restart the project design from scratch. The next valuable milestone is real mini-SWE-agent execution on SWE-bench Lite with Docker available, then parser hardening and real trajectory dataset construction.

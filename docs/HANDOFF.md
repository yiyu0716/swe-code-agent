# SWE-Trace / SWE-Code-Agent Handoff

Last updated: 2026-06-11 CST

This handoff is for `/home/yiyuldx/swe` only. It does not describe Orbit Wars or any other project.

The goal is to keep the next worker grounded in facts that were verified locally. Anything not verified is marked as a caveat or next step.

## Project Summary

Repository:

```text
/home/yiyuldx/swe
```

Large/generated data root:

```text
/data/yiyuldx/swe
```

GitHub remote:

```text
https://github.com/yiyu0716/swe-code-agent.git
```

Project positioning:

```text
SWE-Trace / SWE-Code-Agent is a code-agent data and evaluation pipeline.
It is not trying to build a new coding agent from scratch.
```

The current project value is:

- collect Mini-SWE-agent trajectories on SWE-bench tasks
- normalize trajectory, patch, test log, and report artifacts
- run official SWE-bench evaluation for nonempty patches
- build official-aware SFT/DPO/reward/debug datasets
- provide review and report pages
- run small Qwen LoRA/tokenizer/dry-run smoke tests
- prepare a clean held-out eval set and baseline before formal training

## Current Git State

Fresh command:

```bash
git status --short --branch
git log --oneline -5
```

Observed:

```text
## main...origin/main
?? configs/
?? docs/ATTRIBUTION.md
?? docs/POST_TRAINING_STUDY_PLAN.md
f7c8326 Parse textbased mini trajectories
37f6386 Document restored training and vLLM envs
97f46c3 Add public SFT mix pipeline
7290e35 Record Qwen LoRA smoke result
e3dbeb8 Add training smoke dashboard
```

Facts:

- Branch is `main`.
- Local branch is aligned with `origin/main` in the status output.
- There are untracked source/docs paths:
  - `configs/`
  - `docs/ATTRIBUTION.md`
  - `docs/POST_TRAINING_STUDY_PLAN.md`
- Do not delete or overwrite untracked files without checking their content.

## Environment

Main Python environment:

```text
/home/yiyuldx/birdNet/.venv
```

Fresh package check:

```text
python 3.11.14
executable /home/yiyuldx/birdNet/.venv/bin/python
torch 2.5.1+cu121
transformers 4.46.3
trl 0.12.2
peft 0.19.1
bitsandbytes 0.49.2
datasets 4.8.5
huggingface_hub 0.36.2
vllm MISSING
mini-swe-agent MISSING
litellm 1.87.0
pydantic 2.12.5
pytest 9.0.2
torch_cuda 12.1 available True device_count 3
```

Important environment rule:

```text
Do not install vLLM into /home/yiyuldx/birdNet/.venv.
Use /data/yiyuldx/swe/venvs/vllm-cu121 for vLLM.
```

Isolated vLLM environment:

```text
/data/yiyuldx/swe/venvs/vllm-cu121/bin/python
```

Fresh vLLM env package check:

```text
python 3.11.14
executable /data/yiyuldx/swe/venvs/vllm-cu121/bin/python
vllm 0.6.6.post1
torch 2.5.1
transformers 4.46.3
tokenizers 0.20.3
```

GPU status at the time of this handoff:

```text
GPU0 RTX 3090: 1 MiB / 24576 MiB, 0%
GPU1 RTX 3090: 8774 MiB / 24576 MiB, 75%
GPU2 RTX 3090: 1 MiB / 24576 MiB, 0%
```

Interpretation:

- Qwen/vLLM is not currently deployed on GPU0.
- GPU0 and GPU2 appeared free when checked.
- GPU1 was occupied by another process when checked.

## Docker

Fresh command:

```bash
./scripts/check_docker.sh
```

Observed:

```text
docker daemon: reachable
test image: hello-world
docker preflight: ok
```

Docker details:

- Docker binary: `/usr/bin/docker`
- Docker server version: `29.1.3`
- Docker data root was previously moved to `/data/yiyuldx/docker`.
- In this current shell, Docker was reachable without wrapping in `sg docker`.
- If a future Codex shell predates group membership refresh and gets Docker permission errors, use:

```bash
sg docker -c '<docker or script command>'
```

## Fresh Test Verification

Fresh command:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Observed:

```text
86 passed in 6.95s
```

This verifies the current Python test suite only. It does not prove training quality or model performance.

## Implemented Code Surface

Core package:

- `swetrace/schema/`
  - `TaskSpec`
  - `TrajectoryStep`
  - `RunReport`
  - `FailureLabel`
- `swetrace/artifacts/RunStore`
- `swetrace/adapters/fake.py`
- `swetrace/adapters/mini_swe_agent.py`
- `swetrace/eval/swebench_official.py`
- `swetrace/collect/`
- `swetrace/data_builder/`
- `swetrace/labeling/`
- `swetrace/training/`

Important current adapter fact:

- `MiniSweAgentAdapter` parses textbased Mini trajectories.
- Regression coverage exists in `tests/test_mini_swe_agent_adapter.py`.
- Latest commit shown by git is `f7c8326 Parse textbased mini trajectories`.

Key scripts:

```text
scripts/check_docker.sh
scripts/download_swebench_lite.sh
scripts/run_mini_smoke.sh
scripts/run_official_eval.sh
scripts/build_official_v02.sh
scripts/build_sft_mix.sh
scripts/run_sft_smoke.sh
scripts/run_dpo_smoke.sh
scripts/serve_review_ui.sh
scripts/serve_progress.sh
```

## Data Roots And Cache

SWE-bench Lite local cache exists:

```text
/data/yiyuldx/swe/cache/swebench_lite/data/dev-00000-of-00001.parquet 119551 bytes
/data/yiyuldx/swe/cache/swebench_lite/data/test-00000-of-00001.parquet 1119540 bytes
/data/yiyuldx/swe/cache/swebench_lite/swebench_lite_dev_test.json 3952896 bytes
```

Qwen model exists locally:

```text
/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct
```

Fresh size check:

```text
15G /data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct
```

Model files include:

```text
config.json
generation_config.json
model-00001-of-00004.safetensors
model-00002-of-00004.safetensors
model-00003-of-00004.safetensors
model-00004-of-00004.safetensors
model.safetensors.index.json
tokenizer.json
tokenizer_config.json
vocab.json
merges.txt
```

## Run And Official Evaluation Status

Fresh audit across:

- `/data/yiyuldx/swe/runs`
- `/data/yiyuldx/swe/evals/qwen_baseline_v0/runs`
- `/data/yiyuldx/swe/outputs/runs`

Observed:

```text
reports 152
agent {'fake': 1, 'mini-swe-agent': 151}
status {'resolved': 43, 'env_error': 15, 'failed': 93, 'stopped': 1}
stop_reason {'final': 136, 'env_error': 15, 'step_limit': 1}
label_source {None: 23, 'swebench_official': 109, 'mini_swe_agent': 20}
official_completed {None: 43, True: 109}
resolved {True: 43, False: 109}
nonempty_patch_missing_official_eval_json 0
steps_ge_100 39
steps_ge_150 17
steps_ge_200 8
max_steps 294
```

Most important data-quality fact:

```text
nonempty_patch_missing_official_eval_json = 0
```

This means the old severe bug is not currently present for nonempty patches: nonempty patches found in these run roots have official evaluation JSON.

Important caveat:

- Some trajectory text can still contain Mini-local strings such as `action was not executed`.
- Those strings must not be used as truth labels.
- Current v0.2 training labels use official SWE-bench fields, not Mini-local `test.log` heuristics.

## Closure Audit Caveat

Fresh command:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python \
  -m swetrace.collect.audit_swebench_closure --runs /data/yiyuldx/swe/runs
```

Exit code: `1`

Observed:

```text
latest_images: 112
tasks_with_mini_run: 94
tasks_missing_mini_run: 18
tasks_without_nonempty_patch: 18
tasks_without_official_eval: 18
closed_tasks: 94
nonempty_patch_missing_official: 0
pending_official: 5
pending_official_tasks:
  psf__requests-1963
  psf__requests-2148
  psf__requests-2317
  psf__requests-2674
  psf__requests-3362
```

The 18 missing IDs are:

```text
django__django-11133
django__django-12915
django__django-13158
django__django-13230
django__django-14667
django__django-14915
django__django-14997
django__django-16873
matplotlib__matplotlib-25442
matplotlib__matplotlib-25498
scikit-learn__scikit-learn-10949
scikit-learn__scikit-learn-13142
scikit-learn__scikit-learn-13497
sympy__sympy-11870
sympy__sympy-11897
sympy__sympy-15609
sympy__sympy-15678
sympy__sympy-16792
```

Interpretation:

- Do not describe closure audit as fully green.
- Do describe the most important safety condition as green: `nonempty_patch_missing_official = 0`.
- The 18 missing tasks line up with held-out Qwen baseline task/image work rather than v0.2 training rows, but they still make the main `/data/yiyuldx/swe/runs` closure audit return nonzero.
- If those images/tasks are meant to enter training expansion, they must be closed by Mini collection plus official evaluation first.

## v0.2 Training Dataset

Source of truth:

```text
/data/yiyuldx/swe/outputs/datasets/v0.2
```

Manifest:

```text
version: v0.2-official-20260607
created_at: 2026-06-07T03:08:38.669811+00:00
source_runs: /data/yiyuldx/swe/runs
requires_official_eval: true
min_sft: 30
min_dpo: 60
train_ready: true
```

Fresh strict audit:

```text
sft_rows: 41
sft_official_completed: {true: 41}
sft_official_resolved: {true: 41}
sft_empty_output: 0

dpo_rows: 60
dpo_chosen_source:
  agent_resolved_patch: 1
  swebench_gold_patch: 59
dpo_chosen_resolved: {true: 60}
dpo_rejected_official_completed: {true: 60}
dpo_rejected_official_resolved: {false: 60}
dpo_empty_pairs: 0
dpo_degenerate_pairs: 0

reward_rows: 103
reward_official_completed: {true: 103}
reward_resolved: {false: 61, true: 42}
reward_tests_passed: {false: 61, true: 42}

excluded_rows: 27
excluded_reasons:
  fake_or_synthetic: 1
  missing_official_eval: 19
  official_eval_pending: 5
  duplicate_sft_patch: 1
  duplicate_dpo_pair: 1
```

The strict assertions passed:

```text
STRICT_V02_AUDIT_OK
```

Practical conclusion:

- v0.2 is acceptable for the next small SFT experiment.
- v0.2 DPO has exactly 60 pairs and satisfies the current gate.
- DPO chosen is still mostly SWE-bench gold patch (`59/60`), with only one same-task agent-resolved chosen patch.
- Public or local training claims should mention this mix honestly.

Do not train on:

```text
/data/yiyuldx/swe/outputs/datasets/legacy_root_20260605
/data/yiyuldx/swe/outputs/datasets/v0.1
legacy outputs from build_fake_data.sh
root-level old JSONL files
```

## Public SFT Import And Mix

Public SFT import:

```text
/data/yiyuldx/swe/outputs/datasets/public_sft_v0.1
```

Manifest facts:

```text
source: R2E-Gym/R2EGym-SFT-Trajectories
raw: /data/yiyuldx/swe/public_datasets/raw/R2EGym-SFT-Trajectories/data/train-00000-of-00001.parquet
source_rows: 3231
imported: 3224
excluded: 7
pollution_terms: 117
schema: messages_v1
```

Quality notes from the manifest:

- Public rows do not carry SWE-Trace official_eval labels.
- Public rows are suitable for public SFT warmup, not trusted resolved-rate claims.
- Explicit task-id pollution is filtered; source rows without task ids cannot be proven fully uncontaminated.

SFT mix:

```text
/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1
```

SFT mix manifest:

```text
/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1/manifest.json
```

Manifest facts:

```text
public_messages: 3224
local_sft: 41
total_messages: 3265
schema: messages_v1
```

Practical conclusion:

- `sft_mix_v0.1` is the scale-up SFT warmup dataset.
- `v0.2` is the high-trust official-evaluated local dataset.

## Held-Out Qwen Baseline

Fixed eval set:

```text
/data/yiyuldx/swe/eval_sets/qwen_baseline_v0
```

Baseline artifacts:

```text
/data/yiyuldx/swe/evals/qwen_baseline_v0
```

Current baseline status file:

```text
/data/yiyuldx/swe/evals/qwen_baseline_v0/baseline_status_20260609_textbased_current.json
```

Fresh summary:

```text
eval_set_tasks: 20
tasks_with_runs: 20
latest_runs_with_report: 20
latest_env_error_tasks: 2
latest_env_error_ids:
  matplotlib__matplotlib-24970
  matplotlib__matplotlib-25079
latest_nonempty_patch_tasks: 6
latest_official_completed_tasks: 6
latest_official_resolved_tasks: 0
latest_nonempty_missing_official: []
all_runs: 24
all_nonempty_patch_runs: 6
all_official_completed_runs: 6
all_official_resolved_runs: 0
by_latest_status:
  failed: 18
  env_error: 2
```

Interpretation:

- The fixed 20-task held-out baseline exists.
- The Qwen base baseline produced 6 nonempty patches.
- All 6 nonempty baseline patches were officially evaluated.
- Official resolved count for this baseline is 0.
- Two latest held-out tasks are environment errors, not confirmed model patch failures.

This baseline is useful as a fixed comparison set after SFT LoRA. It is small; do not overclaim statistical significance.

## Training Smoke Assets

Important smoke results:

```text
/data/yiyuldx/swe/outputs/training/sft-lora-smoke-20260608T100926Z/smoke_result.json
```

Observed:

```text
status: real_lora_smoke_ok
loss: 1.193279
grad_norm: 0.256583
trainable_params: 20185088
total_params: 4373157376
seq_length: 783
formal_training: false
```

SFT mix LoRA smoke:

```text
/data/yiyuldx/swe/outputs/training/sft-mix-lora-smoke-20260609T064338Z/smoke_result.json
```

Observed:

```text
status: real_lora_smoke_ok
loss: 1.849222
grad_norm: 0.285644
trainable_params: 20185088
total_params: 4373157376
seq_length: 1024
formal_training: false
```

DPO v0.2 dry smoke:

```text
/data/yiyuldx/swe/outputs/training/dpo-v02-dry-smoke-20260609T090929Z/snapshot.json
```

Observed:

```text
stage: dpo_smoke
dataset: /data/yiyuldx/swe/outputs/datasets/v0.2
version: v0.2-official-20260607
mode: dry_run_no_weight_update
tokenizer: Qwen2TokenizerFast
```

SFT mix dry smoke:

```text
/data/yiyuldx/swe/outputs/training/sft-mix-dry-smoke-20260609T090929Z/snapshot.json
```

Observed:

```text
stage: sft_smoke
dataset: /data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1
version: sft-mix-v0.1
mode: dry_run_no_weight_update
tokenizer: Qwen2TokenizerFast
```

Important:

```text
No formal training run has been confirmed in this handoff.
Formal training still requires explicit user confirmation.
```

## Local Web / Review Servers

Processes observed:

```text
/home/yiyuldx/birdNet/.venv/bin/python -m http.server 20037 --bind 0.0.0.0 -d /home/yiyuldx/swe/reports
/home/yiyuldx/birdNet/.venv/bin/python -m http.server 20038 --bind 0.0.0.0 -d /home/yiyuldx/swe/reports
/home/yiyuldx/birdNet/.venv/bin/python -m http.server 8888 --bind 0.0.0.0 -d /home/yiyuldx/swe/reports
/home/yiyuldx/birdNet/.venv/bin/python -m swetrace.labeling.review_server --host 127.0.0.1 --port 20039 ...
```

Useful URLs:

```text
http://127.0.0.1:20039/review
http://127.0.0.1:20039/training_dashboard.html
http://127.0.0.1:20039/data_quality_report.html
http://127.0.0.1:20039/annotation_calibration.html
http://127.0.0.1:20037/progress.html
```

The review server API responded for `/api/training-runs` with `total: 17` training/smoke run entries.

## Behavior Quality Caveat

Fresh trajectory behavior stats across run roots:

```text
steps_ge_100: 39
steps_ge_150: 17
steps_ge_200: 8
max_steps: 294
stop_reason step_limit: 1
```

Interpretation:

- The old hard `step_limit` failure is not common.
- Long ReAct trajectories are common enough to track.
- Qwen baseline has examples of repeated failing search/grep behavior and empty-patch outcomes.

Practical data rule:

- Do not automatically use long, looping, empty-patch, EOF-exit, or near-limit trajectories as high-quality SFT traces.
- They are better suited for debug/reward/DPO negative examples unless official resolved and manually inspected.

## 2026-06-11 Formal SFT LoRA Experiment

User explicitly approved starting a training experiment on 2026-06-11. Before training, fresh verification was run:

```text
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
90 passed in 7.12s
```

New code added for reproducible SFT:

```text
swetrace/training/sft_lora.py
scripts/run_sft_lora.sh
tests/test_sft_lora_training.py
```

The new runner:

- reads `messages.jsonl` datasets
- writes `snapshot.json`, `metrics.jsonl`, and `train_result.json`
- saves a PEFT LoRA adapter and tokenizer
- defaults to `CUDA_VISIBLE_DEVICES=0`
- sets `USE_TF=0`, `USE_FLAX=0`, and `TRANSFORMERS_NO_TF=1` so the main `.venv` does not trip over TensorFlow/Numpy 2 imports
- supports dry-run mode for tests and real QLoRA SFT mode for training

Base model experiment asset:

```text
/data/yiyuldx/swe/evals/qwen_baseline_v0/baseline_status_20260609_textbased_current.json
```

Base baseline summary:

```text
eval_set_tasks: 20
latest_runs_with_report: 20
latest_env_error_tasks: 2
latest_nonempty_patch_tasks: 6
latest_official_completed_tasks: 6
latest_official_resolved_tasks: 0
latest_nonempty_missing_official: []
```

Formal SFT run:

```text
run_id: sft-mix-qwen2p5-7b-lora-v01-20260611
model: /data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct
dataset: /data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1
dataset rows: 3265 messages = 3224 public + 41 local official-aware v0.2 SFT
GPU: CUDA_VISIBLE_DEVICES=0
method: 4bit QLoRA SFT
max_steps: 80
max_seq_length: 1024
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 2e-4
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
status: formal_sft_lora_ok
runtime: 770.822 seconds
trainable_params: 40,370,176
total_params: 4,393,342,464
```

Training artifacts:

```text
/data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611
/data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611/adapter
/data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611/metrics.jsonl
/data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611/train_result.json
```

Artifact check:

```text
run dir size: 170M
metrics_rows: 80
first_loss: 1.8651
last_logged_loss: 0.0001
min_loss: 0.0001
max_loss: 1.8651
mean_logged_loss: 0.162805
nan_losses: 0
```

Important interpretation:

- The fast loss drop proves the weight-update/data/metrics/adapter plumbing works.
- It does not prove SWE-bench capability improved.
- The held-out official eval must be rerun on the same 20 tasks before making any performance claim.

Experiment manifest:

```text
/data/yiyuldx/swe/outputs/experiments/qwen2p5-7b-sft-v01-20260611T140358Z/experiment_manifest.json
```

SFT LoRA inference smoke:

```text
vLLM env: /data/yiyuldx/swe/venvs/vllm-cu121
served base model: qwen2.5-coder-7b-instruct
served LoRA model: qwen2p5-sft-v01
adapter: /data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611/adapter
request: Reply with exactly: sft lora smoke ok
response: sft lora smoke ok
status: passed
```

vLLM LoRA note:

- The first LoRA server attempt failed with `ModuleNotFoundError: No module named 'setuptools'`.
- Root cause was the isolated vLLM env missing `setuptools`; vLLM's LoRA/Triton path imports Triton build helpers.
- Fixed by installing `setuptools==82.0.1` only into `/data/yiyuldx/swe/venvs/vllm-cu121`.
- Main `/home/yiyuldx/birdNet/.venv` was not changed for this fix.
- GPU0 was released after the smoke; fresh check showed GPU0 at `1 MiB / 24576 MiB`.

## Immediate Next Steps

1. Do not change project scope. Continue SWE-Trace / SWE-Code-Agent only.

2. Treat these as current source-of-truth datasets:

```text
/data/yiyuldx/swe/outputs/datasets/v0.2
/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1
/data/yiyuldx/swe/eval_sets/qwen_baseline_v0
/data/yiyuldx/swe/evals/qwen_baseline_v0
```

3. Before any new training or evaluation batch, re-run:

```bash
cd /home/yiyuldx/swe
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python - <<'PY'
import json, pathlib
p=pathlib.Path('/data/yiyuldx/swe/outputs/datasets/v0.2/manifest.json')
print(json.dumps(json.loads(p.read_text())['counts'], indent=2))
PY
```

4. The first real SFT LoRA has now been run. Next highest-priority action is to rerun exactly the same 20-task held-out eval with the SFT LoRA adapter and official evaluation.

Suggested SFT LoRA eval target:

```text
Base model: /data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct
LoRA adapter: /data/yiyuldx/swe/outputs/training/sft-mix-qwen2p5-7b-lora-v01-20260611/adapter
Served vLLM LoRA model name: qwen2p5-sft-v01
Eval: /data/yiyuldx/swe/eval_sets/qwen_baseline_v0
Compare against: qwen_baseline_v0 official resolved=0
```

5. After collecting LoRA eval runs, run official SWE-bench evaluation for every nonempty LoRA patch and backfill reports. Do not compare against base using Mini-only labels.

6. Keep every new SWE-bench task batch closed:

```text
download/select task
prepare/pull Docker image
Mini collection
official SWE-bench evaluation for nonempty patch
import/backfill official labels
build_official_v02
strict data audit
update progress/report pages
```

7. If expanding DPO, prioritize getting more agent-resolved chosen patches. Current DPO chosen source is mostly gold patch (`59/60`), which is valid but less representative of the model's own successful distribution.

8. If using public SFT data, keep claims separate:

```text
public_sft_v0.1 / sft_mix_v0.1 = scale/warmup
v0.2 = official-evaluated local trusted labels
```

9. Update `reports/progress.html` after meaningful project changes.

10. Sync GitHub only after reviewing untracked files and confirming they should be committed.

## Short Prompt For Next Session

```text
Continue only the SWE-Trace / SWE-Code-Agent project in /home/yiyuldx/swe.

Use /home/yiyuldx/birdNet/.venv as the main environment. Keep large data under /data/yiyuldx/swe. Do not install vLLM into the main .venv; use /data/yiyuldx/swe/venvs/vllm-cu121 if vLLM is needed.

Current verified facts from 2026-06-11:
- pytest: 86 passed in 6.95s.
- Docker preflight: ok.
- Qwen model exists at /data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct.
- v0.2 dataset is official-aware and train_ready=true: SFT patch 41, DPO main 60, reward logs 103.
- Strict v0.2 audit passed: all SFT rows are official resolved, all DPO rejected rows are official unresolved, no empty or degenerate DPO pairs.
- Nonempty patch missing official_eval.json across checked run roots is 0.
- Main closure audit on /data/yiyuldx/swe/runs is not fully green: latest_images=112, closed_tasks=94, missing_mini=18, pending_official=5, but nonempty_patch_missing_official=0.
- Held-out Qwen baseline v0 has 20 tasks, 20 latest reports, 6 nonempty patches, all 6 officially evaluated, 0 resolved, 2 env_error.
- Public SFT import has 3224 rows; sft_mix_v0.1 has 3265 messages = 3224 public + 41 local v0.2 SFT.
- SFT LoRA smoke and SFT mix LoRA smoke succeeded.
- Formal SFT LoRA run `sft-mix-qwen2p5-7b-lora-v01-20260611` succeeded on GPU0.
- LoRA inference smoke with vLLM model name `qwen2p5-sft-v01` succeeded.

Do not overclaim. The next useful action is to rerun exactly the same 20-task Qwen held-out eval through the SFT LoRA adapter and official SWE-bench evaluation, while continuing to keep every new task batch closed by Mini collection plus official evaluation.
```

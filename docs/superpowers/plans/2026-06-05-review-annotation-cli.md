# Review Annotation CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal non-interactive CLI that records human review annotations for manual review queue items.

**Architecture:** Keep run artifacts immutable. The CLI reads the existing manual review queue JSONL, validates that a requested `run_id` exists, then upserts one annotation row into a separate JSONL file under `/data/yiyuldx/swe/outputs/reports`. A small Pydantic schema keeps annotation rows stable for later filtering and data-quality reports.

**Tech Stack:** Python 3.12, Typer, Pydantic, pytest, shell wrapper scripts.

---

### Task 1: Annotation Schema And CLI

**Files:**
- Create: `swetrace/labeling/annotate_review.py`
- Modify: `swetrace/schema/label.py`
- Modify: `swetrace/schema/__init__.py`
- Modify: `scripts/annotate_review.sh`
- Test: `tests/test_swebench_pipeline_clis.py`

- [x] **Step 1: Write the failing CLI tests**

Add tests that create a tiny `manual_review_queue.jsonl`, run:

```bash
python -m swetrace.labeling.annotate_review \
  --queue /tmp/manual_review_queue.jsonl \
  --out /tmp/manual_annotations.jsonl \
  --run-id run-1 \
  --human-failure PatchError.IncompleteFix \
  --patch-quality partial \
  --sft-usable false \
  --dpo-usable true \
  --notes "Patch is close but tests fail."
```

Expected assertions:
- CLI exits 0.
- stdout is `{"annotations": 1, "updated": "run-1", "out": "...manual_annotations.jsonl"}`.
- Output JSONL contains one row with `run_id`, `task_id`, automatic label fields copied from the queue, human fields, and notes.
- Running the CLI again for the same `run_id` replaces the row instead of appending a duplicate.

- [x] **Step 2: Run the failing tests**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_swebench_pipeline_clis.py::test_annotate_review_writes_human_annotation -q
```

Expected: FAIL because `swetrace.labeling.annotate_review` does not exist yet.

- [x] **Step 3: Implement the minimal schema**

Add `ReviewAnnotation` to `swetrace/schema/label.py` with fields:

```python
run_id: str
task_id: str
auto_primary_failure: str
auto_severity: int
human_failure: str
patch_quality: str
sft_usable: bool
dpo_usable: bool
notes: str | None = None
reviewer: str = "manual"
```

Export it from `swetrace/schema/__init__.py`.

- [x] **Step 4: Implement the CLI**

Create `swetrace/labeling/annotate_review.py` that:
- Reads queue rows from `--queue`.
- Fails with a clear Typer error if `--run-id` is absent from the queue.
- Reads existing annotation rows from `--out` if the file exists.
- Upserts by `run_id`.
- Writes JSONL with `ensure_ascii=False`.
- Echoes a compact JSON summary.

- [x] **Step 5: Add the shell wrapper**

Create `scripts/annotate_review.sh` with defaults:

```bash
QUEUE="${SWETRACE_REVIEW_QUEUE:-/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl}"
OUT="${SWETRACE_REVIEW_ANNOTATIONS:-/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl}"
PYTHON="${SWETRACE_PYTHON:-.venv/bin/python}"
```

Pass all additional CLI args through with `"$@"`.

- [x] **Step 6: Run targeted and full tests**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_swebench_pipeline_clis.py::test_annotate_review_writes_human_annotation tests/test_swebench_pipeline_clis.py::test_annotate_review_updates_existing_annotation -q
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Expected: all tests pass.

### Task 2: Real Data Smoke And Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/CONTINUE_PROMPT.md`
- Modify: `reports/progress.html`

- [x] **Step 1: Run a real annotation smoke**

Use one existing review queue item and write:

```bash
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python \
./scripts/annotate_review.sh \
  --run-id 20260604T180152Z-pydicom__pydicom-1694-mini-swe-agent-86ca4ad0 \
  --human-failure PatchError.IncompleteFix \
  --patch-quality close \
  --sft-usable false \
  --dpo-usable true \
  --notes "Gold patch is a tiny try-block move; agent patch matches the intended change but run did not resolve."
```

Expected: `/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl` has one reviewed row.

- [x] **Step 2: Update progress docs**

Record that the review annotation path exists, the first smoke annotation was written, and reviewed data now stays under `/data/yiyuldx/swe/outputs/reports`.

- [x] **Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
sg docker -c './scripts/check_docker.sh'
git diff --check
```

Commit source and docs only; do not commit `/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl`.

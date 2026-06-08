# Training Smoke Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible training snapshot, tokenizer-level SFT/DPO dry-runs, JSONL metrics logging, and a local web dashboard without starting formal training.

**Architecture:** Training utilities live under `swetrace/training` and write only to `/data/yiyuldx/swe/outputs/training`. The review server exposes read-only training APIs that the static dashboard consumes. Smoke scripts validate dataset/model/tokenizer paths and write metrics, but do not update model weights.

**Tech Stack:** Python stdlib, Typer, Transformers tokenizer loading, existing `ThreadingHTTPServer`, static HTML/JS.

---

### Task 1: Snapshot And Metrics

**Files:**
- Create: `swetrace/training/__init__.py`
- Create: `swetrace/training/snapshot.py`
- Create: `swetrace/training/metrics.py`
- Test: `tests/test_training_snapshot.py`

- [ ] Write failing tests for snapshot manifest creation and metrics append/read.
- [ ] Implement `create_training_snapshot`, `append_metric`, `list_training_runs`, and `load_training_metrics`.
- [ ] Verify tests pass.

### Task 2: SFT/DPO Dry-Run CLI

**Files:**
- Create: `swetrace/training/smoke.py`
- Create: `scripts/run_sft_smoke.sh`
- Create: `scripts/run_dpo_smoke.sh`
- Test: `tests/test_training_smoke.py`

- [ ] Write failing tests for SFT and DPO dry-runs.
- [ ] Implement tokenizer-level validation and metrics writing.
- [ ] Verify tests pass.

### Task 3: Dashboard API And Page

**Files:**
- Modify: `swetrace/labeling/review_server.py`
- Modify: `scripts/serve_review_ui.sh`
- Create: `reports/training_dashboard.html`
- Modify: `reports/index.html`
- Test: `tests/test_review_server.py`
- Test: `tests/test_reports_pages.py`

- [ ] Write failing tests for `/api/training-runs`, `/api/training-metrics`, and dashboard links.
- [ ] Implement API handlers and static dashboard.
- [ ] Verify tests pass.

### Task 4: Verification And Progress

**Files:**
- Modify: `reports/progress.html`
- Modify: `README.md`
- Modify: `docs/HANDOFF.md`

- [ ] Run dry-runs against `/data/yiyuldx/swe/outputs/datasets/v0.2` and Qwen tokenizer.
- [ ] Run full pytest and Docker closure checks.
- [ ] Update reports and docs with dry-run status.
- [ ] Commit and push.

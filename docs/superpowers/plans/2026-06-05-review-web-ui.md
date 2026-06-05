# Review Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local browser-based review workbench for visual manual annotation of SWE-Trace review queue items.

**Architecture:** Keep annotation storage in the existing `/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl`. Add a standard-library HTTP server that binds to `127.0.0.1`, serves `reports/review_ui.html`, exposes JSON APIs for queue/run detail/annotation upsert, and reuses the existing `ReviewAnnotation` schema. The UI is a static HTML/CSS/JS page with a task list, run detail panels, annotation controls, and always-visible rules.

**Tech Stack:** Python standard library `http.server`, Pydantic, pytest, vanilla HTML/CSS/JavaScript.

---

### Task 1: Review API

**Files:**
- Create: `swetrace/labeling/review_server.py`
- Create: `scripts/serve_review_ui.sh`
- Test: `tests/test_review_server.py`

- [x] **Step 1: Write failing API tests**

Tests create a temporary runs root, review queue, annotations file, and report directory. They verify:
- `build_review_payload()` returns queue rows with annotation status.
- `load_run_detail()` returns task/report/label/patch/test log text for one run.
- `save_annotation()` upserts by `run_id` and validates that the run exists in the queue.

- [x] **Step 2: Run failing tests**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_review_server.py -q
```

Expected: fail because `swetrace.labeling.review_server` does not exist.

- [x] **Step 3: Implement API helpers**

Implement pure helper functions first:
- `read_jsonl(path: Path) -> list[dict]`
- `write_jsonl(path: Path, rows: list[ReviewAnnotation]) -> None`
- `build_review_payload(queue, annotations) -> dict`
- `load_run_detail(runs, run_id) -> dict`
- `save_annotation(queue, out, payload) -> dict`

- [x] **Step 4: Implement HTTP server**

Routes:
- `GET /` redirects to `/review`
- `GET /review` serves `reports/review_ui.html`
- `GET /api/review-items` returns queue plus annotation state
- `GET /api/run?run_id=...` returns run detail
- `POST /api/annotations` upserts annotation and returns summary

Bind default host `127.0.0.1`, default port `20039`.

### Task 2: Browser UI

**Files:**
- Create: `reports/review_ui.html`
- Modify: `reports/index.html`
- Modify: `reports/progress.html`
- Modify: `reports/project_overview.html`
- Test: `tests/test_reports_pages.py`

- [x] **Step 1: Write failing page tests**

Add assertions that `review_ui.html` exists and contains:
- `人工复核工作台`
- `patch_quality 标准`
- `SFT 可用标准`
- `DPO 可用标准`
- `保存标注`
- `/api/review-items`
- `/api/annotations`

- [x] **Step 2: Implement UI**

The page has:
- Left task list with status filters.
- Middle issue/gold patch/agent patch/test log/report panels.
- Right annotation form and rules.
- Save button posting JSON to `/api/annotations`.

- [x] **Step 3: Add navigation links**

Add `review_ui.html` / `/review` links to report entry pages and progress/overview pages.

### Task 3: Verification And Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/HANDOFF.md`
- Modify: `reports/progress.html`

- [x] **Step 1: Start local review server**

Run:

```bash
SWETRACE_PYTHON=/home/yiyuldx/birdNet/.venv/bin/python ./scripts/serve_review_ui.sh
```

Expected URL:

```text
http://127.0.0.1:20039/review
```

- [x] **Step 2: Verify with curl**

Run:

```bash
curl --noproxy '*' -fsS http://127.0.0.1:20039/api/review-items
curl --noproxy '*' -fsS 'http://127.0.0.1:20039/api/run?run_id=...'
```

- [x] **Step 3: Final verification**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
sg docker -c './scripts/check_docker.sh'
git diff --check
```

# Annotation Calibration Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static calibration page that teaches the human reviewer how to label SWE-Trace runs consistently.

**Architecture:** Add one static HTML report page and link it from existing report entry points. Keep the review server and annotation schema unchanged because this feature is reference material, not a data-model change.

**Tech Stack:** Static HTML/CSS, Python `html.parser` smoke tests, pytest.

---

### Task 1: Report Page Test

**Files:**
- Modify: `tests/test_reports_pages.py`

- [ ] **Step 1: Write the failing test**

Add a test that reads `reports/annotation_calibration.html`, feeds it to `_Parser`, and asserts the page contains:

```python
required_text = [
    "标注校准页",
    "OpenAI SWE-bench Verified",
    "underspecified",
    "false_negative",
    "patch_quality",
    "human_failure",
    "sft_usable",
    "dpo_usable",
    "close",
    "partial",
    "poor",
    "empty",
    "env_only",
    "人工复核工作台",
]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_reports_pages.py::test_annotation_calibration_page_documents_labeling_standards -q
```

Expected: FAIL because `reports/annotation_calibration.html` does not exist.

### Task 2: Static Calibration Page

**Files:**
- Create: `reports/annotation_calibration.html`

- [ ] **Step 1: Implement the page**

Create a static Chinese page with:

- Header navigation to `index.html`, `progress.html`, `project_overview.html`, and `http://127.0.0.1:20039/review`.
- A section explaining the five human-owned fields.
- A section summarizing OpenAI SWE-bench Verified public annotation concepts.
- A patch quality rubric table.
- A SFT/DPO decision table.
- Several example cards with recommended labels and note text.

- [ ] **Step 2: Run page test**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_reports_pages.py::test_annotation_calibration_page_documents_labeling_standards -q
```

Expected: PASS.

### Task 3: Navigation and Progress

**Files:**
- Modify: `reports/index.html`
- Modify: `reports/review_ui.html`
- Modify: `reports/progress.html`
- Modify: `tests/test_reports_pages.py`

- [ ] **Step 1: Add failing navigation assertions**

Extend tests to assert `annotation_calibration.html` appears in `index.html`, `review_ui.html`, and `progress.html`.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_reports_pages.py -q
```

Expected: FAIL until navigation is added.

- [ ] **Step 3: Add navigation and progress text**

Add the calibration page link to the report index, review UI nav, and progress page nav/timeline.

- [ ] **Step 4: Run report-page tests**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest tests/test_reports_pages.py -q
```

Expected: PASS.

### Task 4: Full Verification

**Files:**
- No additional files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
PYTHONPATH=/home/yiyuldx/swe /home/yiyuldx/birdNet/.venv/bin/python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Check git diff**

Run:

```bash
git status --short
git diff --stat
```

Expected: only docs, reports, and report tests changed.

- [ ] **Step 3: Commit and push**

Run:

```bash
git add docs/superpowers/specs/2026-06-05-annotation-calibration-page-design.md docs/superpowers/plans/2026-06-05-annotation-calibration-page.md tests/test_reports_pages.py reports/annotation_calibration.html reports/index.html reports/review_ui.html reports/progress.html
git commit -m "Add annotation calibration page"
git push
```

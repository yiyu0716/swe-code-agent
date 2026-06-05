# Annotation Calibration Page Design

## Goal

Add a static browser page that helps the human reviewer calibrate SWE-Trace labels before using the review workbench.

## Scope

The page explains only the manual fields the user must decide:

- `patch_quality`
- `human_failure`
- `sft_usable`
- `dpo_usable`
- `notes`

All run metadata, automatic labels, reviewer/source metadata, and timestamps remain system-owned.

## Content Design

The page will include:

- A short "what you need to label" section.
- A SWE-bench Verified reference section explaining how OpenAI's public human annotations judge task quality with `underspecified`, `false_negative`, `other_major_issues`, and `difficulty`.
- A SWE-Trace patch-quality rubric for `close`, `partial`, `poor`, `empty`, and `env_only`.
- A SFT/DPO decision table.
- Calibration examples that show what to inspect and how a concise `notes` field should read.

## Integration

The page will live at `reports/annotation_calibration.html`.

Navigation links will be added from:

- `reports/index.html`
- `reports/review_ui.html`
- `reports/progress.html`

No backend API or schema change is part of this feature.

## Testing

`tests/test_reports_pages.py` will parse the new page and assert that it contains the key labels, SWE-bench Verified references, calibration buckets, and review-workbench link. Existing report-page tests will be extended to check navigation.

# SWE-Trace

SWE-Trace is a two-week sprint project for Code Agent post-training data and evaluation.

The project focuses on collecting real Code Agent trajectories, diagnosing failure modes,
building SFT/DPO/RLVR-style datasets, and running small-scale post-training validation.

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

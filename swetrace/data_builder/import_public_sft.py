import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import typer

DEFAULT_RAW = Path(
    "/data/yiyuldx/swe/public_datasets/raw/R2EGym-SFT-Trajectories/data/train-00000-of-00001.parquet"
)
DEFAULT_OUT = Path("/data/yiyuldx/swe/outputs/datasets/public_sft_v0.1")
DEFAULT_EVAL_SET = Path("/data/yiyuldx/swe/eval_sets/qwen_baseline_v0")
DEFAULT_LOCAL_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/v0.2")

app = typer.Typer(add_completion=False)


def import_public_sft(
    *,
    raw: Path = DEFAULT_RAW,
    out: Path = DEFAULT_OUT,
    eval_set: Path | None = DEFAULT_EVAL_SET,
    local_dataset: Path | None = DEFAULT_LOCAL_DATASET,
    source_name: str = "R2E-Gym/R2EGym-SFT-Trajectories",
    version: str = "public-sft-v0.1",
    limit: int | None = None,
) -> dict[str, Any]:
    df = pd.read_parquet(raw)
    pollution_terms = _pollution_terms(eval_set=eval_set, local_dataset=local_dataset)
    imported: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for source_row, row in enumerate(df.to_dict(orient="records")):
        messages = _normalize_messages(row.get("messages"))
        if not _valid_messages(messages):
            excluded.append({"source_row": source_row, "reason": "invalid_messages"})
            continue
        text_blob = "\n".join(message["content"] for message in messages)
        matched_term = _pollution_match(text_blob, pollution_terms)
        if matched_term:
            excluded.append(
                {
                    "source_row": source_row,
                    "reason": "pollution_match",
                    "matched": matched_term,
                }
            )
            continue
        digest = _stable_hash(messages)
        if digest in seen_hashes:
            excluded.append({"source_row": source_row, "reason": "duplicate_messages"})
            continue
        seen_hashes.add(digest)
        imported.append(
            {
                "messages": messages,
                "metadata": {
                    "schema": "messages_v1",
                    "source": source_name,
                    "source_path": str(raw),
                    "source_row": source_row,
                    "message_count": len(messages),
                    "content_sha256": digest,
                    "issue_title": _extract_issue_title(text_blob),
                    "verified_by_swetrace": False,
                    "license_needs_review": True,
                },
            }
        )
        if limit is not None and len(imported) >= limit:
            break

    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "messages.jsonl", imported)
    _write_jsonl(out / "excluded.jsonl", excluded)
    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "source": {
            "name": source_name,
            "raw": str(raw),
            "source_rows": int(len(df)),
        },
        "schema": "messages_v1",
        "filters": {
            "requires_nonempty_messages": True,
            "requires_at_least_one_assistant_message": True,
            "dedupe_by_messages_sha256": True,
            "pollution_terms_from_eval_set": str(eval_set) if eval_set else None,
            "pollution_terms_from_local_dataset": str(local_dataset) if local_dataset else None,
            "limit": limit,
        },
        "counts": {
            "source_rows": int(len(df)),
            "imported": len(imported),
            "excluded": len(excluded),
            "pollution_terms": len(pollution_terms),
        },
        "quality_notes": [
            "Public rows do not carry SWE-Trace official_eval labels.",
            "Rows are suitable for public SFT warmup, not for trusted resolved-rate claims.",
            "Explicit task-id pollution is filtered; source rows without task ids cannot be proven fully uncontaminated.",
        ],
        "files": {
            "messages": str(out / "messages.jsonl"),
            "excluded": str(out / "excluded.jsonl"),
            "manifest": str(out / "manifest.json"),
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


@app.command()
def main(
    raw: Path = typer.Option(DEFAULT_RAW, exists=True, readable=True),
    out: Path = typer.Option(DEFAULT_OUT),
    eval_set: Path = typer.Option(DEFAULT_EVAL_SET),
    local_dataset: Path = typer.Option(DEFAULT_LOCAL_DATASET),
    source_name: str = typer.Option("R2E-Gym/R2EGym-SFT-Trajectories"),
    version: str = typer.Option("public-sft-v0.1"),
    limit: int | None = typer.Option(None, min=1),
) -> None:
    typer.echo(
        json.dumps(
            import_public_sft(
                raw=raw,
                out=out,
                eval_set=eval_set,
                local_dataset=local_dataset,
                source_name=source_name,
                version=version,
                limit=limit,
            ),
            ensure_ascii=False,
        )
    )


def _normalize_messages(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    messages = []
    if not isinstance(value, list):
        return []
    for item in value:
        if not isinstance(item, dict):
            return []
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"system", "user", "assistant", "tool"} or not content:
            return []
        messages.append({"role": role, "content": content})
    return messages


def _valid_messages(messages: list[dict[str, str]]) -> bool:
    return bool(messages) and any(message["role"] == "assistant" for message in messages)


def _pollution_terms(*, eval_set: Path | None, local_dataset: Path | None) -> set[str]:
    terms: set[str] = set()
    if eval_set:
        terms |= _task_ids_from_jsonl(eval_set / "tasks.jsonl")
    if local_dataset:
        for name in (
            "sft_patch.jsonl",
            "sft_plan.jsonl",
            "dpo_main.jsonl",
            "debug_cases.jsonl",
            "reward_logs.jsonl",
            "excluded.jsonl",
        ):
            terms |= _task_ids_from_jsonl(local_dataset / name)
    return {term for term in terms if len(term) >= 6}


def _task_ids_from_jsonl(path: Path) -> set[str]:
    if not path.exists():
        return set()
    task_ids: set[str] = set()
    for row in _read_jsonl(path):
        for value in (
            row.get("task_id"),
            row.get("instance_id"),
            row.get("meta", {}).get("task_id") if isinstance(row.get("meta"), dict) else None,
            row.get("meta", {}).get("instance_id") if isinstance(row.get("meta"), dict) else None,
        ):
            if isinstance(value, str) and value:
                task_ids.add(value)
    return task_ids


def _pollution_match(text: str, terms: set[str]) -> str | None:
    for term in sorted(terms):
        if term in text:
            return term
    return None


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_issue_title(text: str) -> str | None:
    match = re.search(r"\*\*Title:\*\*\s*(.+)", text)
    if not match:
        return None
    return match.group(1).strip()[:200]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    app()

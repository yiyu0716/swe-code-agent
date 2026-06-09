import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

DEFAULT_PUBLIC_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/public_sft_v0.1")
DEFAULT_LOCAL_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/v0.2")
DEFAULT_OUT = Path("/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1")

app = typer.Typer(add_completion=False)


def build_training_mix(
    *,
    public_dataset: Path = DEFAULT_PUBLIC_DATASET,
    local_dataset: Path = DEFAULT_LOCAL_DATASET,
    out: Path = DEFAULT_OUT,
    version: str = "sft-mix-v0.1",
) -> dict[str, Any]:
    public_rows = _read_jsonl(public_dataset / "messages.jsonl")
    local_rows = _read_jsonl(local_dataset / "sft_patch.jsonl")
    mixed: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in public_rows:
        messages = row["messages"]
        metadata = dict(row.get("metadata") or {})
        metadata["mix_source"] = "public_sft"
        _append_unique(mixed, seen, messages, metadata)

    local_imported = 0
    for row in local_rows:
        messages = _local_sft_to_messages(row)
        metadata = {
            "schema": "messages_v1",
            "mix_source": "local_v0.2_sft_patch",
            "source": "swetrace/v0.2/sft_patch",
            **(row.get("meta") or {}),
        }
        if _append_unique(mixed, seen, messages, metadata):
            local_imported += 1

    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "messages.jsonl", mixed)
    public_manifest = _read_optional_json(public_dataset / "manifest.json")
    local_manifest = _read_optional_json(local_dataset / "manifest.json")
    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "schema": "messages_v1",
        "sources": {
            "public_dataset": str(public_dataset),
            "public_version": public_manifest.get("version"),
            "local_dataset": str(local_dataset),
            "local_version": local_manifest.get("version"),
        },
        "counts": {
            "public_messages": len(public_rows),
            "local_sft": local_imported,
            "total_messages": len(mixed),
        },
        "mix_policy": [
            "Public messages provide scale for warmup SFT.",
            "Local v0.2 SFT patch rows provide official-evaluated high-trust calibration data.",
            "Rows are deduplicated by full messages sha256.",
        ],
        "files": {
            "messages": str(out / "messages.jsonl"),
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
    public_dataset: Path = typer.Option(DEFAULT_PUBLIC_DATASET, exists=True, file_okay=False),
    local_dataset: Path = typer.Option(DEFAULT_LOCAL_DATASET, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_OUT),
    version: str = typer.Option("sft-mix-v0.1"),
) -> None:
    typer.echo(
        json.dumps(
            build_training_mix(
                public_dataset=public_dataset,
                local_dataset=local_dataset,
                out=out,
                version=version,
            ),
            ensure_ascii=False,
        )
    )


def _local_sft_to_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    user = f"{row['instruction']}\n\n{row['input']}".strip()
    assistant = str(row["output"]).strip()
    return [
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]


def _append_unique(
    rows: list[dict[str, Any]],
    seen: set[str],
    messages: list[dict[str, str]],
    metadata: dict[str, Any],
) -> bool:
    digest = _stable_hash(messages)
    if digest in seen:
        return False
    seen.add(digest)
    rows.append(
        {
            "messages": messages,
            "metadata": {
                **metadata,
                "content_sha256": digest,
            },
        }
    )
    return True


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    app()

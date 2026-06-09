import json
from pathlib import Path

import pandas as pd

from swetrace.data_builder.import_public_sft import import_public_sft


def test_import_public_sft_normalizes_messages_and_filters_pollution(tmp_path) -> None:
    raw = tmp_path / "raw.parquet"
    good_messages = [
        {"role": "system", "content": "You are a coding agent."},
        {"role": "user", "content": "Consider issue clean-task. Please fix it."},
        {"role": "assistant", "content": "I will inspect and patch the code."},
    ]
    polluted_messages = [
        {"role": "user", "content": "This mentions eval-task-1 explicitly."},
        {"role": "assistant", "content": "Patch."},
    ]
    duplicate_messages = list(good_messages)
    invalid_messages = [{"role": "user", "content": "No assistant here."}]
    pd.DataFrame(
        {
            "messages": [
                good_messages,
                polluted_messages,
                duplicate_messages,
                invalid_messages,
            ]
        }
    ).to_parquet(raw)

    eval_set = tmp_path / "eval"
    eval_set.mkdir()
    (eval_set / "tasks.jsonl").write_text(json.dumps({"instance_id": "eval-task-1"}) + "\n")
    local_dataset = tmp_path / "v0.2"
    local_dataset.mkdir()
    (local_dataset / "sft_patch.jsonl").write_text(json.dumps({"task_id": "local-task-1"}) + "\n")

    out = tmp_path / "public_sft_v0.1"
    manifest = import_public_sft(
        raw=raw,
        out=out,
        eval_set=eval_set,
        local_dataset=local_dataset,
        source_name="fixture/public",
        version="public-sft-v0.1-test",
    )

    rows = [json.loads(line) for line in (out / "messages.jsonl").read_text().splitlines()]
    excluded = [json.loads(line) for line in (out / "excluded.jsonl").read_text().splitlines()]

    assert manifest["counts"]["imported"] == 1
    assert manifest["counts"]["excluded"] == 3
    assert rows[0]["messages"] == good_messages
    assert rows[0]["metadata"]["source"] == "fixture/public"
    assert rows[0]["metadata"]["source_row"] == 0
    assert rows[0]["metadata"]["schema"] == "messages_v1"
    assert {row["reason"] for row in excluded} == {
        "pollution_match",
        "duplicate_messages",
        "invalid_messages",
    }


def test_import_public_sft_can_limit_rows(tmp_path) -> None:
    raw = tmp_path / "raw.parquet"
    pd.DataFrame(
        {
            "messages": [
                [
                    {"role": "user", "content": f"Fix issue {index}."},
                    {"role": "assistant", "content": "Here is the patch."},
                ]
                for index in range(3)
            ]
        }
    ).to_parquet(raw)

    manifest = import_public_sft(
        raw=raw,
        out=tmp_path / "out",
        limit=2,
        source_name="fixture/public",
    )

    assert manifest["counts"]["source_rows"] == 3
    assert manifest["counts"]["imported"] == 2


def test_import_public_sft_escapes_newlines_as_jsonl(tmp_path) -> None:
    raw = tmp_path / "raw.parquet"
    pd.DataFrame(
        {
            "messages": [
                [
                    {"role": "user", "content": "Fix this\nwith two lines."},
                    {"role": "assistant", "content": "Patch line 1\nPatch line 2"},
                ]
            ]
        }
    ).to_parquet(raw)

    import_public_sft(
        raw=raw,
        out=tmp_path / "out",
        source_name="fixture/public",
        eval_set=None,
        local_dataset=None,
    )

    lines = (tmp_path / "out" / "messages.jsonl").read_text().splitlines()

    assert len(lines) == 1
    assert json.loads(lines[0])["messages"][0]["content"] == "Fix this\nwith two lines."


def test_import_public_sft_escapes_unicode_line_separator(tmp_path) -> None:
    raw = tmp_path / "raw.parquet"
    pd.DataFrame(
        {
            "messages": [
                [
                    {"role": "user", "content": "Fix this\u2028without breaking JSONL."},
                    {"role": "assistant", "content": "Patch."},
                ]
            ]
        }
    ).to_parquet(raw)

    import_public_sft(
        raw=raw,
        out=tmp_path / "out",
        source_name="fixture/public",
        eval_set=None,
        local_dataset=None,
    )

    raw_text = (tmp_path / "out" / "messages.jsonl").read_text()
    lines = raw_text.splitlines()

    assert len(lines) == 1
    assert "\\u2028" in raw_text
    assert json.loads(lines[0])["messages"][0]["content"] == "Fix this\u2028without breaking JSONL."

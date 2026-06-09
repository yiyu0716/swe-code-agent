import json

from swetrace.data_builder.build_training_mix import build_training_mix


def test_build_training_mix_combines_public_messages_and_local_sft(tmp_path) -> None:
    public = tmp_path / "public_sft_v0.1"
    public.mkdir()
    (public / "manifest.json").write_text(
        json.dumps({"version": "public-test", "counts": {"imported": 1}})
    )
    (public / "messages.jsonl").write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "Fix public issue."},
                    {"role": "assistant", "content": "Public patch."},
                ],
                "metadata": {"source": "public/source", "source_row": 0},
            }
        )
        + "\n"
    )

    local = tmp_path / "v0.2"
    local.mkdir()
    (local / "manifest.json").write_text(
        json.dumps({"version": "v0.2-test", "counts": {"sft_patch": 1}})
    )
    (local / "sft_patch.jsonl").write_text(
        json.dumps(
            {
                "type": "sft_patch",
                "instruction": "Produce a patch.",
                "input": "Issue:\nFix local issue.",
                "output": "diff --git a/a.py b/a.py\n",
                "meta": {"task_id": "local-task", "official_resolved": True},
            }
        )
        + "\n"
    )

    out = tmp_path / "sft_mix_v0.1"
    manifest = build_training_mix(
        public_dataset=public,
        local_dataset=local,
        out=out,
        version="sft-mix-test",
    )

    rows = [json.loads(line) for line in (out / "messages.jsonl").read_text().splitlines()]

    assert manifest["counts"]["public_messages"] == 1
    assert manifest["counts"]["local_sft"] == 1
    assert manifest["counts"]["total_messages"] == 2
    assert rows[0]["metadata"]["mix_source"] == "public_sft"
    assert rows[1]["metadata"]["mix_source"] == "local_v0.2_sft_patch"
    assert rows[1]["metadata"]["official_resolved"] is True
    assert rows[1]["messages"][-1]["content"].startswith("diff --git")

from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class _Parser(HTMLParser):
    pass


def test_project_overview_page_documents_full_pipeline() -> None:
    html_path = REPO_ROOT / "reports" / "project_overview.html"
    html = html_path.read_text()
    _Parser().feed(html)

    required_text = [
        "SWE-Trace 项目全景图",
        "端到端流程图",
        "SWE-bench Lite parquet",
        "mini-SWE-agent + DeepSeek",
        "RunStore 标准化产物",
        "SFT / DPO / Reward 数据",
        "人工复核与 annotation",
        "下一步人工介入",
        "/home/yiyuldx/swe",
        "/data/yiyuldx/swe",
        "manual_review_queue.jsonl",
        "manual_annotations.jsonl",
    ]
    for text in required_text:
        assert text in html


def test_progress_page_links_to_project_overview() -> None:
    html = (REPO_ROOT / "reports" / "progress.html").read_text()
    _Parser().feed(html)

    assert "project_overview.html" in html
    assert "项目全景图" in html
    assert "annotation_calibration.html" in html
    assert "标注校准页" in html
    assert "data_quality_report.html" in html
    assert "数据质量报告" in html
    assert "dpo_browser.html" in html
    assert "DPO 数据浏览器" in html
    assert "官方 SWE-bench 评测" in html
    assert "42 个官方 resolved" in html
    assert "SFT Patch" in html
    assert "DPO Main" in html
    assert "下载闭环门禁" in html
    assert "audit_swebench_closure" in html


def test_review_ui_page_explains_annotation_rules() -> None:
    html_path = REPO_ROOT / "reports" / "review_ui.html"
    html = html_path.read_text()
    _Parser().feed(html)

    required_text = [
        "人工复核工作台",
        "patch_quality 标准",
        "SFT 可用标准",
        "DPO 可用标准",
        "保存标注",
        "/api/review-items",
        "/api/annotations",
        "close",
        "partial",
        "poor",
        "env_only",
        "annotation_calibration.html",
        "标注校准页",
        "data_quality_report.html",
        "数据质量报告",
    ]
    for text in required_text:
        assert text in html


def test_annotation_calibration_page_documents_labeling_standards() -> None:
    html_path = REPO_ROOT / "reports" / "annotation_calibration.html"
    html = html_path.read_text()
    _Parser().feed(html)

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
        "data_quality_report.html",
        "数据质量报告",
    ]
    for text in required_text:
        assert text in html


def test_report_index_links_to_annotation_calibration_page_and_quality_report() -> None:
    html = (REPO_ROOT / "reports" / "index.html").read_text()
    _Parser().feed(html)

    assert "annotation_calibration.html" in html
    assert "标注校准页" in html
    assert "data_quality_report.html" in html
    assert "数据质量报告" in html
    assert "dpo_browser.html" in html
    assert "DPO 数据浏览器" in html


def test_data_quality_report_summarizes_annotations_and_filter_rules() -> None:
    html_path = REPO_ROOT / "reports" / "data_quality_report.html"
    html = html_path.read_text()
    _Parser().feed(html)

    required_text = [
        "数据质量报告",
        "manual_annotations.jsonl",
        "官方 SWE-bench 评测",
        "103 completed",
        "42 official resolved",
        "5 个 requests run",
        "SFT patch 42",
        "DPO main 61",
        "reward logs 103",
        "train_ready=true",
        "下载闭环审计",
        "missing_mini=0",
        "missing_official=0",
        "52 条 annotation",
        "close=23",
        "partial=19",
        "poor=2",
        "empty=2",
        "env_only=6",
        "仓库分布",
        "失败类型",
        "SFT 入选规则",
        "DPO 入选规则",
        "可用/不可用",
        "下一步",
    ]
    for text in required_text:
        assert text in html


def test_dpo_browser_page_documents_splits_and_loads_api() -> None:
    html_path = REPO_ROOT / "reports" / "dpo_browser.html"
    html = html_path.read_text()
    _Parser().feed(html)

    required_text = [
        "DPO 数据浏览器",
        "dpo_main.jsonl",
        "dpo_hard_negative.jsonl",
        "sft_sanity.jsonl",
        "/api/dpo-dataset",
        "chosen",
        "rejected",
        "patch_quality",
        "notes",
        "数据质量报告",
    ]
    for text in required_text:
        assert text in html

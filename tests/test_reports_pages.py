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

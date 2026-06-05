import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from swetrace.schema import ReviewAnnotation

DEFAULT_RUNS = Path("/data/yiyuldx/swe/runs")
DEFAULT_QUEUE = Path("/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl")
DEFAULT_ANNOTATIONS = Path("/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl")
DEFAULT_REPORTS = Path("/home/yiyuldx/swe/reports")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[ReviewAnnotation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json"), ensure_ascii=False) for row in rows)
        + ("\n" if rows else "")
    )


def build_review_payload(queue: Path = DEFAULT_QUEUE, annotations: Path = DEFAULT_ANNOTATIONS) -> dict:
    queue_rows = read_jsonl(queue)
    annotation_rows = {
        row["run_id"]: ReviewAnnotation.model_validate(row).model_dump(mode="json")
        for row in read_jsonl(annotations)
    }
    items = []
    for row in queue_rows:
        annotation = annotation_rows.get(row.get("run_id"))
        item = dict(row)
        item["is_annotated"] = annotation is not None
        item["annotation"] = annotation
        items.append(item)
    return {
        "total": len(items),
        "annotated": sum(1 for item in items if item["is_annotated"]),
        "items": items,
    }


def load_run_detail(runs: Path = DEFAULT_RUNS, run_id: str = "") -> dict:
    run_dir = runs / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run_id not found: {run_id}")
    return {
        "run_id": run_id,
        "task": _read_json(run_dir / "task.json"),
        "report": _read_json(run_dir / "report.json"),
        "label": _read_json(run_dir / "labels.json"),
        "patch": _read_text(run_dir / "patch.diff"),
        "test_log": _read_text(run_dir / "test.log"),
        "trajectory_preview": _trajectory_preview(run_dir / "trajectory.jsonl"),
        "paths": {
            "run_dir": str(run_dir),
            "task": str(run_dir / "task.json"),
            "report": str(run_dir / "report.json"),
            "label": str(run_dir / "labels.json"),
            "patch": str(run_dir / "patch.diff"),
            "test_log": str(run_dir / "test.log"),
            "trajectory": str(run_dir / "trajectory.jsonl"),
        },
    }


def save_annotation(
    queue: Path = DEFAULT_QUEUE,
    out: Path = DEFAULT_ANNOTATIONS,
    payload: dict | None = None,
) -> dict:
    payload = payload or {}
    run_id = str(payload.get("run_id") or "")
    queue_row = next((row for row in read_jsonl(queue) if row.get("run_id") == run_id), None)
    if queue_row is None:
        raise ValueError(f"run_id not found in review queue: {run_id}")
    annotation = ReviewAnnotation(
        run_id=run_id,
        task_id=str(queue_row.get("task_id") or ""),
        auto_primary_failure=str(queue_row.get("primary_failure") or ""),
        auto_severity=int(queue_row.get("severity") or 1),
        human_failure=str(payload.get("human_failure") or ""),
        patch_quality=str(payload.get("patch_quality") or ""),
        sft_usable=bool(payload.get("sft_usable")),
        dpo_usable=bool(payload.get("dpo_usable")),
        notes=payload.get("notes"),
        reviewer=str(payload.get("reviewer") or "manual"),
    )
    rows = [
        ReviewAnnotation.model_validate(row)
        for row in read_jsonl(out)
        if row.get("run_id") != run_id
    ]
    rows.append(annotation)
    rows.sort(key=lambda row: row.run_id)
    write_jsonl(out, rows)
    return {"annotations": len(rows), "updated": run_id, "out": str(out)}


def serve(
    host: str = "127.0.0.1",
    port: int = 20039,
    reports: Path = DEFAULT_REPORTS,
    runs: Path = DEFAULT_RUNS,
    queue: Path = DEFAULT_QUEUE,
    annotations: Path = DEFAULT_ANNOTATIONS,
) -> None:
    handler = _make_handler(reports=reports, runs=runs, queue=queue, annotations=annotations)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"SWE-Trace review UI: http://{host}:{port}/review", flush=True)
    server.serve_forever()


def _make_handler(reports: Path, runs: Path, queue: Path, annotations: Path):
    class ReviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    self.send_response(HTTPStatus.FOUND)
                    self.send_header("Location", "/review")
                    self.end_headers()
                    return
                if parsed.path == "/review":
                    self._send_html(reports / "review_ui.html")
                    return
                if parsed.path == "/api/review-items":
                    self._send_json(build_review_payload(queue=queue, annotations=annotations))
                    return
                if parsed.path == "/api/run":
                    run_id = parse_qs(parsed.query).get("run_id", [""])[0]
                    self._send_json(load_run_detail(runs=runs, run_id=run_id))
                    return
                html_path = _html_path_for_request(reports=reports, request_path=parsed.path)
                if html_path is not None:
                    self._send_html(html_path)
                    return
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            except Exception as exc:  # pragma: no cover - exercised by real server smoke.
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/api/annotations":
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode() or "{}")
                self._send_json(save_annotation(queue=queue, out=annotations, payload=payload))
            except Exception as exc:  # pragma: no cover - exercised by real server smoke.
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def _send_html(self, path: Path) -> None:
            if not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND, "HTML not found")
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ReviewHandler


def _html_path_for_request(reports: Path, request_path: str) -> Path | None:
    relative = unquote(request_path).lstrip("/")
    if not relative or "/" in relative or "\\" in relative or not relative.endswith(".html"):
        return None
    candidate = (reports / relative).resolve()
    reports_root = reports.resolve()
    if candidate.parent != reports_root:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def _trajectory_preview(path: Path, limit: int = 12) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        step = json.loads(line)
        rows.append(
            {
                "step_id": step.get("step_id"),
                "phase": step.get("phase"),
                "tool_name": step.get("tool_name"),
                "model_output": str(step.get("model_output") or "")[:500],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local SWE-Trace review UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=20039)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    args = parser.parse_args()
    serve(
        host=args.host,
        port=args.port,
        reports=args.reports,
        runs=args.runs,
        queue=args.queue,
        annotations=args.annotations,
    )


if __name__ == "__main__":
    main()

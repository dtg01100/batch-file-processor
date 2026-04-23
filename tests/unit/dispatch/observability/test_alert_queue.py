# tests/unit/dispatch/observability/test_alert_queue.py
import json


class TestAlertQueue:
    def test_enqueue_adds_json_line(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        alert = {"error_type": "ValidationError", "message": "bad file"}
        queue.enqueue(alert)
        lines = (tmp_path / "queue.jsonl").read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["error_type"] == "ValidationError"

    def test_dequeue_returns_and_removes_first(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        queue._queue_path.write_text(json.dumps({"id": 1}) + "\n" + json.dumps({"id": 2}) + "\n")
        result = queue.dequeue()
        assert result["id"] == 1
        remaining = queue.peek()
        assert len(remaining) == 1
        assert remaining[0]["id"] == 2

    def test_dequeue_empty_returns_none(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        assert queue.dequeue() is None

    def test_mark_failed_writes_to_failures_log(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(
            queue_path=str(tmp_path / "queue.jsonl"),
            failures_path=str(tmp_path / "failures.log"),
        )
        queue.mark_failed({"error": "boom"}, "SMTP connection refused")
        assert (tmp_path / "failures.log").exists()
        assert "boom" in (tmp_path / "failures.log").read_text()

    def test_enqueue_sets_retry_count(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        queue.enqueue({"error": "test"})
        stored = queue.peek()[0]
        assert stored["retry_count"] == 0

    def test_retry_count_preserved_on_enqueue(self, tmp_path):
        from dispatch.observability.alert_queue import AlertQueue

        queue = AlertQueue(queue_path=str(tmp_path / "queue.jsonl"))
        queue.enqueue({"error": "test", "retry_count": 3})
        stored = queue.peek()[0]
        assert stored["retry_count"] == 3

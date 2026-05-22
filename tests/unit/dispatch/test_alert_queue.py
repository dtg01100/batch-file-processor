"""Tests for dispatch/observability/alert_queue.py"""

from __future__ import annotations

import json
from pathlib import Path

from dispatch.observability.alert_queue import AlertQueue


class TestAlertQueueMalformedLines:
    """Test AlertQueue handling of malformed lines."""

    def test_peek_skips_malformed_json_lines(self, tmp_path: Path) -> None:
        """peek() should skip lines that are not valid JSON."""
        queue_path = tmp_path / "alert_queue.jsonl"
        failures_path = tmp_path / "failures.json"

        # Write valid and invalid JSON lines
        with open(queue_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"test": 1}) + "\n")
            f.write("not valid json\n")
            f.write(json.dumps({"test": 2}) + "\n")
            f.write("also invalid\n")
            f.write(json.dumps({"test": 3}) + "\n")

        aq = AlertQueue(queue_path=queue_path, failures_path=failures_path)

        alerts = aq.peek()

        assert len(alerts) == 3
        assert alerts[0]["test"] == 1
        assert alerts[1]["test"] == 2
        assert alerts[2]["test"] == 3

    def test_peek_skips_empty_lines(self, tmp_path: Path) -> None:
        """peek() should skip empty lines."""
        queue_path = tmp_path / "alert_queue.jsonl"
        failures_path = tmp_path / "failures.json"

        with open(queue_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"test": 1}) + "\n")
            f.write("\n")
            f.write("   \n")
            f.write(json.dumps({"test": 2}) + "\n")

        aq = AlertQueue(queue_path=queue_path, failures_path=failures_path)

        alerts = aq.peek()

        assert len(alerts) == 2
        assert alerts[0]["test"] == 1
        assert alerts[1]["test"] == 2

    def test_dequeue_with_malformed_lines(self, tmp_path: Path) -> None:
        """dequeue() should return first valid alert and skip malformed lines."""
        queue_path = tmp_path / "alert_queue.jsonl"
        failures_path = tmp_path / "failures.json"

        with open(queue_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"test": 1}) + "\n")
            f.write("invalid\n")
            f.write(json.dumps({"test": 2}) + "\n")

        aq = AlertQueue(queue_path=queue_path, failures_path=failures_path)

        first = aq.dequeue()
        remaining = aq.peek()

        assert first["test"] == 1
        assert len(remaining) == 1
        assert remaining[0]["test"] == 2

    def test_peek_handles_partial_json(self, tmp_path: Path) -> None:
        """peek() should skip partial/incomplete JSON lines."""
        queue_path = tmp_path / "alert_queue.jsonl"
        failures_path = tmp_path / "failures.json"

        with open(queue_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"valid": True}) + "\n")
            f.write('{"incomplete":\n')
            f.write(json.dumps({"also": "valid"}) + "\n")

        aq = AlertQueue(queue_path=queue_path, failures_path=failures_path)

        alerts = aq.peek()

        assert len(alerts) == 2
        assert alerts[0]["valid"] is True
        assert alerts[1]["also"] == "valid"

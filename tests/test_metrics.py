import os
import tempfile

import src.storage.sqlite as sqlite
from src.utils.metrics import emit_metric, measure_stage


def test_emit_metric_without_external_dependency():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        event = emit_metric("unit_event", count=2, source="tests", reason="ok", metadata={"a": 1})
    sqlite.DB_PATH = original

    assert event["event_name"] == "unit_event"
    assert event["count"] == 2
    assert event["source"] == "tests"


def test_measure_stage_emits_duration_metric():
    original = sqlite.DB_PATH
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite.DB_PATH = os.path.join(tmpdir, "test.db")
        with measure_stage("unit_stage", source="tests"):
            value = 1 + 1
    sqlite.DB_PATH = original

    assert value == 2

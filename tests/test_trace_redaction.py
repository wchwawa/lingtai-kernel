import json

from lingtai_kernel.services.logging import CompositeLoggingService, JSONLLoggingService
from lingtai_kernel.trace_redaction import redact_for_trajectory, redact_text


def test_redact_text_common_secret_shapes():
    telegram_like = "123456789" + ":" + "A" * 35
    openai_like = "sk" + "-proj-" + "B" * 60
    bearer_like = "C" * 36
    text = (
        f"token={telegram_like} "
        f"api_key='{openai_like}' "
        f"Authorization: Bearer {bearer_like}"
    )
    redacted = redact_text(text)
    assert telegram_like not in redacted
    assert openai_like not in redacted
    assert f"Bearer {bearer_like}" not in redacted
    assert "<REDACTED:" in redacted


def test_redact_for_trajectory_redacts_secret_mapping_values_without_mutation():
    event = {
        "type": "tool_result",
        "tool_args": {
            "token": "plain-app-password-value",
            "safe": "keep me",
        },
    }
    redacted = redact_for_trajectory(event)
    assert event["tool_args"]["token"] == "plain-app-password-value"
    assert redacted["tool_args"]["token"] == "<REDACTED:secret>"
    assert redacted["tool_args"]["safe"] == "keep me"


def test_composite_logging_redacts_before_jsonl_write_and_sqlite_index(tmp_path):
    jsonl = JSONLLoggingService(tmp_path / "events.jsonl")
    service = CompositeLoggingService(jsonl)
    service.log({
        "type": "tool_result",
        "ts": 1.0,
        "tool_args": {"password": "correct-horse-battery-staple"},
        "result": "token=" + "123456789" + ":" + "A" * 35,
    })
    service.close()

    line = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "correct-horse-battery-staple" not in line
    assert "123456789" + ":" not in line
    record = json.loads(line)
    assert record["tool_args"]["password"] == "<REDACTED:secret>"

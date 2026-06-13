import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_serving_support.py"

sys.path.insert(0, ROOT.as_posix())
from scripts.aios_serving_support import (
    build_admin_summary,
    build_incident_timeline,
    project_support,
    redact_event,
)


def _make_event(
    user_id: str = "user1",
    incident_id: str = "inc-001",
    stage: str = "dispatch",
    status: str = "failed",
    **extra: object,
) -> dict:
    base = {
        "user_id": user_id,
        "incident_id": incident_id,
        "session_id": "sess-001",
        "stage": stage,
        "status": status,
        "timestamp": "2026-06-14T01:00:00+09:00",
        "error_type": "provider_timeout",
        "severity": "high",
        "retryable": True,
    }
    base.update(extra)
    return base


# ── redaction tests ──────────────────────────────────────────────────

class RedactionTest(unittest.TestCase):
    """raw_content_redaction_test evidence."""

    def test_message_body_redacted(self) -> None:
        event = _make_event(message_body="Hello, please help me with...")
        result = redact_event(event)
        self.assertEqual(result["message_body"], "[REDACTED]")

    def test_memory_body_redacted(self) -> None:
        event = _make_event(memory_body="User prefers dark mode and lives in Seoul")
        result = redact_event(event)
        self.assertEqual(result["memory_body"], "[REDACTED]")

    def test_provider_output_redacted(self) -> None:
        event = _make_event(provider_output="Claude responded: here is the plan...")
        result = redact_event(event)
        self.assertEqual(result["provider_output"], "[REDACTED]")

    def test_tool_output_redacted(self) -> None:
        event = _make_event(tool_output="file contents: import os; ...")
        result = redact_event(event)
        self.assertEqual(result["tool_output"], "[REDACTED]")

    def test_prompt_text_redacted(self) -> None:
        event = _make_event(prompt_text="You are a helpful assistant...")
        result = redact_event(event)
        self.assertEqual(result["prompt_text"], "[REDACTED]")

    def test_credential_value_redacted(self) -> None:
        event = _make_event(credential_value="sk-abc123def456")
        result = redact_event(event)
        self.assertEqual(result["credential_value"], "[REDACTED]")

    def test_token_field_redacted(self) -> None:
        event = _make_event(token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        result = redact_event(event)
        self.assertEqual(result["token"], "[REDACTED]")

    def test_private_export_redacted(self) -> None:
        event = _make_event(private_export="/home/user/exports/data.csv")
        result = redact_event(event)
        self.assertEqual(result["private_export"], "[REDACTED]")

    def test_credential_pattern_in_arbitrary_field_redacted(self) -> None:
        event = _make_event(some_field="key is sk-proj-abcdefghijklmnopqrstuvwxyz")
        result = redact_event(event)
        self.assertEqual(result["some_field"], "[REDACTED:credential_pattern]")

    def test_jwt_pattern_in_arbitrary_field_redacted(self) -> None:
        event = _make_event(auth_header="eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0")
        result = redact_event(event)
        self.assertEqual(result["auth_header"], "[REDACTED:credential_pattern]")

    def test_nested_dict_raw_fields_redacted(self) -> None:
        event = _make_event(
            details={"message_body": "private text", "stage": "dispatch"}
        )
        result = redact_event(event)
        self.assertEqual(result["details"]["message_body"], "[REDACTED]")
        self.assertEqual(result["details"]["stage"], "dispatch")

    def test_safe_metadata_preserved(self) -> None:
        event = _make_event()
        result = redact_event(event)
        self.assertEqual(result["stage"], "dispatch")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_type"], "provider_timeout")
        self.assertEqual(result["severity"], "high")
        self.assertTrue(result["retryable"])
        self.assertEqual(result["timestamp"], "2026-06-14T01:00:00+09:00")
        self.assertEqual(result["incident_id"], "inc-001")

    def test_all_raw_fields_absent_from_redacted_output(self) -> None:
        event = _make_event(
            message_body="msg",
            memory_body="mem",
            provider_output="prov",
            tool_output="tool",
            prompt_text="prompt",
            credential_value="cred",
            token="tok",
            private_export="export",
            raw_provider_log="log",
            raw_tool_response="resp",
            user_message="um",
            raw_output="raw",
            secret="sec",
            password="pw",
            api_key="ak",
            auth_token="at",
            bearer_token="bt",
            access_token="act",
            refresh_token="rt",
        )
        result = redact_event(event)
        for key in (
            "message_body", "memory_body", "provider_output", "tool_output",
            "prompt_text", "credential_value", "token", "private_export",
            "raw_provider_log", "raw_tool_response", "user_message", "raw_output",
            "secret", "password", "api_key", "auth_token", "bearer_token",
            "access_token", "refresh_token",
        ):
            self.assertEqual(result[key], "[REDACTED]", f"{key} was not redacted")


# ── cross-user incident denial tests ────────────────────────────────

class CrossUserDenialTest(unittest.TestCase):
    """cross_user_incident_denial_test evidence."""

    def test_timeline_denied_when_user_does_not_match(self) -> None:
        events = [_make_event(user_id="owner_user")]
        result = build_incident_timeline(events, user_id="attacker_user")
        self.assertEqual(result["status"], "denied")
        self.assertEqual(result["reason"], "requesting_user_does_not_match_incident_owner")
        self.assertEqual(result["timeline"], [])

    def test_timeline_denied_via_project_support(self) -> None:
        events = [_make_event(user_id="owner_user")]
        result = project_support(events, user_id="other_user", mode="timeline")
        self.assertEqual(result["status"], "denied")

    def test_timeline_allowed_for_matching_user(self) -> None:
        events = [_make_event(user_id="user1")]
        result = build_incident_timeline(events, user_id="user1")
        self.assertEqual(result["status"], "ok")
        self.assertGreater(len(result["timeline"]), 0)

    def test_empty_events_return_empty_not_denied(self) -> None:
        result = build_incident_timeline([], user_id="user1")
        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["timeline"], [])


# ── incident timeline tests ─────────────────────────────────────────

class IncidentTimelineTest(unittest.TestCase):
    """aios.serving_incident_timeline.v1 evidence."""

    def test_timeline_schema_version(self) -> None:
        events = [_make_event()]
        result = build_incident_timeline(events, user_id="user1")
        self.assertEqual(result["schema_version"], "aios.serving_incident_timeline.v1")

    def test_timeline_preserves_stage_status_error_metadata(self) -> None:
        events = [
            _make_event(stage="dispatch", status="failed", error_type="provider_timeout", severity="high"),
            _make_event(stage="execution", status="success", error_type="none", severity="low"),
        ]
        result = build_incident_timeline(events, user_id="user1")
        self.assertEqual(len(result["timeline"]), 2)
        self.assertEqual(result["timeline"][0]["stage"], "dispatch")
        self.assertEqual(result["timeline"][0]["status"], "failed")
        self.assertEqual(result["timeline"][0]["error_type"], "provider_timeout")
        self.assertEqual(result["timeline"][0]["severity"], "high")
        self.assertEqual(result["timeline"][1]["stage"], "execution")
        self.assertEqual(result["timeline"][1]["status"], "success")

    def test_timeline_entries_have_opaque_refs(self) -> None:
        events = [_make_event(incident_id="inc-99")]
        result = build_incident_timeline(events, user_id="user1")
        entry = result["timeline"][0]
        self.assertIn("ref", entry)
        self.assertTrue(entry["ref"].startswith("opaque:"))

    def test_timeline_does_not_contain_raw_fields(self) -> None:
        events = [_make_event(
            message_body="private message",
            memory_body="private memory",
            provider_output="raw provider output",
            prompt_text="system prompt",
            credential_value="sk-secret123456789012345",
        )]
        result = build_incident_timeline(events, user_id="user1")
        timeline_json = json.dumps(result)
        self.assertNotIn("private message", timeline_json)
        self.assertNotIn("private memory", timeline_json)
        self.assertNotIn("raw provider output", timeline_json)
        self.assertNotIn("system prompt", timeline_json)
        self.assertNotIn("sk-secret", timeline_json)

    def test_timeline_retryable_preserved(self) -> None:
        events = [_make_event(retryable=False)]
        result = build_incident_timeline(events, user_id="user1")
        self.assertFalse(result["timeline"][0]["retryable"])

    def test_timeline_filters_to_requesting_user(self) -> None:
        events = [
            _make_event(user_id="user1", stage="a"),
            _make_event(user_id="user2", stage="b"),
            _make_event(user_id="user1", stage="c"),
        ]
        result = build_incident_timeline(events, user_id="user1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["event_count"], 2)
        stages = [e["stage"] for e in result["timeline"]]
        self.assertEqual(stages, ["a", "c"])


# ── admin summary tests ─────────────────────────────────────────────

class AdminSummaryTest(unittest.TestCase):
    """aios.serving_support_projection.v1 admin_summary evidence."""

    def test_admin_summary_schema_version(self) -> None:
        result = build_admin_summary([_make_event()])
        self.assertEqual(result["schema_version"], "aios.serving_support_projection.v1")
        self.assertEqual(result["mode"], "admin_summary")

    def test_admin_summary_counts_by_stage(self) -> None:
        events = [
            _make_event(stage="dispatch"),
            _make_event(stage="dispatch"),
            _make_event(stage="execution"),
        ]
        result = build_admin_summary(events)
        self.assertEqual(result["by_stage"]["dispatch"], 2)
        self.assertEqual(result["by_stage"]["execution"], 1)

    def test_admin_summary_counts_by_status(self) -> None:
        events = [
            _make_event(status="failed"),
            _make_event(status="success"),
            _make_event(status="failed"),
        ]
        result = build_admin_summary(events)
        self.assertEqual(result["by_status"]["failed"], 2)
        self.assertEqual(result["by_status"]["success"], 1)

    def test_admin_summary_distinct_users(self) -> None:
        events = [
            _make_event(user_id="u1"),
            _make_event(user_id="u2"),
            _make_event(user_id="u1"),
        ]
        result = build_admin_summary(events)
        self.assertEqual(result["distinct_users"], 2)

    def test_admin_summary_does_not_contain_raw_content(self) -> None:
        events = [_make_event(
            message_body="sensitive user content",
            memory_body="private memory",
            provider_output="raw llm output",
            credential_value="sk-secret123456789012345",
        )]
        result = build_admin_summary(events)
        summary_json = json.dumps(result)
        self.assertNotIn("sensitive user content", summary_json)
        self.assertNotIn("private memory", summary_json)
        self.assertNotIn("raw llm output", summary_json)
        self.assertNotIn("sk-secret", summary_json)

    def test_admin_summary_does_not_expose_user_ids(self) -> None:
        events = [_make_event(user_id="specific_user_name")]
        result = build_admin_summary(events)
        summary_json = json.dumps(result)
        self.assertNotIn("specific_user_name", summary_json)

    def test_admin_summary_error_type_and_severity_counts(self) -> None:
        events = [
            _make_event(error_type="timeout", severity="high"),
            _make_event(error_type="timeout", severity="low"),
            _make_event(error_type="auth_fail", severity="high"),
        ]
        result = build_admin_summary(events)
        self.assertEqual(result["by_error_type"]["timeout"], 2)
        self.assertEqual(result["by_error_type"]["auth_fail"], 1)
        self.assertEqual(result["by_severity"]["high"], 2)
        self.assertEqual(result["by_severity"]["low"], 1)


# ── project_support entry point tests ───────────────────────────────

class ProjectSupportTest(unittest.TestCase):
    def test_timeline_mode_requires_user_id(self) -> None:
        result = project_support([_make_event()], mode="timeline")
        self.assertEqual(result["status"], "error")
        self.assertIn("user_id_required", result["reason"])

    def test_unknown_mode_returns_error(self) -> None:
        result = project_support([], mode="invalid")
        self.assertEqual(result["status"], "error")

    def test_admin_mode_via_project_support(self) -> None:
        events = [_make_event(), _make_event()]
        result = project_support(events, mode="admin")
        self.assertEqual(result["mode"], "admin_summary")
        self.assertEqual(result["total_events"], 2)


# ── CLI tests ───────────────────────────────────────────────────────

class CLITest(unittest.TestCase):
    def _run(self, stdin_data: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            input=stdin_data,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cli_timeline_json(self) -> None:
        events = [_make_event(message_body="private")]
        result = self._run(
            json.dumps(events),
            "project", "--mode", "timeline", "--user-id", "user1", "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertNotIn("private", json.dumps(payload["projection"]["timeline"]))

    def test_cli_admin_json(self) -> None:
        events = [_make_event(), _make_event(stage="execution")]
        result = self._run(
            json.dumps(events),
            "project", "--mode", "admin", "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["projection"]["total_events"], 2)

    def test_cli_invalid_json_returns_error(self) -> None:
        result = self._run(
            "not json",
            "project", "--mode", "admin", "--json",
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()

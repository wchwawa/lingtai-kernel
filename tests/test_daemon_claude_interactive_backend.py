"""Tests for the interactive Claude daemon backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
import textwrap
import threading
from unittest.mock import MagicMock, patch

from lingtai.agent import Agent
from lingtai.core.daemon import get_schema
from lingtai.core.daemon.claude_interactive import run_claude_interactive
from lingtai.core.daemon.run_dir import DaemonRunDir
from lingtai_kernel.config import AgentConfig


def _make_agent(tmp_path: Path) -> Agent:
    svc = MagicMock()
    svc.provider = "mock"
    svc.model = "mock-model"
    svc.create_session = MagicMock()
    svc.make_tool_result = MagicMock()
    return Agent(
        svc,
        working_dir=tmp_path / "daemon-agent",
        capabilities=["daemon"],
        config=AgentConfig(),
    )


def _make_run_dir(tmp_path: Path, *, backend: str = "claude") -> DaemonRunDir:
    parent = tmp_path / "daemon-agent"
    parent.mkdir(parents=True, exist_ok=True)
    return DaemonRunDir(
        parent_working_dir=parent,
        handle="em-1",
        task="interactive task",
        tools=[],
        model=backend,
        max_turns=30,
        timeout_s=30,
        parent_addr="daemon-agent",
        parent_pid=os.getpid(),
        system_prompt="[claude interactive backend]",
        backend=backend,
    )


def _write_fake_claude(bin_dir: Path, transcript_text: str = "fake interactive answer") -> Path:
    fake = bin_dir / "claude"
    fake.write_text(textwrap.dedent(f"""
        #!/usr/bin/env python3
        from __future__ import annotations
        import json
        from pathlib import Path
        import subprocess
        import sys
        import time

        args = sys.argv[1:]
        settings = None
        resume_session = None
        i = 0
        while i < len(args):
            if args[i] == "--settings":
                settings = json.loads(args[i + 1])
                i += 2
            elif args[i] == "--resume":
                resume_session = args[i + 1]
                i += 2
            else:
                i += 1
        if settings is None:
            raise SystemExit("missing --settings")

        def hook_command(event):
            for group in settings["hooks"][event]:
                for hook in group["hooks"]:
                    return hook["command"]
            raise SystemExit(f"missing hook {{event}}")

        session_id = resume_session or "claude-session-123"
        transcript = Path.cwd() / "fake-claude-transcript.jsonl"

        # Exercise the bridge's terminal probe responder.  The fake does not
        # need the responses; real Claude/Ink does.
        sys.stdout.buffer.write(b"\\x1b[c\\x1b[>c\\x1b[6n\\x1b[>q\\x1b[18t")
        sys.stdout.buffer.flush()

        start_payload = {{"session_id": session_id}}
        subprocess.run(
            hook_command("SessionStart"),
            input=json.dumps(start_payload),
            text=True,
            shell=True,
            check=True,
        )

        # Read the prompt pasted by the bridge.  It arrives as bracketed paste
        # plus CR; stop at CR/LF so the process can finish deterministically.
        got = bytearray()
        deadline = time.time() + 5
        while time.time() < deadline:
            ch = sys.stdin.buffer.read(1)
            if not ch:
                time.sleep(0.01)
                continue
            got += ch
            if ch in (b"\\r", b"\\n"):
                break
        if b"interactive task" not in got and b"follow-up message" not in got:
            raise SystemExit(f"prompt not received: {{got!r}}")

        with transcript.open("w", encoding="utf-8") as f:
            f.write(json.dumps({{"type": "custom-title", "customTitle": "em-1", "sessionId": session_id}}) + "\\n")
            f.write(json.dumps({{
                "type": "assistant",
                "session_id": session_id,
                "message": {{
                    "role": "assistant",
                    "content": [{{"type": "text", "text": {transcript_text!r}}}],
                }},
            }}) + "\\n")

        stop_payload = {{
            "session_id": session_id,
            "transcript_path": str(transcript),
            "last_assistant_message": {transcript_text!r},
        }}
        subprocess.run(
            hook_command("Stop"),
            input=json.dumps(stop_payload),
            text=True,
            shell=True,
            check=True,
        )
    """).lstrip(), encoding="utf-8")
    fake.chmod(0o755)
    return fake


def test_schema_exposes_interactive_and_print_mode_claude_backends():
    backend = get_schema()["properties"]["backend"]
    assert "claude" in backend["enum"]
    assert "claude-interactive" in backend["enum"]
    assert "claude-p" in backend["enum"]
    # Backward compatibility for existing callers and stored daemon entries.
    assert "claude-code" in backend["enum"]


def test_emanate_claude_dispatches_interactive_runner(tmp_path):
    agent = _make_agent(tmp_path)
    mgr = agent.get_capability("daemon")
    captured = {}

    def fake_run(em_id, run_dir, task, cancel_event, timeout_event, backend_argv=None):
        captured["backend"] = run_dir._state["backend"]
        captured["task"] = task
        captured["backend_argv"] = list(backend_argv or [])
        run_dir._state["claude_session_id"] = "session-from-fake"
        run_dir._atomic_write_json(run_dir.daemon_json_path, run_dir._state)
        run_dir.mark_done("done")
        return "done"

    with patch.object(mgr, "_run_claude_interactive_emanation", side_effect=fake_run):
        result = mgr.handle({
            "action": "emanate",
            "backend": "claude",
            "tasks": [{
                "task": "Use interactive Claude",
                "tools": [],
                "backend_options": {"model": "opus", "verbose": True},
            }],
        })
        assert result["status"] == "dispatched"
        em_id = result["ids"][0]
        mgr._emanations[em_id]["future"].result(timeout=5)

    assert captured == {
        "backend": "claude",
        "task": "Use interactive Claude",
        "backend_argv": ["--model", "opus", "--verbose"],
    }


def test_emanate_claude_p_dispatches_legacy_print_runner(tmp_path):
    agent = _make_agent(tmp_path)
    mgr = agent.get_capability("daemon")
    captured = {}

    def fake_run(em_id, run_dir, task, cancel_event, timeout_event, backend_argv=None):
        captured["backend"] = run_dir._state["backend"]
        captured["task"] = task
        run_dir.mark_done("done")
        return "done"

    with patch.object(mgr, "_run_claude_code_emanation", side_effect=fake_run):
        result = mgr.handle({
            "action": "emanate",
            "backend": "claude-p",
            "tasks": [{"task": "Use print mode", "tools": []}],
        })
        assert result["status"] == "dispatched"
        em_id = result["ids"][0]
        mgr._emanations[em_id]["future"].result(timeout=5)

    assert captured == {"backend": "claude-p", "task": "Use print mode"}



def test_claude_reserved_backend_options_are_rejected(tmp_path):
    agent = _make_agent(tmp_path)
    mgr = agent.get_capability("daemon")

    result = mgr.handle({
        "action": "emanate",
        "backend": "claude",
        "tasks": [{
            "task": "should not spawn",
            "tools": [],
            "backend_options": {"settings": "{}"},
        }],
    })

    assert result["status"] == "error"
    assert "--settings is reserved" in result["message"]
    assert mgr._emanations == {}


def test_run_claude_interactive_fake_cli_hooks_and_transcript(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_claude(bin_dir, transcript_text="fake interactive answer")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    run_dir = _make_run_dir(tmp_path)
    result = run_claude_interactive(
        em_id="em-1",
        run_dir=run_dir,
        working_dir=tmp_path / "daemon-agent",
        task="interactive task",
        cancel_event=threading.Event(),
        env=os.environ.copy(),
    )

    assert result.final_text == "fake interactive answer"
    assert result.session_id == "claude-session-123"
    assert result.transcript_path is not None
    assert result.raw_pty_log_path is not None

    state = json.loads(run_dir.daemon_json_path.read_text())
    assert state["claude_session_id"] == "claude-session-123"
    assert state["claude_interactive_transcript_path"] == result.transcript_path
    assert state["claude_interactive_prompt_sent"] is True
    assert Path(state["claude_interactive_raw_pty_log"]).exists()

    events = run_dir.events_path.read_text(encoding="utf-8")
    assert "fake interactive answer" in events
    assert "claude interactive SessionStart" in events
    assert "claude interactive Stop" in events

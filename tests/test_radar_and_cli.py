import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from core import radar_workflow
from core.state import JobDescription, MatchResult, SkillGap
from skills.job_radar import handler as radar


def test_radar_legacy_entrypoints_and_partial_failure(profile, monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(radar, "PROJECT_ROOT", tmp_path)
    def parse(text, provider=None):
        if text == "SENSITIVE broken JD":
            raise ValueError("SENSITIVE response data")
        return JobDescription(company=text, role="研发", raw_text=text)
    def match(profile, job, provider=None):
        return MatchResult(
            score={"low": 60, "high": 90}[job.company], overview="合成判断",
            missing_skills=[SkillGap(skill="测试缺口", status="unknown")],
        )
    monkeypatch.setattr(radar_workflow, "parse_jd", parse)
    monkeypatch.setattr(radar_workflow, "match_profile_with_jd", match)
    results = radar.scan_opportunities(["low", "", "SENSITIVE broken JD", "high"], profile)
    assert [item.company for item in results] == ["high", "low"]
    assert [item.rank for item in results] == [1, 2]
    assert [item.tier for item in results] == ["优先主投", "暂缓考虑"]
    assert "SENSITIVE" not in caplog.text
    jd_dir = tmp_path / "jds"
    jd_dir.mkdir()
    (jd_dir / "a.txt").write_text("low", encoding="utf-8")
    (jd_dir / "b.txt").write_text("high", encoding="utf-8")
    from skills.job_radar import scan_from_directory, run_radar_pipeline
    assert [item.score for item in scan_from_directory(jd_dir, profile)] == [90, 60]
    report = run_radar_pipeline(jd_dir, profile)
    assert report.total_scanned == 2
    assert Path(report.report_file_path).is_file()


def test_no_business_module_imports_another_business_module():
    root = Path(__file__).resolve().parents[1] / "skills"
    violations = []
    for path in root.rglob("*.py"):
        if path.parent == root:
            continue
        own_module = path.relative_to(root).parts[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            for name in names:
                parts = name.split(".")
                if len(parts) > 1 and parts[0] == "skills" and parts[1] != own_module:
                    violations.append(f"{path.name}: {name}")
    assert violations == []


@pytest.mark.parametrize("command", [
    ["--help"], ["tailor", "--help"], ["interview", "--help"], ["resume", "--help"],
    ["radar", "--help"], ["tracker", "--help"], ["mcp", "--help"],
])
def test_cli_old_command_help_is_available(command):
    from main import app
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output


def test_cli_old_interview_options_and_new_optional_context(monkeypatch):
    import run_interview
    from main import app
    captured = []
    monkeypatch.setattr(run_interview, "main", lambda **kwargs: captured.append(kwargs))
    result = CliRunner().invoke(app, [
        "interview", "--role", "strict_architect", "--company", "合成企业",
        "--target-role", "前端开发", "--provider", "unit",
    ])
    assert result.exit_code == 0, result.output
    assert captured[0]["mode"] == "simulation"
    assert captured[0]["jd"] is None
    result = CliRunner().invoke(app, [
        "interview", "--role", "hrbp", "--company", "合成企业", "--target-role", "前端开发",
        "--jd", "React 合成岗位", "--mode", "practice",
    ])
    assert result.exit_code == 0, result.output
    assert captured[1]["jd"] == "React 合成岗位"
    assert captured[1]["mode"] == "practice"


def test_invalid_mode_does_not_start_interactive_wizard(monkeypatch):
    import run_interview
    from main import app
    monkeypatch.setattr(run_interview, "main", lambda **kwargs: pytest.fail("must reject invalid mode"))
    result = CliRunner().invoke(app, ["interview", "--mode", "unknown"])
    assert result.exit_code == 2


def test_mcp_interview_old_and_optional_arguments(profile, llm_stub, monkeypatch):
    from adapters import mcp_server
    from skills.mock_interviewer import handler as interview
    monkeypatch.setattr(interview, "load_user_profile", lambda: profile)
    monkeypatch.setattr(interview, "LLMClient", llm_stub)
    first = json.loads(mcp_server.tool_interview_start())
    assert first["status"] == "success"
    second = json.loads(mcp_server.tool_interview_start(
        target_role="前端开发", jd_text="React 测试 JD", mode="practice",
    ))
    assert second["status"] == "success"
    prompt = llm_stub.calls[-1]["messages"][0]["content"]
    assert "React 测试 JD" in prompt and "训练模式" in prompt
    assert first["session_id"] != second["session_id"]
    mcp_server._interview_sessions.clear()

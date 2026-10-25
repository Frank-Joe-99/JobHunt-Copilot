"""所有测试使用合成材料；MCP 子进程使用隔离配置、数据库和输出目录。"""

import sys
from pathlib import Path

import httpx
import pytest
import yaml
from mcp import StdioServerParameters

from core import config
from core.state import Basics, Education, Objective, Project, Skills, UserProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def profile():
    return UserProfile(
        basics=Basics(
            name="Synthetic Candidate", birth_year=2002, phone="13800000000",
            email="synthetic@example.invalid", location="测试城市",
        ),
        objective=Objective(target_role="研发工程师"),
        education=[Education(
            school="合成测试大学", major="软件工程", degree="本科",
            start_date="2020", end_date="2024",
        )],
        skills=Skills(frameworks_and_tools=["React", "FastAPI"]),
        projects=[
            Project(
                name=f"合成项目{index}", start_date="2024", end_date="进行中",
                tech_stack=["React", "FastAPI"],
                highlights=["参与接口和页面开发，验证功能"],
            )
            for index in range(6)
        ],
    )


@pytest.fixture(autouse=True)
def protect_private_data_and_network(monkeypatch):
    read_yaml = config._read_yaml_file

    def guarded_read(path):
        resolved = Path(path).resolve()
        if resolved.parent == (PROJECT_ROOT / "config").resolve() and ".example." not in resolved.name:
            raise AssertionError("测试禁止读取真实个人配置；请注入合成配置。")
        return read_yaml(path)

    def no_network(*args, **kwargs):
        raise AssertionError("离线测试禁止真实 HTTP 请求；请使用 MockTransport。")

    monkeypatch.setattr(config, "_read_yaml_file", guarded_read)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)


@pytest.fixture
def mcp_server_params(tmp_path, profile):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "profile.yaml").write_text(
        yaml.safe_dump(profile.model_dump(mode="json"), allow_unicode=True), encoding="utf-8",
    )
    (config_dir / "settings.yaml").write_text(
        yaml.safe_dump({"llm": {"default_provider": "offline", "providers": {}}}),
        encoding="utf-8",
    )
    bootstrap = """
import sys
from pathlib import Path
import httpx
from core import config
config.PROJECT_ROOT = Path(sys.argv[1])
def no_network(*args, **kwargs):
    raise RuntimeError("MCP test subprocess is offline")
httpx.HTTPTransport.handle_request = no_network
from skills.resume_generator import handler as generator
generator.OUTPUT_DIR = config.PROJECT_ROOT / "storage" / "resumes"
from skills.application_tracker import database
database.DEFAULT_DB_PATH = config.PROJECT_ROOT / "storage" / "tracker.db"
from adapters.mcp_server import main
main()
"""
    return StdioServerParameters(
        command=sys.executable,
        args=["-X", "utf8", "-c", bootstrap, str(tmp_path)],
        cwd=str(PROJECT_ROOT),
    )


@pytest.fixture
def llm_stub():
    class Stub:
        calls = []
        responder = None
        chunks = ["请介绍与你应聘岗位相关的经历。"]
        stream_error = None
        closed = False

        def __init__(self, provider=None):
            self.provider = provider

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def close(self):
            type(self).closed = True

        def chat_pydantic(self, messages, model_class, **kwargs):
            type(self).calls.append({"messages": messages, "model_class": model_class})
            assert type(self).responder is not None
            return type(self).responder(messages, model_class)

        def chat_stream(self, messages, **kwargs):
            type(self).calls.append({"messages": messages})
            yield from type(self).chunks
            if type(self).stream_error:
                raise type(self).stream_error

    return Stub

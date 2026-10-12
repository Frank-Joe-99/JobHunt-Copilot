"""
宿主客户端配置生成与一键安装脚本 (Host Config Generator)
运行方式:
  uv run python adapters/generate_client_configs.py
  uv run python adapters/generate_client_configs.py --install-codex
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_codex_toml_snippet() -> str:
    escaped_path = str(PROJECT_ROOT).replace("\\", "/")
    return f"""
[mcp_servers.jobhunt-copilot]
command = "uv"
args = [
    "--directory",
    "{escaped_path}",
    "run",
    "python",
    "-X",
    "utf8",
    "-m",
    "adapters.mcp_server",
]
startup_timeout_sec = 60
tool_timeout_sec = 180
"""


def get_json_snippet() -> dict:
    escaped_path = str(PROJECT_ROOT).replace("\\", "\\\\")
    return {
        "mcpServers": {
            "jobhunt-copilot": {
                "command": "uv",
                "args": [
                    "--directory",
                    str(PROJECT_ROOT),
                    "run",
                    "python",
                    "-X",
                    "utf8",
                    "-m",
                    "adapters.mcp_server"
                ]
            }
        }
    }


def install_to_codex():
    codex_cfg = Path(os.environ.get("USERPROFILE", "")) / ".codex" / "config.toml"
    if not codex_cfg.parent.exists():
        print(f"[-] 未检测到 Codex 目录: {codex_cfg.parent}")
        return False

    snippet = get_codex_toml_snippet()
    existing_content = codex_cfg.read_text(encoding="utf-8") if codex_cfg.exists() else ""

    if "[mcp_servers.jobhunt-copilot]" in existing_content:
        print(f"[✓] ~/.codex/config.toml 中已存在 jobhunt-copilot 配置，无需重复写入。")
        return True

    # 安全备份
    if codex_cfg.exists():
        backup_file = codex_cfg.with_suffix(".toml.jobhunt_backup")
        shutil.copy2(codex_cfg, backup_file)
        print(f"[+] 已安全备份原有配置文件至: {backup_file}")

    with codex_cfg.open("a", encoding="utf-8") as f:
        f.write("\n# === JobHunt-Copilot MCP Server ===\n")
        f.write(snippet)

    print(f"[+] 成功将 jobhunt-copilot 写入 ~/.codex/config.toml！")
    print("    重启 Codex 后即可在会话中通过输入 /mcp 查看并直接使用 13 大求职工具。")
    return True


def main():
    parser = argparse.ArgumentParser(description="生成与安装 JobHunt-Copilot MCP 宿主客户端配置")
    parser.add_argument("--install-codex", action="store_true", help="一键写入 ~/.codex/config.toml")
    args = parser.parse_args()

    if args.install_codex:
        install_to_codex()
        return

    print("=" * 60)
    print("[*] JobHunt-Copilot MCP 宿主客户端即插即用配置")
    print("=" * 60)
    print(f"当前项目绝对路径: {PROJECT_ROOT}\n")

    print("【1. Codex 配置 (~/.codex/config.toml)】")
    print("可直接追加至 ~/.codex/config.toml（或运行 `uv run python adapters/generate_client_configs.py --install-codex` 自动写入）：")
    print(get_codex_toml_snippet().strip())
    print()

    print("【2. Claude Desktop 配置】")
    print("放置于 %APPDATA%\\Claude\\claude_desktop_config.json:")
    print(json.dumps(get_json_snippet(), ensure_ascii=False, indent=2))
    print()

    print("【3. Cursor IDE 配置】")
    print("打开 Cursor 设置 -> Features -> MCP -> Add new MCP server:")
    print(f"  Name: jobhunt-copilot")
    print(f"  Type: command")
    print(f"  Command: uv --directory \"{PROJECT_ROOT}\" run python -X utf8 -m adapters.mcp_server")
    print("=" * 60)


if __name__ == "__main__":
    main()

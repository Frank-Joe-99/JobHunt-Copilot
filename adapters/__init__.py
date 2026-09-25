"""
JobHunt-Copilot Adapters Package
外部生态协议适配层：包含 MCP (Model Context Protocol) 服务与标准 Function Calling 导出器
"""

from adapters.mcp_server import mcp_app

__all__ = ["mcp_app"]

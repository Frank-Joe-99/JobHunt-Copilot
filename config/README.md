# 配置

仅 example 模板受版本控制；实际配置、密钥及个人图片保留本地。

| 模板 | 本地工作文件 | 用途 |
| --- | --- | --- |
| [profile.example.yaml](profile.example.yaml) | `profile.yaml` | 真实个人档案与经历 |
| [preferences.example.yaml](preferences.example.yaml) | `preferences.yaml` | 岗位、城市等求职偏好 |
| [settings.example.yaml](settings.example.yaml) | `settings.yaml` | 模型、能力及 GitHub 预算 |

## 初始化

在项目根目录执行；已有配置不会覆盖：

```powershell
"profile", "preferences", "settings" | ForEach-Object {
    if (-not (Test-Path "config/$_.yaml")) {
        Copy-Item "config/$_.example.yaml" "config/$_.yaml"
    }
}
```

填写真实档案，选择供应商并设置可用的 `api_key`、`base_url` 和 `model`。YAML 支持 `${LLM_API_KEY}` 这类进程环境变量引用；未设置的变量不会自动获得可用凭证。

```powershell
uv run python -X utf8 check_config.py
```

该命令只校验本地结构，不验证远端连通性。加载有进程内缓存，改配置后重启相关进程；恢复面试继续使用原事实快照。

## 升级相关设置

- 模型参数按端点能力显式配置：`temperature`、`supports_temperature`、`token_limit_parameter`、输出和输入预算；不按模型名猜测。
- `structured_output: auto` 配合 JSON 能力选择格式。严格 schema 仅在验证支持后开启；错误分类、降级与共享预算见 [M08](../future-upgrade/M08-STRUCTURED-OUTPUT.md)。
- `github` 配置搜索、README、请求体积、耗时与缓存期限；Token 可选。`offline: true` 只关闭 GitHub，不关闭模型调用。
- 面试预算通过新建会话的 CLI / MCP 参数设置，见[面试说明](../skills/mock_interviewer/README.md)。

字段以[数据契约](../core/state.py)和示例模板为准。图片路径见 [assets](assets/README.md)；缺失事实不要用虚构指标补齐。

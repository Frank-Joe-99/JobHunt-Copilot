# JobHunt-Copilot

面向应届生的求职辅助工具。维护一份 YAML 个人档案，用于生成简历、润色经历和分析岗位要求。

## 当前功能

- **简历生成**：从个人档案生成 Word 和 PDF，支持本地运行，无需模型 API。
- **经历润色**：按 STAR 方法整理经历，检查简历与岗位关键词的匹配情况。
- **岗位分析**：解析岗位描述（JD），比较已有技能与岗位要求，生成修改建议和自荐信草稿。

经历润色和岗位分析需要配置模型 API。个人档案保存在本地，调用云端模型时，相关内容会发送到所配置的服务。

项目仍在开发中。模拟面试、投递管理、岗位雷达和 MCP 接入尚未实现。

## 快速开始

### 1. 安装依赖

需要 Python 3.12+ 和 [uv](https://github.com/astral-sh/uv)。以下命令均在项目根目录运行。

```bash
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot
uv sync
```

### 2. 准备配置

首次使用时复制示例文件；已有配置时跳过对应文件，避免覆盖。

```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```

以上复制命令适用于 PowerShell 和 Linux/macOS 终端。

| 文件 | 用途 |
| --- | --- |
| `config/profile.yaml` | 教育背景、技能、项目、实习等个人经历；生成简历必需 |
| `config/preferences.yaml` | 目标岗位、城市、薪资等求职偏好 |
| `config/settings.yaml` | 模型供应商、API Key 和运行参数；调用模型前填写 |

可选照片和校徽放在 `config/assets/`，在档案中填写相应路径。字段说明见 [配置文档](config/README.md)。

### 3. 生成简历

填写个人档案后运行：

```bash
uv run generate_resume.py
```

输出文件：

- `storage/resumes/resume_default.docx`
- `storage/resumes/resume_default.pdf`

重复运行会覆盖这两个文件。模板和自定义调用方式见 [简历生成模块](skills/resume_generator/README.md)。

## 检查与验证

### 检查配置

```bash
uv run check_config.py
```

检查三份配置能否加载、字段是否符合数据模型，不调用模型 API，也不验证密钥是否有效。

### 验证模型与业务模块

配置有效的 API Key 和个人档案后运行：

```bash
uv run test_phase2.py
```

依次调用模型客户端、经历润色、关键词诊断和岗位分析。该脚本会发送真实 API 请求，使用个人档案中的相关内容，并产生 API 用量；它用于联调，不是离线单元测试。

单独调用各模块的方法见 [经历润色](skills/resume_polisher/README.md) 和 [岗位匹配](skills/jd_matcher/README.md)。目前尚无统一的 `main.py` 命令行入口。

## 后续计划

- 项目推荐：根据技能差距查找可参考的开源项目。
- 模拟面试与投递记录。
- MCP 接入：先封装简历生成，再接入润色和岗位分析，供桌面客户端调用。
- ChatGPT Work 插件与文件交付：在 MCP 接入完成后实现。
- 岗位雷达：暂缓开发。

## 开发文档

各目录的职责和实现细节放在对应 README 中，主文档只保留使用入口。

- [配置与字段](config/README.md)
- [数据模型与配置加载](core/README.md)
- [业务模块](skills/README.md)
- [模型客户端与基础工具](tools/README.md)
- [外部接入规划](adapters/README.md)（待实现）
- [产物存储](storage/README.md)

## 许可证

[MIT](LICENSE)

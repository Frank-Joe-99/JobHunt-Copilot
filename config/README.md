# 📁 config/ 目录：用户资产与配置中心

> 本模块为 JobHunt-Copilot 的**用户数据与系统配置中心**。遵循本地优先（Local-First）原则，用户档案、隐私偏好与模型密钥均存储在本地，通过 `.gitignore` 隔离，不随 Git 提交到公共代码仓库。

---

## 📄 配置文件结构

| 模板文件 (已版本控制) | 实际工作文件 (本地私密) | 对应数据模型 | 核心用途说明 |
| :--- | :--- | :--- | :--- |
| `profile.example.yaml` | `profile.yaml` | `UserProfile` | 个人主档案：基础信息、教育背景、技能清单、实习与项目经历 |
| `preferences.example.yaml` | `preferences.yaml` | `JobPreferences` | 求职意向：目标岗位、意向城市、期望薪资及雷达扫描过滤阈值 |
| `settings.example.yaml` | `settings.yaml` | `AppSettings` | 运行设置：大模型厂商（DeepSeek/OpenAI等）、API 密钥与超时参数 |
| `assets/` | `assets/*` | 静态文件 | 个人多媒体资源：证件照 (`avatar.png`)、学校校徽 (`school_logo.png`) |

---

## 🛠️ 配置初始化与编辑操作 (Procedures)

### 1. 前置条件 (Prerequisites)
- 项目依赖已安装（已执行 `uv sync`）。
- 位于项目根目录下。

---

### 2. 初始化工作配置文件步骤

#### 步骤 1：从模板复制生成配置文件
在终端中执行下列复制命令：
```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```
*预期结果*：在 `config/` 目录下生成三个非 `example` 的本地工作文件。

#### 步骤 2：编辑个人档案 (`config/profile.yaml`)
使用文本编辑器打开 `config/profile.yaml` 并填写以下核心板块：
- `basics`（必填）：填写真实姓名、出生年份、电话、邮箱与现居城市。
- `education`（必填）：按时间倒序排列填写（最新学历在前），注明学校、专业、学历。
- `skills`（必填）：分项列出编程语言（含熟练度）、框架工具与数据库技能。
- `internships` / `projects`：经历亮点描述建议遵循 STAR 结构（背景、任务、行动与量化产出）。

#### 步骤 3：配置大模型与外部凭证 (`config/settings.yaml`)
编辑 `config/settings.yaml` 配置大模型连接信息：
```yaml
llm:
  default_provider: "deepseek"   # 默认供应商名称
  providers:
    deepseek:
      base_url: "https://api.deepseek.com/v1"
      api_key: "sk-your-deepseek-api-key"
      model: "deepseek-chat"
      timeout_seconds: 60.0
```
> [!TIP]
> 如需提升 GitHub 仓库检索速率限制，可在本文件中填入 `github.token`。

---

### 3. 配置正确性校验操作

#### 步骤 1：运行校验命令
在终端执行统一配置校验脚本：
```bash
uv run python -X utf8 check_config.py
```

#### 步骤 2：检查校验结果
- **校验成功**：终端输出 `[✓] All configurations validated successfully!`。
- **校验失败**：终端输出指出具体的 YAML 文件名、出错行号与缺失的必填字段名称。根据提示修正对应的 YAML 缩进或字段格式。

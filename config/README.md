# 📁 config/ 目录：用户资产与配置中心

`config/` 是用户的**私人数据中心**。本项目严格遵守 **“数据与逻辑解耦”** 和 **“本地隐私优先 (Local-First)”** 原则。用户的敏感求职信息只保存在本地，绝不会随 Git 提交到公共代码仓库。

---

## 📄 核心文件说明

| 文件名 | 职责与内容 | 状态说明 |
| :--- | :--- | :--- |
| `profile.example.yaml` | **个人主档案示例模板**：涵盖基本联系方式、教育经历、技能树、项目经历、校内荣誉、资格证书等标准字段。 | 模板文件（纳入版本控制） |
| `profile.yaml` | **用户的真实主档案**：用户基于示例复制并填写的真实数据，所有简历生成与分析的底层输入源。 | 隐私敏感（已在 `.gitignore` 忽略） |
| `preferences.example.yaml` | **求职意向示例**：目标岗位类别、意向城市、期望薪资下限、校招岗位雷达抓取频率等配置。 | 模板文件（纳入版本控制） |
| `preferences.yaml` | **用户的真实求职偏好**。 | 隐私敏感（已在 `.gitignore` 忽略） |
| `settings.example.yaml` | **系统级配置示例**：大模型厂商（DeepSeek / OpenAI / Claude 等）、API Key、代理、排版模板选择。 | 模板文件（纳入版本控制） |
| `settings.yaml` | **用户的系统级配置与私有密钥**。 | 隐私敏感（已在 `.gitignore` 忽略） |
| `assets/` | **多媒体静态资源文件夹**：存放用户个人证件照（`avatar.png`）、学校校徽矢量图（`school_logo.png`）等。 | 私人文件（已在 `.gitignore` 忽略，仅保留占位符） |

---

## 🚀 YAML 配置文件使用指南

### 1. 快速初始化（首次使用）
在首次拉取项目或开始使用前，执行以下命令从示例模板创建你的本地私有配置：

```bash
# Windows PowerShell 或 Linux/macOS Bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```

> 🔒 **隐私安全保障**：所有真实 `.yaml` 配置文件和 `assets/` 下的私人照片均已被 `.gitignore` 严格忽略，绝不会被意外推送到 GitHub 等公共代码仓库。

---

### 2. 核心 YAML 文件配置与填写指引

#### ① `config/profile.yaml`（个人主档案）
* **定位**：求职者的核心“个人资产库”。系统内所有简历排版、经历润色、模拟面试的原始输入源。
* **填写要点**：
  * `basics`：姓名、出生年份、电话、邮箱、现居城市为必填；头像照片推荐存入 `config/assets/avatar.png`；
  * `education`：按时间倒序填写（最高学历在前），支持本科、硕士、博士、直博；
  * `skills`：掌握的编程语言及熟练度、常用框架与数据库；
  * `internships` / `projects`：实习与项目经历，建议每条亮点遵循 **STAR 法则**（情境、任务、行动、量化成果）；
  * `research` / `articles`：硕博或学术方向可填写科研课题与论文发表（本科生可留空或直接删除对应项）。

#### ② `config/preferences.yaml`（求职偏好与雷达规则）
* **定位**：机会雷达扫描与匹配过滤规则。
* **填写要点**：
  * `search_criteria`：目标岗位列表（`target_roles`）、意向城市（`target_locations`）、月薪范围（`expected_salary_monthly_k`）；
  * `job_radar`：抓取间隔小时数（`fetch_interval_hours`）、最低匹配度打分阈值（`min_match_score`，低于此分数的岗位不提示）；
  * `channels`：启用或关闭特定的招聘抓取渠道（牛客、V2EX、RSS 源）。

#### ③ `config/settings.yaml`（系统与模型运行参数）
* **定位**：驱动底层工具运转的基础设施配置与 API 密钥。
* **填写要点**：
  * `llm.default_provider`：指定默认大模型厂商（如 `deepseek`、`openai` 或 `claude`）；
  * `llm.providers`：填入对应厂商的 `api_key`、`model`、`base_url`；
  * `resume_generation`：排版引擎选择（推荐 `engine: "typst"`，毫秒级排版且无复杂环境依赖）；
  * `github.token`：可选填 GitHub Personal Access Token（用于提高开源项目推荐时的 API 速率限制）。

---

### 3. 如何在 Python 中加载与校验 YAML 文件？

在项目代码中，推荐使用 `core/state.py` 提供的强类型模型反序列化加载。也可以在终端执行单行命令快速校验自己的配置文件是否有格式错误：

```powershell
uv run python -c "
import yaml
from core.state import UserProfile, JobPreferences, AppSettings

# 校验个人主档案
profile = UserProfile.model_validate(yaml.safe_load(open('config/profile.yaml', encoding='utf-8')))
print('✅ profile.yaml 校验通过！姓名:', profile.basics.name)

# 校验求职偏好
prefs = JobPreferences.model_validate(yaml.safe_load(open('config/preferences.yaml', encoding='utf-8')))
print('✅ preferences.yaml 校验通过！目标岗位数:', len(prefs.search_criteria.target_roles))

# 校验系统设置
settings = AppSettings.model_validate(yaml.safe_load(open('config/settings.yaml', encoding='utf-8')))
print('✅ settings.yaml 校验通过！默认大模型:', settings.llm.default_provider)
"
```

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

## 🔒 隐私保护最佳实践

1. **首次使用**：
   ```bash
   cp config/profile.example.yaml config/profile.yaml
   cp config/preferences.example.yaml config/preferences.yaml
   cp config/settings.example.yaml config/settings.yaml
   ```
2. **切勿更改文件名后缀**：系统默认读取 `config/profile.yaml`（未来也可支持 `config/profile.md` 解析）。
3. **敏感信息保障**：`.gitignore` 已预设过滤所有 `.yaml` 真实配置文件及 `assets/` 下的私人照片，确保即便将项目开源或备份，也不会发生个人隐私泄露。

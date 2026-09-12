# 📦 storage/ 目录：产物持久化仓库

`storage/` 目录专门用于存放 JobHunt-Copilot 系统运行过程中生成的各种文件、数据库和运行记录。

---

## 🔒 隐私与版本控制规则

> **重要提示**：本目录下除各子目录的 `.gitkeep` 占位文件外，**所有生成的最终文件均已被 `.gitignore` 排除在版本库之外**。
> 
> 导出的 PDF 简历含有个人私密信息，生成的面试录音或打分记录亦属于个人隐私，绝不会被意外推送到 GitHub 等公共代码仓库。

---

## 📂 存储子目录划分

| 目录/文件 | 用途与生成物 |
| :--- | :--- |
| `resumes/` | 模块 0 生成的各版本 PDF 简历成品（如 `resume_default.pdf`、`resume_bytedance_backend.pdf`）。 |
| `radar_reports/` | 模块 1.5 定期扫描后生成的校招新发岗位推荐简报（Markdown 格式）。 |
| `interview_logs/` | 模块 3 AI 模拟面试问答的对话全景录音/文本，以及最终输出的《复盘体检报告》。 |
| `tracker.db` | 模块 4 求职投递看板的本地轻量 SQLite 数据库文件。 |

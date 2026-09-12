# 📄 skills/resume_generator/：模块 0 本地简历排版引擎

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生使用 Word 排版容易产生对齐错乱、换电脑变形、跨行跨页问题；
  - 传统 LaTeX 配置繁琐、编译慢、环境安装动辄几 GB；
  - 在线平台制作简历存在付费墙和严重的隐私数据泄露隐患。
- **本模块职责**：
  - 读取 `config/profile.yaml` 中的结构化数据。
  - 自动渲染并编译生成学术级/工业级美观、边距严谨、严格限制在 **A4 一页纸** 内的高清 PDF。

---

## ⚙️ 关键技术方案
1. **优先推荐：Typst 现代化排版引擎**
   - 语法极度清爽现代，编译速度毫秒级（远胜传统 LaTeX）。
   - 官方 Python 绑定或 CLI 支持，轻松控制单页布局与字体间距。
2. **备选方案：Jinja2 (HTML+CSS) + WeasyPrint / Playwright**
   - 适合前端开发者极度自由地定制现代化 Web 扁平风格简历。

---

## 📂 预期内部结构
```text
skills/resume_generator/
├── __init__.py
├── handler.py             # 核心逻辑：读取 UserProfile -> 填充模板 -> 调用编译
├── templates/             # 预设主题模板库
│   ├── modern_geek.typ    # 现代极客风 (技术/计算机方向)
│   ├── business_clean.typ # 商务简约风 (商科/金融/运营方向)
│   └── academic.typ       # 学术规范风 (科研院所/国企体制内方向)
└── README.md
```

## 📥 输入与输出契约
- **输入**：`UserProfile` 对象（来自 `core.state`） + 模板名称 `template_name`。
- **输出**：生成的目标 PDF 绝对路径（存储于 `storage/resumes/`）。

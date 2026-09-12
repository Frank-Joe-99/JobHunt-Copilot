# 🔧 tools/ 目录：底层基础设施与外设驱动层

`tools/` 负责充当系统的**“手和脚”**。它专门处理与现实外部世界的具体协议对接（HTTP 请求、外部命令行、文件解析、大模型厂商 API 等）。

---

## 🛑 纯粹性铁律（重要架构准则）

> **`tools/` 里的代码只管“怎么发请求、怎么编译渲染”，绝不包含任何“应届生怎么写简历”这类业务逻辑或大模型提示词（Prompt）。**
> 
> 业务策略属于 `skills/`，底层工具属于 `tools/`。这种设计保证了底层技术更换（例如更换大模型 SDK 或更换 PDF 编译器）时，业务层代码完全不受影响。

---

## 🗂️ 核心工具文件规划

```text
tools/
├── __init__.py
├── llm_client.py       # 统一大模型请求客户端封装
├── pdf_engine.py       # PDF 编译、渲染与解析引擎
├── github_client.py    # GitHub API 交互封装
├── crawler.py          # 网络页面抓取与 HTML 文本清洗器
└── README.md
```

### 1. `llm_client.py`（统一大模型客户端）
- 抽象统一的 LLM 访问接口，支持一键切换厂商：**DeepSeek**、**OpenAI**、**Claude**、**Gemini**、**本地 Ollama**。
- 提供标准能力：
  - `generate_text(prompt, system_prompt, **kwargs) -> str`
  - `generate_json(prompt, response_model: Type[BaseModel]) -> BaseModel`（基于结构化 JSON 输出）
  - `stream_chat(messages) -> Generator`（流式输出，供模拟面试使用）

### 2. `pdf_engine.py`（PDF 编译与解析引擎）
- **PDF 编译**：调用 Typst 编译器或 WeasyPrint，将结构化模板与数据渲染为矢量 PDF 简历。
- **PDF 逆向解析**：基于 `pdfplumber` 或 `pypdf`，用于提取用户上传的旧简历中的纯文本和章节信息。

### 3. `github_client.py`（GitHub 接口封装）
- 负责与 GitHub REST API 交互。
- 提供项目检索函数：按编程语言（`language:python`）、star 数范围（`stars:500..5000`）、活跃度、关键词（`rag`, `mini-redis`, `web-server`）进行查询并返回结构化仓库信息。

### 4. `crawler.py`（网络抓取与清洗工具）
- 轻量级页面抓取与正文提取工具（基于 `httpx` + `BeautifulSoup4`）。
- 负责爬取公开校招资讯、V2EX 酷工作板块或企业招聘网页，自动剔除导航栏和无用广告，抽取出核心职位文本。

# 📄 skills/resume_generator/：模块 0 本地简历排版引擎

## 🎯 业务定位与核心价值
- **双格式输出（Word + PDF 镜像对齐）**：
  - **Word (.docx)**：基于 `python-docx` 纯代码构建，方便用户在生成后针对具体岗位进行微调、手动增删细节。
  - **PDF (.pdf)**：基于现代排版新星 **Typst** 引擎编译，毫秒级编译，排版严密对齐、绝对不会跨平台错位。
  - 两者视觉规格（1cm 边距、1.1 倍行距、三列紧凑头部、论文悬挂缩进）保持 **1:1 绝对一致**。
- **本地隐私安全 (Local-First)**：
  - 零云端依赖，无需上传个人信息到第三方网站，彻底杜绝个人隐私泄露。
  - 结构化输入：严格读取 `core.state.UserProfile` 强类型数据，按需自动隐藏空字段板块。

---

## 🏗️ 模块内部架构与文件职责

```text
skills/resume_generator/
├── __init__.py
├── handler.py              # 统一门面入口：协调 Word + PDF 双引擎，一键双出
├── docx_builder.py         # Word 构建器：基于 python-docx 渲染 .docx 简历
├── typst_builder.py        # PDF 构建器：调用 typst Python 绑定编译 .pdf 简历
├── templates/
│   └── modern.typ          # 现代精致风 Typst 简历模板（数据驱动排版）
└── README.md               # 本说明文档
```

### 文件职责说明
1. **`handler.py` (统一门面)**：
   - 对外暴露主函数 `generate_resume(profile=None, output_name="resume_default", template="modern")`。
   - 协调调度 Word 与 PDF 两个构建器，将生成产物统一保存至 `storage/resumes/`。
2. **`docx_builder.py` (Word 构建引擎)**：
   - 页面规范：A4 纸张、1.0cm 紧凑边距、全局 1.1 倍行间距。
   - 头部设计：三列无边框表格（左侧姓名与联系方式、中间学校校徽 Logo、右侧个人照片证件照）。
   - 布局技巧：利用右对齐制表位（Tab Stop）实现“左侧经历名称 + 右侧起止时间”经典简历排版；底边框直接挂载于标题段落消除多余空行；论文发表支持悬挂缩进编号。
3. **`typst_builder.py` (Typst PDF 编译引擎)**：
   - 无需本地预装 Typst CLI，直接调用官方 `typst` Python 绑定接口进行内存编译。
   - 通过 `sys.inputs` / 临时数据桥接机制安全传递数据，支持以项目根目录作为静态资源根路径读取图片。
4. **`templates/modern.typ` (Typst 模板)**：
   - 声明式数据驱动排版，完美复刻 Word 的 1cm 边距与三列头部排版。
   - 具有优雅的间距控制与中文字体适配（Arial + 微软雅黑 + 黑体回退链）。

---

## 📥 输入与输出契约

- **输入**：`UserProfile` 对象（来自 `core.state`，若不传则通过 `core.config.load_user_profile()` 自动从 `config/profile.yaml` 读取）。
- **输出**：包含生成产物路径的字典：
  ```python
  {
      "docx": Path("storage/resumes/resume_default.docx"),
      "pdf": Path("storage/resumes/resume_default.pdf")
  }
  ```

---

## 🚀 独立调用与验证命令

在项目根目录下通过终端一键生成简历：

```powershell
# 一键同时生成 Word (.docx) 和 PDF (.pdf) 简历
uv run python -c "from skills.resume_generator.handler import generate_resume; res = generate_resume(); print('[OK] 生成成功！\nWord:', res['docx'], '\nPDF:', res['pdf'])"
```

生成结果将存放在：
- `storage/resumes/resume_default.docx`
- `storage/resumes/resume_default.pdf`

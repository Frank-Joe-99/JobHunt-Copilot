# 简历生成

从真实档案本地生成 PDF 和 Word，不调用模型，也不改写经历。

## 使用

```powershell
uv run jobhunt resume --template modern -o my_resume
```

产物为 `storage/resumes/my_resume.pdf` 和 `my_resume.docx`。输出名只填文件名，不含目录和扩展名。

```python
from skills.resume_generator import generate_resume

paths = generate_resume(output_name="my_resume", template="modern")
# paths["pdf"] / paths["docx"] 为 Path；也可显式传入 profile。
```

## 实现与边界

- `handler.py` 在临时目录完成两种格式构建后，再替换正式文件。
- `typst_builder.py` 使用本地 Typst；当前仅附带 [modern.typ](templates/modern.typ)。新增 PDF 模板须提供对应 .typ 文件。
- `docx_builder.py` 使用 python-docx，独立构建 Word 布局。
- 照片和校徽可选，路径见[图片说明](../../config/assets/README.md)。生成后分别检查分页、字体和图片。
- 岗位定制使用 `uv run jobhunt tailor "JD文本"`，相关改写由[核心工作流](../../core/README.md)处理。

[配置指南](../../config/README.md) · [存储说明](../../storage/README.md)

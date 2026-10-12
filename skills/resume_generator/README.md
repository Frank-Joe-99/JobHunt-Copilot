# 📄 skills/resume_generator/：模块 0 本地双格式简历排版引擎

> 本模块为 JobHunt-Copilot 的**核心排版编译组件**。基于 Typst 与 python-docx 引擎，以声明式与数据驱动方式一键输出视觉镜像对齐的 Word (.docx) 与 PDF (.pdf) 双格式简历。

---

## 🎯 业务定位与排版规格

| 格式 | 构建技术底座 | 适用求职场景 | 视觉设计标准 |
| :--- | :--- | :--- | :--- |
| **Word (.docx)** | `python-docx` 纯代码构建 | 需二次个性化微调细节的场景 | 1.0cm 紧凑边距、全局 1.1 倍行间距、三列紧凑标题栏、右对齐制表位时间轴、论文悬挂缩进 |
| **PDF (.pdf)** | `typst` 官方 Python 绑定接口 | 邮件直投、官网网申、打印现场面试 | 与 Word 版保持 1:1 绝对镜像一致排版，中文无缝适配回退链 |

> [!NOTE]
> **本地编译与隐私安全**：无需云端渲染服务，零外部依赖，毫秒级本地编译，彻底规避简历数据泄漏风险。

---

## 🏗️ 内部组件与文件分工

```text
skills/resume_generator/
├── __init__.py          # 导出 generate_resume 入口
├── handler.py           # 协调门面：控制临时目录防冲突，并发/原子化生成双格式
├── docx_builder.py      # Word 渲染器：基于 python-docx 构建 .docx 文件
├── typst_builder.py     # PDF 渲染器：调用 typst 库执行内存编译
├── templates/
│   └── modern.typ       # 现代科技风 Typst 简历模板文件
└── README.md            # 本使用说明
```

---

## 🛠️ 操作与生成指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/profile.yaml` 存在且格式合法（如未传入内存 Profile，将自动读取该文件）。
- 输出目录 `storage/resumes/` 将自动创建。

---

### 2. 通过 CLI 命令行生成简历

#### 步骤 1：执行编译命令
在项目根目录运行下列命令编译基础简历：
```bash
# 生成默认 modern 模板简历
uv run jobhunt resume --template modern -o my_resume_2026
```

#### 步骤 2：参数说明表
| 参数名 | 简写 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `--template` | `-t` | 否 | `modern` | 模板风格，支持 `modern`（现代风）或 `minimal`（极简风） |
| `--output-name` | `-o` | 否 | `resume_default` | 产物文件名称（无需输入 `.pdf` 或 `.docx` 扩展名） |

#### 步骤 3：验证生成产物
检查输出路径中是否存在双格式文件：
- PDF 文件：`storage/resumes/my_resume_2026.pdf`
- Word 文件：`storage/resumes/my_resume_2026.docx`

---

### 3. 通过 Python API 调用生成

#### 步骤 1：导入接口并调用
```python
from core.config import load_user_profile
from skills.resume_generator import generate_resume

# 可选：载入并修改内存中的 Profile 实体
profile = load_user_profile()

# 执行生成
result_paths = generate_resume(
    profile=profile,
    output_name="custom_resume",
    template="modern"
)

print(f"PDF 绝对路径: {result_paths['pdf']}")
print(f"Word 绝对路径: {result_paths['docx']}")
```
*预期结果*：函数返回包含 `"pdf"` 与 `"docx"` 两个 `Path` 对象的字典。

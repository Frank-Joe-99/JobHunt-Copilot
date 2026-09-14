"""PDF 简历构建器；在项目根目录运行 python -m skills.resume_generator.typst_builder。"""

import json
import warnings
from pathlib import Path

import typst

from core.state import UserProfile

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def build_pdf(
    profile: UserProfile, output_path: str | Path, template: str = "modern"
) -> Path:
    """将 UserProfile 编译为 PDF，返回产物的绝对路径。"""
    if not template or any(char in template for char in ("/", "\\", ":")):
        raise ValueError("template 必须是模板名称（不含路径和 .typ 扩展名）")
    template_path = TEMPLATE_DIR / f"{template}.typ"
    if not template_path.is_file():
        raise FileNotFoundError(f"找不到 Typst 模板：{template_path}")

    output_path = Path(output_path).resolve()

    data = profile.model_dump(mode="json", exclude_none=True)
    for field in ("school_logo", "avatar"):
        image_name = data["basics"].get(field)
        if not image_name:
            continue
        image_path = (PROJECT_ROOT / image_name.replace("\\", "/")).resolve()
        if not image_path.is_relative_to(PROJECT_ROOT):
            raise ValueError(f"{field} 图片必须位于项目目录内：{image_path}")
        if not image_path.is_file():
            # 与 Word 构建器一致：未准备好的可选图片不阻断简历生成。
            warnings.warn(f"{field} 图片不存在，已跳过：{image_path}", stacklevel=2)
            data["basics"].pop(field)
        else:
            data["basics"][field] = image_path.relative_to(PROJECT_ROOT).as_posix()

    # 每次编译独立传入数据；root 仍用于解析 /config/assets/... 图片路径。
    try:
        pdf_bytes = typst.compile(
            str(template_path),
            root=str(PROJECT_ROOT),
            format="pdf",
            sys_inputs={"profile": json.dumps(data, ensure_ascii=False)},
        )
    except typst.TypstError as exc:
        # 默认异常文本只有简短原因；补充模板行列号和编译器提示。
        exc.add_note(f"Typst 模板：{template_path}\n{exc.diagnostic}")
        raise

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    return output_path


if __name__ == "__main__":
    from core.config import load_user_profile

    result = build_pdf(
        load_user_profile(), PROJECT_ROOT / "storage" / "resumes" / "resume_default.pdf"
    )
    print(f"[+] PDF resume saved to: {result}")

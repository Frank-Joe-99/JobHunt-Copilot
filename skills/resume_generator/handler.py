"""双格式简历生成入口；在项目根目录运行 python -m skills.resume_generator.handler。"""

from pathlib import Path
from tempfile import TemporaryDirectory

from core.config import load_user_profile
from core.state import UserProfile
from skills.resume_generator.docx_builder import build_docx
from skills.resume_generator.typst_builder import build_pdf

# 默认产物输出目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "storage" / "resumes"


def generate_resume(
    profile: UserProfile | None = None,
    output_name: str = "resume_default",
    template: str = "modern",
) -> dict[str, Path]:
    """
    一键生成 Word + PDF 双格式简历
    
    Args:
        profile: 用户档案对象（若不传则自动从 config/profile.yaml 加载）
        output_name: 输出文件名（不含扩展名）
        template: PDF 模板风格名称
    
    Returns:
        包含 "docx" 和 "pdf" 产物绝对路径的字典
    """
    if (
        not output_name.strip()
        or output_name in (".", "..")
        or Path(output_name).name != output_name
    ):
        raise ValueError("output_name 必须是非空文件名，不能包含目录")

    if profile is None:
        profile = load_user_profile()

    docx_path = OUTPUT_DIR / f"{output_name}.docx"
    pdf_path = OUTPUT_DIR / f"{output_name}.pdf"

    # 两种格式都生成成功后才替换正式文件，避免 PDF 编译失败时只更新 Word。
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".resume-", dir=OUTPUT_DIR) as temp_dir:
        staging_dir = Path(temp_dir)
        print("[+] generating PDF resume...")
        staged_pdf = build_pdf(profile, staging_dir / pdf_path.name, template=template)

        print("[+] generating Word resume...")
        staged_docx = build_docx(profile, staging_dir / docx_path.name)

        staged_pdf.replace(pdf_path)
        staged_docx.replace(docx_path)

    return {"docx": docx_path, "pdf": pdf_path}


if __name__ == "__main__":
    for file_format, path in generate_resume().items():
        print(f"[+] {file_format.upper()} resume saved to: {path}")

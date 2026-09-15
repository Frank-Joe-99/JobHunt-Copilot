"""生成 Word 和 PDF 简历：uv run generate_resume.py。"""

from skills.resume_generator.handler import generate_resume


def main() -> None:
    for file_format, path in generate_resume().items():
        print(f"{file_format.upper()}: {path}")


if __name__ == "__main__":
    main()

"""
Word (.docx) 简历构建器
接收 UserProfile 对象，输出一份排版整洁紧凑的 .docx 简历文件。
"""

from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from core.state import UserProfile

# 项目根目录，用于解析图片相对路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# 通用排版辅助函数
# ---------------------------------------------------------------------------

# A4 页面宽 21cm，左右边距各 1.0cm，可用宽度 = 19.0cm
_USABLE_WIDTH_CM = 19.0

# 全局紧凑字号设定
_FONT_NAME = "微软雅黑"
_FONT_NAME_EN = "Arial"
_FONT_SIZE_BODY = Pt(9.5)
_FONT_SIZE_SECTION_TITLE = Pt(11)
_FONT_SIZE_NAME = Pt(15)


def _set_font(run, font_size=_FONT_SIZE_BODY, bold=False, color=None):
    """统一设置 run 的中英文字体、字号、加粗、颜色"""
    run.font.size = font_size
    run.font.bold = bold
    run.font.name = _FONT_NAME_EN
    run.element.rPr.rFonts.set(qn("w:eastAsia"), _FONT_NAME)
    if color:
        run.font.color.rgb = color


def _setup_page(doc: Document):
    """设置 A4 页面边距（上下左右各 1.0cm）与全局行距"""
    for section in doc.sections:
        section.top_margin = Cm(1.0)
        section.bottom_margin = Cm(1.0)
        section.left_margin = Cm(1.0)
        section.right_margin = Cm(1.0)
        
    # 设置全局默认段落样式：1.1 倍行距
    doc.styles['Normal'].paragraph_format.line_spacing = 0.9


def _add_section_title(doc: Document, title: str):
    """添加板块标题，底边框直接附加在标题段落上，完全消除多余空行"""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(6)  # 标题上方稍微留一点呼吸感
    para.paragraph_format.space_after = Pt(2)   # 标题文字距离横线的极小间距
    
    run = para.add_run(title)
    _set_font(run, font_size=_FONT_SIZE_SECTION_TITLE, bold=True)
    
    # 获取段落属性对象，直接给当前段落加上底边框
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")       # 4 个 1/8 磅 = 0.5 磅厚度
    bottom.set(qn("w:space"), "1")    # 边框与文字的垂直间距
    bottom.set(qn("w:color"), "888888")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_line_with_right_date(
    doc: Document,
    left_text: str,
    right_text: str,
    bold: bool = False,
    font_size=_FONT_SIZE_BODY,
):
    """带制表位的左右布局"""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(1.5)
    para.paragraph_format.space_after = Pt(1.5)

    tab_stops = para.paragraph_format.tab_stops
    tab_stops.add_tab_stop(Cm(_USABLE_WIDTH_CM), alignment=WD_ALIGN_PARAGRAPH.RIGHT)

    run_left = para.add_run(left_text)
    _set_font(run_left, font_size=font_size, bold=bold)

    para.add_run("\t")

    run_right = para.add_run(right_text)
    _set_font(run_right, font_size=font_size)


def _add_bullet_point(doc: Document, text: str):
    """添加无序列表项"""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(1)
    para.paragraph_format.space_after = Pt(1)
    # 悬挂缩进以实现更紧凑的换行对齐
    para.paragraph_format.left_indent = Cm(0.5)
    para.paragraph_format.first_line_indent = Cm(-0.5)
    run = para.add_run(f"• {text}")
    _set_font(run)


def _add_plain_line(doc: Document, text: str, font_size=_FONT_SIZE_BODY, bold=False):
    """添加普通行"""
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(1)
    para.paragraph_format.space_after = Pt(1)
    run = para.add_run(text)
    _set_font(run, font_size=font_size, bold=bold)


# ---------------------------------------------------------------------------
# 各板块渲染函数
# ---------------------------------------------------------------------------

def _add_header(doc: Document, profile: UserProfile):
    """渲染简历头部：左侧姓名与联系方式，中间学校Logo，右侧个人照片"""
    basics = profile.basics

    # 使用无边框表格 1行3列
    table = doc.add_table(rows=1, cols=3)
    table.autofit = False
    
    # 严格控制列宽（总宽 19.0cm = 13.0 + 3.0 + 3.0）
    for cell in table.columns[0].cells: cell.width = Cm(13.0)
    for cell in table.columns[1].cells: cell.width = Cm(3.0)
    for cell in table.columns[2].cells: cell.width = Cm(3.0)

    c_left, c_mid, c_right = table.rows[0].cells

    # --- 左列：姓名与联系方式 ---
    p_name = c_left.add_paragraph()
    p_name.paragraph_format.space_after = Pt(2)
    run = p_name.add_run(basics.name)
    _set_font(run, font_size=_FONT_SIZE_NAME, bold=True)

    # 联系方式
    contact_parts = [basics.phone, basics.email, basics.location]
    if basics.github:
        github_id = basics.github.rstrip("/").split("/")[-1]
        contact_parts.append(f"GitHub: {github_id}")
    if basics.blog:
        contact_parts.append("Blog")

    p_contact = c_left.add_paragraph()
    p_contact.paragraph_format.space_before = Pt(0)
    p_contact.paragraph_format.space_after = Pt(2)
    run = p_contact.add_run(" | ".join(contact_parts))
    _set_font(run, font_size=Pt(8.5), color=RGBColor(0x55, 0x55, 0x55))

    # 求职意向
    if profile.objective:
        obj = profile.objective
        parts = [f"求职意向：{obj.target_role}"]
        if obj.target_industry:
            parts.append(f"行业：{obj.target_industry}")
        if obj.expected_locations:
            parts.append(f"城市：{'、'.join(obj.expected_locations)}")

        p_obj = c_left.add_paragraph()
        p_obj.paragraph_format.space_before = Pt(0)
        p_obj.paragraph_format.space_after = Pt(0)
        run_obj = p_obj.add_run(" | ".join(parts))
        _set_font(run_obj, font_size=Pt(8.5), color=RGBColor(0x55, 0x55, 0x55))

    # --- 中列：学校 Logo ---
    p_mid = c_mid.add_paragraph()
    p_mid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if basics.school_logo:
        logo_path = PROJECT_ROOT / basics.school_logo
        if logo_path.exists():
            r_mid = p_mid.add_run()
            r_mid.add_picture(str(logo_path), width=Cm(2.2))

    # --- 右列：个人照片 ---
    p_right = c_right.add_paragraph()
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if basics.avatar:
        avatar_path = PROJECT_ROOT / basics.avatar
        if avatar_path.exists():
            r_right = p_right.add_run()
            r_right.add_picture(str(avatar_path), width=Cm(2.2))

    # 给头部表格下方加一条主分隔线（这里利用一个极窄的空段落作为载体，不会增加间距）
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(2)
    para.paragraph_format.space_after = Pt(2)
    para.paragraph_format.line_spacing = Pt(1) # 高度压到极致
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")       # 8 个 1/8 磅 = 1.0 磅厚度
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "888888")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _add_education(doc: Document, profile: UserProfile):
    """渲染教育经历板块"""
    if not profile.education:
        return

    _add_section_title(doc, "教育经历")

    for edu in profile.education:
        left = f"{edu.school} · {edu.degree} · {edu.major}"
        right = f"{edu.start_date} – {edu.end_date}"
        _add_line_with_right_date(doc, left, right, bold=True)

        details = []
        if edu.gpa:
            details.append(f"GPA: {edu.gpa}")
        if edu.ranking:
            details.append(f"排名: {edu.ranking}")
        if edu.research_direction:
            details.append(f"研究方向: {edu.research_direction}")
        if details:
            _add_plain_line(doc, "　　".join(details))

        if edu.courses:
            _add_plain_line(doc, f"核心课程：{'、'.join(edu.courses)}")


def _add_skills(doc: Document, profile: UserProfile):
    """渲染专业技能板块"""
    if not profile.skills:
        return

    skills = profile.skills
    _add_section_title(doc, "专业技能")

    if skills.programming_languages:
        for lang in skills.programming_languages:
            text = f"{lang.name}（{lang.level}）"
            if lang.details:
                text += f"：{lang.details}"
            _add_bullet_point(doc, text)

    if skills.frameworks_and_tools:
        _add_bullet_point(doc, f"框架与工具：{'、'.join(skills.frameworks_and_tools)}")

    if skills.databases:
        _add_bullet_point(doc, f"数据库：{'、'.join(skills.databases)}")


def _add_internships(doc: Document, profile: UserProfile):
    """渲染实习经历板块"""
    if not profile.internships:
        return

    _add_section_title(doc, "实习经历")

    for intern in profile.internships:
        left = f"{intern.company} · {intern.role}"
        if intern.department:
            left += f" · {intern.department}"
        right = f"{intern.start_date} – {intern.end_date}"
        _add_line_with_right_date(doc, left, right, bold=True)

        for highlight in intern.highlights:
            _add_bullet_point(doc, highlight)


def _add_projects(doc: Document, profile: UserProfile):
    """渲染项目经历板块"""
    if not profile.projects:
        return

    _add_section_title(doc, "项目经历")

    for proj in profile.projects:
        left = proj.name
        if proj.role:
            left += f" · {proj.role}"
        right = f"{proj.start_date} – {proj.end_date}"
        _add_line_with_right_date(doc, left, right, bold=True)

        if proj.tech_stack:
            _add_plain_line(doc, f"技术栈：{'、'.join(proj.tech_stack)}")

        for highlight in proj.highlights:
            _add_bullet_point(doc, highlight)


def _add_research(doc: Document, profile: UserProfile):
    """渲染科研经历板块"""
    if not profile.research:
        return

    _add_section_title(doc, "科研经历")

    for res in profile.research:
        left = res.name
        if res.role:
            left += f" · {res.role}"
        right = f"{res.start_date} – {res.end_date}"
        _add_line_with_right_date(doc, left, right, bold=True)

        for highlight in res.highlights:
            _add_bullet_point(doc, highlight)


def _add_articles(doc: Document, profile: UserProfile):
    """渲染论文发表板块"""
    if not profile.articles:
        return

    _add_section_title(doc, "论文发表")

    for i, article in enumerate(profile.articles, 1):
        details = []
        if article.author_order:
            details.append(article.author_order)
        if article.cas_partition:
            details.append(article.cas_partition)
        if article.impact_factor:
            details.append(f"IF: {article.impact_factor}")
        if article.citation_counts:
            details.append(f"被引: {article.citation_counts}")
            
        details_str = f"（{'，'.join(details)}）" if details else ""
        text = f"[{i}] {article.cite} {details_str}"
        
        para = doc.add_paragraph()
        para.paragraph_format.space_before = Pt(1)
        para.paragraph_format.space_after = Pt(1)
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.first_line_indent = Cm(-0.5)
        run = para.add_run(text)
        _set_font(run, font_size=_FONT_SIZE_BODY)


def _add_honors(doc: Document, profile: UserProfile):
    """渲染荣誉奖项板块"""
    if not profile.honors_and_awards:
        return

    _add_section_title(doc, "荣誉奖项")

    for award in profile.honors_and_awards:
        left = award.title
        if award.level:
            left += f"（{award.level}）"
        _add_line_with_right_date(doc, left, award.date)


def _add_certs(doc: Document, profile: UserProfile):
    """渲染资格证书板块"""
    if not profile.certifications:
        return

    _add_section_title(doc, "资格证书")

    for cert in profile.certifications:
        text = cert.certificate
        if cert.detail:
            text += cert.detail
        _add_bullet_point(doc, text)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def build_docx(profile: UserProfile, output_path: Path) -> Path:
    """
    主入口函数：从 UserProfile 构建一份完整的 Word 简历并保存。
    """
    doc = Document()
    _setup_page(doc)

    _add_header(doc, profile)
    _add_education(doc, profile)
    _add_skills(doc, profile)
    _add_internships(doc, profile)
    _add_projects(doc, profile)
    _add_research(doc, profile)
    _add_articles(doc, profile)
    _add_honors(doc, profile)
    _add_certs(doc, profile)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path

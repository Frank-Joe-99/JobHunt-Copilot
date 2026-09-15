// Python 通过 sys_inputs 传入 JSON 字符串，避免共用临时文件。
#let data = json(bytes(sys.inputs.profile))
#let basics = data.basics
#let has_text(value) = value != none and value != ""
#let asset_path(path) = "/" + path.replace("\\", "/").trim("/")

// 1. 设置 1cm 边距与纸张
#set page(paper: "a4", margin: 1cm)

// 2. 设置全局字体与字号 (9.5pt 正文)
#set text(font: ("Arial", "Microsoft YaHei", "SimHei"), size: 9.5pt)

// 3. 设置行间距与段间距（leading 是额外间距，并非 Word 的倍数行距）
#set par(leading: 0.9em, spacing: 0.9em)

// 颜色定义
#let gray_color = rgb("555555")
#let line_color = rgb("888888")

// =====================================================================
// 排版辅助函数
// =====================================================================

// 板块标题：加大不同内容块之间的间距，并在横线与文字之间留出更多呼吸感
#let section(title) = block(
  width: 100%,
  above: 18pt,
  below: 8pt,
  breakable: false,
  sticky: true,
  inset: (bottom: 8pt),
  stroke: (bottom: 0.6pt + line_color),
)[#text(size: 11pt, weight: "bold")[#title]]

// 左右布局行
#let item_line(left, right, bold: false) = {
  if bold {
    text(weight: "bold")[#left]
  } else {
    left
  }
  h(1fr) // 制表位填充
  right
  linebreak()
}

// 无序列表项（悬挂缩进）
#let bullet_point(body) = par(hanging-indent: 0.5cm)[#box(width: 0.5cm)[•]#body]

// =====================================================================
// 1. 头部：三列布局 (姓名联系方式 13cm, Logo 3cm, 头像 3cm)
// =====================================================================
#grid(
  columns: (13cm, 3cm, 3cm),
  align: (left + horizon, center + horizon, right + horizon),
  [
    #text(size: 15pt, weight: "bold")[#basics.name]
    #v(4pt)
    #let contacts = ()
    #contacts.push(basics.phone)
    #contacts.push(basics.email)
    #contacts.push(basics.location)
    #if has_text(basics.at("github", default: none)) { contacts.push("GitHub: " + basics.github.trim("/").split("/").last()) }
    #if has_text(basics.at("blog", default: none)) { contacts.push("Blog") }
    #text(size: 8.5pt, fill: gray_color)[#(contacts.join(" | "))]
    
    #if data.at("objective", default: none) != none {
      // 花括号内是代码模式；只有进入 [...] 内容块后才需要 #。
      let obj = data.objective
      let objs = ("求职意向：" + obj.target_role,)
      if has_text(obj.at("target_industry", default: none)) { objs.push("行业：" + obj.target_industry) }
      if obj.at("expected_locations", default: ()).len() > 0 { objs.push("城市：" + obj.expected_locations.join("、")) }
      v(0pt)
      text(size: 8.5pt, fill: gray_color)[#(objs.join(" | "))]
    }
  ],
  [
    #if has_text(basics.at("school_logo", default: none)) {
      // 在 Python 端我们配置了以项目根目录为读取源
      image(asset_path(basics.school_logo), width: 2.2cm)
    }
  ],
  [
    #if has_text(basics.at("avatar", default: none)) {
      image(asset_path(basics.avatar), width: 2.2cm)
    }
  ]
)
#v(8pt)
#line(length: 100%, stroke: 1pt + line_color)
#v(6pt)

// =====================================================================
// 2. 教育经历
// =====================================================================
#if "education" in data and data.education.len() > 0 {
  section("教育经历")
  for edu in data.education {
    item_line(edu.school + " · " + edu.degree + " · " + edu.major, edu.start_date + " – " + edu.end_date, bold: true)
    
    let details = ()
    if "gpa" in edu and edu.gpa != none { details.push("GPA: " + edu.gpa) }
    if "ranking" in edu and edu.ranking != none { details.push("排名: " + edu.ranking) }
    if "research_direction" in edu and edu.research_direction != none { details.push("研究方向: " + edu.research_direction) }
    if details.len() > 0 [ #(details.join("　　")) \ ]
    
    if "courses" in edu and edu.courses.len() > 0 [ 核心课程：#(edu.courses.join("、")) \ ]
  }
}

// =====================================================================
// 3. 专业技能
// =====================================================================
#if data.at("skills", default: none) != none {
  let skills = data.skills
  if (
    skills.at("programming_languages", default: ()).len() > 0
    or skills.at("frameworks_and_tools", default: ()).len() > 0
    or skills.at("databases", default: ()).len() > 0
  ) {
    section("专业技能")
  }
  if "programming_languages" in skills {
    for lang in skills.programming_languages {
      let t = lang.name + "（" + lang.level + "）"
      if "details" in lang and lang.details != none { t += "：" + lang.details }
      bullet_point(t)
    }
  }
  if "frameworks_and_tools" in skills and skills.frameworks_and_tools.len() > 0 {
    bullet_point("框架与工具：" + skills.frameworks_and_tools.join("、"))
  }
  if "databases" in skills and skills.databases.len() > 0 {
    bullet_point("数据库：" + skills.databases.join("、"))
  }
}

// =====================================================================
// 4. 实习经历
// =====================================================================
#if "internships" in data and data.internships.len() > 0 {
  section("实习经历")
  for intern in data.internships {
    let left = intern.company + " · " + intern.role
    if "department" in intern and intern.department != none { left += " · " + intern.department }
    item_line(left, intern.start_date + " – " + intern.end_date, bold: true)
    for highlight in intern.highlights { bullet_point(highlight) }
  }
}

// =====================================================================
// 5. 项目经历
// =====================================================================
#if "projects" in data and data.projects.len() > 0 {
  section("项目经历")
  for proj in data.projects {
    let left = proj.name
    if "role" in proj and proj.role != none { left += " · " + proj.role }
    item_line(left, proj.start_date + " – " + proj.end_date, bold: true)
    if "tech_stack" in proj and proj.tech_stack.len() > 0 [ 技术栈：#(proj.tech_stack.join("、")) \ ]
    for highlight in proj.highlights { bullet_point(highlight) }
  }
}

// =====================================================================
// 6. 科研经历
// =====================================================================
#if "research" in data and data.research.len() > 0 {
  section("科研经历")
  for res in data.research {
    let left = res.name
    if "role" in res and res.role != none { left += " · " + res.role }
    item_line(left, res.start_date + " – " + res.end_date, bold: true)
    for highlight in res.highlights { bullet_point(highlight) }
  }
}

// =====================================================================
// 7. 论文发表 (悬挂缩进排版)
// =====================================================================
#if "articles" in data and data.articles.len() > 0 {
  section("论文发表")
  for (i, article) in data.articles.enumerate() {
    let details = ()
    if "author_order" in article and article.author_order != none { details.push(article.author_order) }
    if "cas_partition" in article and article.cas_partition != none { details.push(article.cas_partition) }
    if "impact_factor" in article and article.impact_factor != none { details.push("IF: " + str(article.impact_factor)) }
    if "citation_counts" in article and article.citation_counts != none { details.push("被引: " + str(article.citation_counts)) }
    
    let details_str = if details.len() > 0 { " （" + details.join("，") + "）" } else { "" }
    
    // 悬挂缩进
    par(hanging-indent: 0.5cm)[
      [#(i+1)] #article.cite #details_str
    ]
  }
}

// =====================================================================
// 8. 荣誉奖项
// =====================================================================
#if "honors_and_awards" in data and data.honors_and_awards.len() > 0 {
  section("荣誉奖项")
  for award in data.honors_and_awards {
    let left = award.title
    if "level" in award and award.level != none { left += "（" + award.level + "）" }
    item_line(left, award.date)
  }
}

// =====================================================================
// 9. 资格证书
// =====================================================================
#if "certifications" in data and data.certifications.len() > 0 {
  section("资格证书")
  for cert in data.certifications {
    let text = cert.certificate
    if "detail" in cert and cert.detail != none { text += cert.detail }
    bullet_point(text)
  }
}

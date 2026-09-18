from enum import Enum
from pydantic import BaseModel, Field, AliasChoices


# ==============================================================================
# 1. 个人核心档案数据契约 (对应 config/profile.yaml)
# ==============================================================================

class Basics(BaseModel):
    """
    个人基本信息解析
    """
    name: str = Field(..., description="姓名（必填）")
    birth_year: int = Field(..., description="出生年份，如 2002（必填）")
    phone: str = Field(..., description="联系手机号（必填）")
    email: str = Field(..., description="电子邮箱（必填）")
    location: str = Field(..., description="现居住城市/所在地（必填）")

    # 就读大学与院系（选填，应届在读生可填，已毕业者亦可保留）
    school: str | None = Field(None, description="当前就读大学/毕业院校（选填）")
    school_logo: str | None = Field(None, description="当前就读学校矢量校徽相对路径（选填）")
    department: str | None = Field(None, description="当前院系（选填）")
    degree: str | None = Field(None, description="当前攻读/最高学位（选填）")

    # 更多个人与社交信息（选填）
    gender: str | None = Field(None, description="性别（选填）")
    political_status: str | None = Field(None, description="政治面貌（选填）")
    avatar: str | None = Field(None, description="证件照相对路径（选填）")
    github: str | None = Field(None, description="GitHub 主页链接（选填）")
    linkedin: str | None = Field(None, description="LinkedIn 主页链接（选填）")
    blog: str | None = Field(None, description="个人博客/作品集链接（选填）")


class Objective(BaseModel):
    """
    求职意向
    """
    target_role: str = Field(..., description="意向岗位名称，如：后端开发工程师")
    expected_locations: list[str] = Field(default_factory=list, description="意向工作城市列表")
    target_industry: str | None = Field(None, description="意向行业领域，如：互联网 / 人工智能（选填）")


class Education(BaseModel):
    """
    单段教育经历实体
    无论是本科、硕士、博士还是直博，每读一个阶段就对应一个 Education 对象
    """
    school: str = Field(..., description="学校名称，如：北京理工大学")
    major: str = Field(..., description="专业名称，如：计算机科学与技术")
    degree: str = Field(..., description="学位或学历阶段，如：学士/本科、硕士、博士、直博、硕博连读")
    start_date: str = Field(..., description="入学时间，如：2023.09")
    end_date: str = Field(..., description="毕业或预计毕业时间，如：2026.06 / 至今")

    # 选填字段（本科/硕博按需填写）
    gpa: str | None = Field(None, description="GPA 成绩，如：3.8/4.0")
    ranking: str | None = Field(None, description="专业排名，如：Top 5%")
    courses: list[str] = Field(default_factory=list, description="核心专业课程列表（选填）")
    award: list[str] = Field(default_factory=list, description="校内获得的奖学金/竞赛荣誉简述列表（选填）")

    # 针对 硕士/博士/直博 的加分学术字段（本科生可不填）
    research_direction: str | None = Field(None, description="研究方向/课题，如：大语言模型推理优化（选填）")
    advisor: str | None = Field(None, description="指导导师姓名（选填）")
    laboratory: str | None = Field(None, description="所在实验室/课题组名称（选填）")
    logo: str | None = Field(None, description="学校校徽矢量图相对路径（选填）")


class ProgrammingLanguage(BaseModel):
    """
    单一编程语言掌握情况
    """
    name: str = Field(..., description="编程语言名称，如：Python、Go、C/C++")
    level: str = Field(..., description="熟练程度，如：精通、熟练、良好、了解")
    details: str | None = Field(None, description="掌握的具体细节、底层机制或应用场景（选填）")


class Skills(BaseModel):
    """
    专业技能清单（整个类可选）
    """
    programming_languages: list[ProgrammingLanguage] = Field(
        default_factory=list, description="掌握的编程语言列表"
    )
    frameworks_and_tools: list[str] = Field(
        default_factory=list, description="常用框架与工具链列表，如：FastAPI、Docker、Git"
    )
    databases: list[str] = Field(
        default_factory=list, description="数据库与中间件掌握情况列表，如：MySQL、Redis、Milvus"
    )


class Internship(BaseModel):
    """
    企业实习经历实体（整个类可选，没有可不写）
    """
    company: str = Field(..., description="实习公司名称")
    role: str = Field(..., description="实习职位名称，如：后端开发实习生")
    start_date: str = Field(..., description="实习开始日期，如：2025.06")
    end_date: str = Field(..., description="实习结束日期，如：2025.11 / 至今")
    department: str | None = Field(None, description="所在部门/业务线，如：基础架构研发部（选填）")
    city: str | None = Field(None, description="工作城市，如：北京（选填）")
    highlights: list[str] = Field(
        default_factory=list, description="实习工作核心亮点（建议遵循 STAR 法则并带有量化数据）"
    )


class Project(BaseModel):
    """
    实战项目经历实体（整个类可选，没有可不写）
    """
    name: str = Field(..., description="项目名称")
    start_date: str = Field(..., description="项目开始时间，如：2026.01")
    end_date: str = Field(..., description="项目结束时间，如：2026.03 / 至今")
    role: str | None = Field(None, description="所任角色，如：核心开发者 / 负责人（选填）")
    tech_stack: list[str] = Field(default_factory=list, description="所用关键技术栈列表")
    repo_url: str | None = Field(None, description="开源仓库地址或演示 Demo 链接（选填）")
    highlights: list[str] = Field(
        default_factory=list, description="项目核心架构设计、技术突破与量化成果亮点"
    )


class ResearchProject(BaseModel):
    """
    学术科研课题/项目实体（主要针对硕博生或有科研经历的本科生，整个类可选）
    """
    name: str = Field(..., description="科研课题或学术研究项目名称")
    start_date: str = Field(..., description="研究开始时间，如：2022.01")
    end_date: str = Field(..., description="研究结束时间，如：2024.01 / 至今")
    role: str | None = Field(None, description="承担角色，如：项目负责人、核心研究员（选填）")
    highlights: list[str] = Field(
        default_factory=list, description="科研内容、实验方法、创新点与产出成果"
    )


class Article(BaseModel):
    """
    学术论文发表情况（整个类可选，没有可不写）
    """
    cite: str = Field(..., description="论文完整标准引用格式文本 (GB/T 7714 或 APA)")
    author_order: str | None = Field(None, description="作者顺位，如：第一作者、共同一作、通讯作者（选填）")
    impact_factor: float | None = Field(None, description="期刊/会议影响因子 (IF)（选填）")
    cas_partition: str | None = Field(None, description="中科院分区或 CCF 等级，如：一区、CCF-A（选填）")
    citation_counts: int | None = Field(
        None,
        validation_alias=AliasChoices("citation_counts", "catation_counts"),
        description="论文被引次数（选填）"
    )


class HonorAndAward(BaseModel):
    """
    荣誉奖项或奖学金详细信息（整个类可选）
    """
    title: str = Field(..., description="所获荣誉/奖学金/竞赛名称")
    date: str = Field(..., description="获奖日期，如：2024.11")
    level: str | None = Field(None, description="荣誉等级，如：院系级、校级、省市级、国家级（选填）")


class Certification(BaseModel):
    """
    技能或资格证书获得情况（整个类可选）
    """
    certificate: str = Field(..., description="证书名称，如：英语六级 (CET-6)")
    detail: str | None = Field(None, description="证书详情，如成绩分值、等级说明等（选填）")


class UserProfile(BaseModel):
    """
    个人完整主档案聚合根对象（严格映射 config/profile.yaml）
    """
    basics: Basics = Field(..., description="个人基础信息（必填）")
    objective: Objective | None = Field(None, description="求职意向（可选）")
    education: list[Education] = Field(default_factory=list, description="教育经历列表（建议按时间倒序）")
    skills: Skills | None = Field(None, description="专业技能清单（可选）")
    internships: list[Internship] = Field(default_factory=list, description="实习经历列表（可选）")
    projects: list[Project] = Field(default_factory=list, description="实战项目经历列表（可选）")
    research: list[ResearchProject] = Field(default_factory=list, description="学术科研课题列表（可选）")
    articles: list[Article] = Field(default_factory=list, description="学术论文发表列表（可选）")
    honors_and_awards: list[HonorAndAward] = Field(default_factory=list, description="所获荣誉与奖项列表（可选）")
    certifications: list[Certification] = Field(default_factory=list, description="资格证书列表（可选）")


# ==============================================================================
# 2. 求职意愿与机会雷达配置契约 (对应 config/preferences.yaml)
# ==============================================================================

class ExpectedSalary(BaseModel):
    """
    期望月薪区间（单位：k）
    """
    min: int = Field(..., description="期望最低月薪 (k)")
    max: int = Field(..., description="期望最高月薪 (k)")


class SearchCriteria(BaseModel):
    """
    岗位搜索与雷达过滤准则
    """
    target_roles: list[str] = Field(default_factory=list, description="目标求职岗位名称列表")
    target_locations: list[str] = Field(default_factory=list, description="意向工作城市列表")
    company_types: list[str] = Field(default_factory=list, description="偏好公司性质/类型")
    expected_salary_monthly_k: ExpectedSalary | None = Field(None, description="期望月薪区间（选填）")


class JobRadarConfig(BaseModel):
    """
    校招/社招岗位雷达扫描器运行参数
    """
    enabled: bool = Field(True, description="是否启用自动岗位雷达扫描")
    fetch_interval_hours: int = Field(24, description="雷达扫描周期（小时）")
    max_recommendations_per_run: int = Field(10, description="单次运行精选推送的最大岗位数量")
    min_match_score: int = Field(75, ge=0, le=100, description="最低岗位匹配度推荐阈值 (0-100)")


class ChannelsConfig(BaseModel):
    """
    招聘数据采集渠道开关与来源
    """
    v2ex_jobs: bool = Field(True, description="是否抓取 V2EX 酷工作板块")
    nowcoder_campus: bool = Field(True, description="是否抓取牛客校招信息")
    rss_sources: list[str] = Field(default_factory=list, description="自定义外部 RSS/API 订阅源列表")


class EmailNotificationConfig(BaseModel):
    """
    邮件推送配置
    """
    enabled: bool = Field(False, description="是否开启邮件通知")
    receiver_email: str | None = Field(None, description="接收推送的邮箱地址")


class NotificationConfig(BaseModel):
    """
    报告生成与触达通知配置
    """
    generate_markdown_report: bool = Field(True, description="是否在 storage/radar_reports/ 生成 Markdown 岗位简报")
    terminal_alert: bool = Field(True, description="是否在控制台打印彩色高亮提示")
    email_notification: EmailNotificationConfig = Field(
        default_factory=EmailNotificationConfig, description="邮件通知配置"
    )


class JobPreferences(BaseModel):
    """
    用户求职偏好与雷达配置聚合对象（严格映射 config/preferences.yaml）
    """
    job_radar: JobRadarConfig = Field(default_factory=JobRadarConfig, description="雷达扫描频率与阈值配置")
    search_criteria: SearchCriteria = Field(..., description="搜索与过滤准则（必填）")
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig, description="数据采集渠道配置")
    notification: NotificationConfig = Field(default_factory=NotificationConfig, description="通知与报告生成配置")


# ==============================================================================
# 3. 系统运行与基础设施配置契约 (对应 config/settings.yaml)
# ==============================================================================

class AppInfoConfig(BaseModel):
    """
    应用基础信息
    """
    name: str = Field("JobHunt-Copilot", description="应用名称")
    version: str = Field("0.1.0", description="应用版本")
    log_level: str = Field("INFO", description="日志等级：DEBUG, INFO, WARNING, ERROR")


class LLMProviderConfig(BaseModel):
    """
    单一 LLM 供应商参数配置
    """
    api_key: str = Field(..., description="大模型厂商 API Key（必填）")
    base_url: str | None = Field(None, description="API 基础请求 URL（选填）")
    model: str = Field(..., description="模型名称或版本号，如：deepseek-chat, gpt-4o, claude-3-5-sonnet")
    temperature: float = Field(0.3, ge=0.0, le=2.0, description="采样温度")
    max_tokens: int | None = Field(None, gt=0, description="最大生成 token 数（选填）")


class LLMConfig(BaseModel):
    """
    大模型全局调度配置
    """
    default_provider: str = Field("deepseek", description="默认使用的大模型供应商名称")
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict, description="各供应商具体参数字典")


class ResumeGenerationConfig(BaseModel):
    """
    简历渲染与排版引擎配置
    """
    engine: str = Field("typst", description="简历编译引擎（typst 或 html）")
    default_template: str = Field("modern_geek", description="默认模版风格名称")
    page_limit: int = Field(1, ge=1, description="强制约束页面数量上限（默认 A4 单页）")


class GithubConfig(BaseModel):
    """
    GitHub API 客户端配置
    """
    token: str = Field("", description="GitHub 访问 Token（选填，用于提升 API 速率限制）")


class AppSettings(BaseModel):
    """
    全系统运行时基础设施配置聚合根（严格映射 config/settings.yaml）
    """
    app: AppInfoConfig = Field(default_factory=AppInfoConfig, description="应用基础信息")
    llm: LLMConfig = Field(default_factory=LLMConfig, description="大语言模型连接配置")
    resume_generation: ResumeGenerationConfig = Field(
        default_factory=ResumeGenerationConfig, description="简历排版引擎配置"
    )
    github: GithubConfig = Field(default_factory=GithubConfig, description="GitHub 服务配置")


# ==============================================================================
# 4. 简历润色与 ATS 诊断数据契约 (对应 skills/resume_polisher)
# ==============================================================================

class PolishedItem(BaseModel):
    """单条经历 STAR 润色结果"""
    source: str = Field(..., description="经历来源")
    original: str = Field(..., description="润色前原始描述")
    polished: str = Field(..., description="STAR 润色后描述")
    situation_and_task: str = Field("", description="背景与目标")
    action: str = Field("", description="核心行动")
    result: str = Field("", description="量化成果")
    improvement_reason: str = Field("", description="提分亮点")


class ResumePolishReport(BaseModel):
    """整份简历润色综合报告"""
    summary: str = Field(..., description="总体评述")
    items: list[PolishedItem] = Field(default_factory=list, description="逐条润色清单")


class ATSScoreReport(BaseModel):
    """ATS 关键词诊断报告"""
    score: int = Field(..., ge=0, le=100, description="ATS 评分")
    dimension_scores: dict[str, int] = Field(default_factory=dict, description="各维度得分")
    matched_keywords: list[str] = Field(default_factory=list, description="命中关键词")
    missing_keywords: list[str] = Field(default_factory=list, description="缺失关键词")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


# ==============================================================================
# 5. 目标岗位 JD 穿透与匹配数据契约 (对应 skills/jd_matcher)
# ==============================================================================

class JobDescription(BaseModel):
    """结构化岗位描述"""
    company: str = Field(..., description="公司名称")
    role: str = Field(..., description="岗位名称")
    department: str | None = Field(None, description="部门")
    hard_requirements: list[str] = Field(default_factory=list, description="硬性技术要求")
    soft_requirements: list[str] = Field(default_factory=list, description="软技能要求")
    bonus_items: list[str] = Field(default_factory=list, description="加分项")
    raw_text: str = Field("", description="JD 原文")


class SkillGap(BaseModel):
    """单项技能比对"""
    skill: str = Field(..., description="技能名称")
    status: str = Field(..., description="matched / partial / missing")
    evidence: str = Field("", description="简历中的佐证")
    suggestion: str = Field("", description="补强建议")


class MatchResult(BaseModel):
    """岗位匹配分析结果"""
    score: int = Field(..., ge=0, le=100, description="契合度评分")
    overview: str = Field(..., description="匹配评述")
    matched_skills: list[SkillGap] = Field(default_factory=list, description="命中技能")
    missing_skills: list[SkillGap] = Field(default_factory=list, description="缺失技能")
    resume_tuning_advice: list[str] = Field(default_factory=list, description="简历调优建议")
    cover_letter_draft: str = Field("", description="自荐信草稿")


class ProjectRecommendation(BaseModel):
    """单个开源项目推荐条目"""
    repo_name: str                  # 仓库全名 owner/repo
    repo_url: str                   # GitHub 链接
    stars: int = 0
    language: str | None = None     # 主要编程语言
    languages: str | None = None    # 兼容别名
    why_recommended: str            # 推荐理由
    learning_path: str              # 学习路径：重点看哪几个文件/模块
    interview_tips: str             # 面试考点：可能会追问的问题
    star_resume_sample: str         # 写进简历的 STAR 模板


class ProjectRecommendationReport(BaseModel):
    """开源实战项目推荐报告"""
    overview: str = Field(..., description="针对技能缺口的总体学习与提升建议")
    recommendations: list[ProjectRecommendation] = Field(
        default_factory=list, description="精选推荐的开源项目列表"
    )


# ==============================================================================
# 6. 机会雷达批量评估与机会排名契约 (对应 skills/job_radar)
# ==============================================================================

class RankedOpportunity(BaseModel):
    """单个岗位的雷达评估与排名条目"""
    rank: int = Field(..., description="推荐排名序号 (1, 2, 3...)")
    company: str = Field(..., description="招聘企业")
    role: str = Field(..., description="目标岗位名称")
    department: str | None = Field(None, description="部门/业务线")
    score: int = Field(..., ge=0, le=100, description="综合匹配度得分 (0-100)")
    tier: str = Field(..., description="机会分层：'优先主投' / '微调冲刺' / '暂缓考虑'")
    verdict: str = Field(..., description="投递建议策略一句话总结")
    top_matches: list[str] = Field(default_factory=list, description="核心命中优势技能")
    key_gaps: list[str] = Field(default_factory=list, description="主要技能缺口")
    overview: str = Field("", description="岗位匹配综合简评")
    tuning_advice: list[str] = Field(default_factory=list, description="针对该岗位的简历微调建议")


class JobRadarReport(BaseModel):
    """机会雷达综合诊断与战略报告"""
    created_at: str = Field(..., description="报告生成时间")
    total_scanned: int = Field(..., description="本次扫描的岗位总数")
    opportunities: list[RankedOpportunity] = Field(default_factory=list, description="按得分降序排列的机会列表")
    common_skill_gaps: list[dict[str, int | str]] = Field(
        default_factory=list,
        description="跨岗位高频共性缺口统计 [{'skill': 'Kafka', 'count': 3, 'importance': '高'}]"
    )
    strategic_advice: str = Field("", description="求职整体投递优先级与攻坚战略建议")
    report_file_path: str = Field("", description="导出的 Markdown 报告物理路径")


# ==============================================================================
# 7. 模拟面试模块数据契约 (对应 skills/mock_interviewer)
# ==============================================================================

class InterviewStage(str, Enum):
    """面试流程阶段枚举"""
    INTRO = "intro"                       # 阶段 0：开场破冰与自我介绍
    RESUME_DEEP_DIVE = "resume_deep_dive" # 阶段 1：简历项目与经历穿透深挖
    FUNDAMENTALS = "fundamentals"         # 阶段 2：计算机基础与核心八股考点
    BEHAVIORAL = "behavioral"             # 阶段 3：行为情境与软实力考察
    REVERSE_QA = "reverse_qa"             # 阶段 4：候选人反问环节
    COMPLETED = "completed"               # 阶段 5：整场面试已结束


class InterviewRole(str, Enum):
    """面试官角色风格人设枚举"""
    STRICT_ARCHITECT = "strict_architect" # 严苛型大牛架构师（追问底层、性能瓶颈、边界极限）
    PRACTICAL_LEAD = "practical_lead"     # 务实型研发主管（关注业务落地、敏捷排错、系统可用性）
    HRBP = "hrbp"                         # 亲和型 HR 面试官（关注求职动机、团队协作、稳定性与抗压）


class InterviewTurn(BaseModel):
    """单轮问答记录"""
    turn_id: int = Field(..., description="问答轮次序号 (从 1 开始)")
    stage: InterviewStage = Field(..., description="所属面试阶段")
    question: str = Field(..., description="面试官提出的问题")
    answer: str = Field("", description="候选人的回答内容")
    feedback: str = Field("", description="针对本轮回答的即时简析或追问提示")


class InterviewSession(BaseModel):
    """模拟面试会话上下文状态载体 (全程记忆容器)"""
    session_id: str = Field(..., description="会话唯一识别码")
    role: InterviewRole = Field(default=InterviewRole.STRICT_ARCHITECT, description="当前面试官人设")
    current_stage: InterviewStage = Field(default=InterviewStage.INTRO, description="当前进行的面试阶段")
    history: list[InterviewTurn] = Field(default_factory=list, description="完整问答对话历史")
    target_role: str = Field("后端开发工程师", description="面试目标岗位名称")
    target_company: str = Field("目标企业", description="面试目标企业名称")
    is_finished: bool = Field(False, description="整场面试是否已完成")


class InterviewEvaluationReport(BaseModel):
    """面试结束后生成的全维度复盘体检报告"""
    overall_score: int = Field(..., ge=0, le=100, description="面试综合得分 (0-100)")
    result: str = Field(..., description="面试结果建议：'建议通过 (Pass)' / '有待商榷 (Weak Pass)' / '暂不匹配 (Reject)'")
    summary: str = Field(..., description="面试官对整场表现的总体评语")
    dimension_scores: dict[str, int] = Field(
        default_factory=dict,
        description="各维度打分 (如：技术深度、计算机基础、逻辑表达、工程素养、应变能力)"
    )
    highlights: list[str] = Field(default_factory=list, description="回答非常出彩的高光亮点")
    weaknesses: list[str] = Field(default_factory=list, description="暴露出的致命失分点或技术硬伤")
    model_answers: list[dict[str, str]] = Field(
        default_factory=list,
        description="针对失分问题的标准满分回答示范 [{'question': '...', 'ideal_answer': '...'}]"
    )
    report_file_path: str = Field("", description="保存到本地的 Markdown 复盘报告物理路径")


# ==============================================================================
# 兼容别名
# ==============================================================================
objective = Objective
education = Education
honors_and_awards = HonorAndAward
certifications = Certification
UserPreferences = JobPreferences
SystemSettings = AppSettings
JDMatchReport = MatchResult
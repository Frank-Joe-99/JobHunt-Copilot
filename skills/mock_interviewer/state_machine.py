"""
面试流程状态机控制器 (Interview State Machine)
纯粹负责面试阶段的推进规则、轮次计数与快捷指令拦截，不直接绑定具体 IO。
"""

from core.state import InterviewStage, InterviewSession


class InterviewStateMachine:
    """面试流程状态机"""

    # 1. 严格有序的阶段流水线
    STAGE_ORDER: list[InterviewStage] = [
        InterviewStage.INTRO,
        InterviewStage.RESUME_DEEP_DIVE,
        InterviewStage.FUNDAMENTALS,
        InterviewStage.BEHAVIORAL,
        InterviewStage.REVERSE_QA,
        InterviewStage.COMPLETED,
    ]

    # 2. 各阶段默认规划的问答轮数
    MAX_TURNS_PER_STAGE: dict[InterviewStage, int] = {
        InterviewStage.INTRO: 1,           # 自我介绍 1 问
        InterviewStage.RESUME_DEEP_DIVE: 2,# 简历项目深挖 2 问 (1 问 + 1 追问)
        InterviewStage.FUNDAMENTALS: 1,    # 核心八股考点 1 问
        InterviewStage.BEHAVIORAL: 1,      # 行为情境题 1 问
        InterviewStage.REVERSE_QA: 1,      # 候选人反问 1 问
        InterviewStage.COMPLETED: 0,
    }

    def handle_command(
        self, user_input: str, session: InterviewSession
    ) -> str | None:
        """
        检查并拦截快捷指令。
        Returns:
            "next": 用户触发跳过阶段
            "finish": 用户触发提前交卷
            None: 正常回答，非指令
        """
        clean_input = user_input.strip().lower()
        if clean_input in ("/next", "next", "跳过"):
            self.advance_stage(session)
            return "next"
        elif clean_input in ("/finish", "finish", "退出", "quit", "/quit", "交卷"):
            # 立即提前交卷，直达完成态
            session.current_stage = InterviewStage.COMPLETED
            session.is_finished = True
            return "finish"
        return None

    def get_current_stage_turns(self, session: InterviewSession) -> int:
        """计算当前阶段已经完成了几轮问答"""
        return sum(1 for turn in session.history if turn.stage == session.current_stage)

    def should_advance(self, session: InterviewSession) -> bool:
        """判断当前阶段是否已问够设定的轮数，该进入下一阶段了"""
        current_turns = self.get_current_stage_turns(session)
        max_allowed = self.MAX_TURNS_PER_STAGE.get(session.current_stage, 1)
        return current_turns >= max_allowed

    def advance_stage(self, session: InterviewSession) -> InterviewStage:
        """将面试会话推向下一个阶段"""
        try:
            curr_idx = self.STAGE_ORDER.index(session.current_stage)
            next_idx = curr_idx + 1

            # 达到或超过最后一个阶段时，标记完成
            if next_idx >= len(self.STAGE_ORDER) - 1:
                session.current_stage = InterviewStage.COMPLETED
                session.is_finished = True
            else:
                session.current_stage = self.STAGE_ORDER[next_idx]
        except ValueError:
            session.current_stage = InterviewStage.COMPLETED
            session.is_finished = True

        return session.current_stage

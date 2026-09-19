"""
AI 场景化模拟面试官模块 (Mock Interviewer Skill)
"""

from skills.mock_interviewer.handler import (
    start_interview,
    step_interview_stream,
    finish_interview,
)
from skills.mock_interviewer.state_machine import InterviewStateMachine
from skills.mock_interviewer.prompt import (
    INTERVIEWER_PERSONAS,
    STAGE_GUIDELINES,
    DRILL_DOWN_DIRECTIVE,
    EVALUATION_REPORT_SYSTEM,
)

__all__ = [
    "start_interview",
    "step_interview_stream",
    "finish_interview",
    "InterviewStateMachine",
    "INTERVIEWER_PERSONAS",
    "STAGE_GUIDELINES",
    "DRILL_DOWN_DIRECTIVE",
    "EVALUATION_REPORT_SYSTEM",
]


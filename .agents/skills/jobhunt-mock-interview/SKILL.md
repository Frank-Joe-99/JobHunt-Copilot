---
name: jobhunt-mock-interview
description: Run the repository's interactive, multi-stage mock interview using the candidate profile and a target role/company. Use when the user asks to practice, simulate, or debrief a job interview.
---

# JobHunt Mock Interview

1. Clarify the target role/company and interviewer style only when not provided. Use the user's actual experience and distinguish known facts from details still needing confirmation.
2. From the repository root start `uv run jobhunt interview`, optionally passing `--target-role`, `--company`, `--role` (`strict_architect`, `practical_lead`, or `hrbp`), and `--provider`. Pass `--jd <text-or-file>` when a JD is provided. Use `--mode practice` for explanations and hints, or keep the default `--mode simulation` for a mock interview. Existing invocations remain valid.
3. Keep the practice interactive: present one question at a time, let the user answer, and do not fabricate candidate answers. If the command is being run through a terminal, relay prompts and answers faithfully.
4. Record the returned session ID. Answers are saved before model generation; if the stream fails, use `/retry` to regenerate the unfinished question without resubmitting the answer. `/pause` saves the session without a debrief. EOF or Ctrl+C also pauses. Resume with `uv run jobhunt interview --resume-session <session_id>`; it uses the original profile snapshot, target and mode, so do not add new target/JD/style options. For a new background or job, start a new session. If the saved provider/model/endpoint configuration changes, pass `--provider` explicitly to acknowledge the change.
5. Finish through `/finish` and summarize strengths, weak spots, and practice tasks. If the debrief fails, resume the ended session to retry it. Label model-generated ideal answers as examples, not as the user's real experience.
6. Manage sessions offline with `uv run jobhunt interview-sessions list`, `uv run jobhunt interview-sessions show <session_id>` and `uv run jobhunt interview-sessions delete <session_id>`. Delete removes the session and request records; separately exported Markdown reports remain. Ask only when the intended session is unclear.
7. Private snapshots and request output are in ignored `storage/interviews.db`; reports are in `storage/interview_logs/`. Do not commit these files or reveal unrelated personal details.

## MCP compatibility

Keep the existing three interview tools. Resume with `tool_interview_start(resume_session_id=...)`. For a model-generating answer, pass a unique `request_id` and reuse the same ID and exact input on retries; alternatively use `/retry` for the saved unfinished request. A completed request replays its result without calling the model or changing stored history. Before answering a later question, read the current session again if an old result was replayed. `tool_interview_finish` uses `request_id="finish"` by default and replays the saved report after restarts. A different report ID explicitly requests a separate evaluation. `recoverable_error` responses retain `session_id`, `pending_request_id` and a safe error class so the host can recover. Do not treat a partial question as complete.

## Evidence grounding

Choose the technical domain from the target role and JD, independently of interviewer style. Use the candidate's actual profile and current answers; do not fill missing education or ownership with defaults. Tutorial reproduction is learning practice, not production experience. Never invent performance data or industrial experience. Missing or invalid profile configuration must be reported rather than replaced by a fabricated identity.

## Privacy

The interview sends profile and conversation content to the configured LLM provider. Do not run for an offline-only request, and never display API secrets.

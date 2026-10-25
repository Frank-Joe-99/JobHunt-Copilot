---
name: jobhunt-mock-interview
description: Run the repository's interactive, multi-stage mock interview using the candidate profile and a target role/company. Use when the user asks to practice, simulate, or debrief a job interview.
---

# JobHunt Mock Interview

1. Clarify the target role/company and interviewer style only when not provided. Use the user's actual experience and distinguish known facts from details still needing confirmation.
2. From the repository root start `uv run jobhunt interview`, optionally passing `--target-role`, `--company`, `--role` (`strict_architect`, `practical_lead`, or `hrbp`), and `--provider`. Pass `--jd <text-or-file>` when a JD is provided. Use `--mode practice` for explanations and hints, or keep the default `--mode simulation`. The default `--flow fixed` retains streamed questions and fixed stages; `--flow adaptive` opts into the controlled trial. It validates one action and complete question before display. Existing invocations remain valid.
3. Keep the practice interactive: present one question at a time, let the user answer, and do not fabricate candidate answers. If the command is being run through a terminal, relay prompts and answers faithfully.
4. Record the returned session ID. Answers are saved before model generation; if generation fails, use `/retry` without resubmitting the answer. `/pause` saves without a debrief; EOF or Ctrl+C also pauses. Resume with `uv run jobhunt interview --resume-session <session_id>`; it uses the original snapshot, target, mode, flow and policy. Do not add new target/JD/style/flow/budget options when resuming. For changed background or policy, start a new session. If the provider/model/endpoint configuration changes, pass `--provider` explicitly.
5. Finish through `/finish` and summarize strengths, weak spots, and practice tasks. If the debrief fails, resume the ended session to retry it. Label model-generated ideal answers as examples, not as the user's real experience.
6. Manage sessions offline with `uv run jobhunt interview-sessions list`, `uv run jobhunt interview-sessions show <session_id>` and `uv run jobhunt interview-sessions delete <session_id>`. Delete removes the session and request records; separately exported Markdown reports remain. Ask only when the intended session is unclear.
7. Private snapshots and request output are in ignored `storage/interviews.db`; reports are in `storage/interview_logs/`. Do not commit these files or reveal unrelated personal details.

## MCP compatibility

Keep the existing three interview tools. Resume with `tool_interview_start(resume_session_id=...)`. For a model-generating answer, pass a unique `request_id` and reuse the same ID and exact input on retries; alternatively use `/retry` for the saved unfinished request. A completed request replays its result without calling the model or changing stored history. Before answering a later question, read the current session again if an old result was replayed. `tool_interview_finish` uses `request_id="finish"` by default and replays the saved report after restarts. A different report ID explicitly requests a separate evaluation. `recoverable_error` responses retain `session_id`, `pending_request_id` and a safe error class so the host can recover. Do not treat a partial question as complete.

Start the adaptive trial with `flow="adaptive"`. Optional MCP policy fields are `max_turns`, `max_duration_seconds`, `max_followups`, `max_requests_per_turn`, `max_requests_total` and `request_timeout_seconds`. Answer results add flow, stop reason, policy notice and metrics. No extra tool is required.

## Adaptive limits and comparison

Adaptive defaults: 16 interaction turns including opening, 1800 active seconds excluding pauses, at most 2 consecutive followups, 1 HTTP request per turn, 32 across the interview, and 30 seconds per generated response. Debrief requests are separate. Useful CLI overrides are `--max-turns`, `--max-duration` (seconds), `--max-followups` (adaptive only), `--request-budget`, `--max-requests` and `--request-timeout`.

The model may clarify, follow up, advance, or answer a reverse question; hints/re-answer actions require practice mode. Limits are ceilings, not requirements to ask every followup. The program rejects invalid jumps and duplicate questions. Keep `/next`, `/pause`, `/retry` and `/finish` available. Do not silently switch an existing session's flow or provider after errors; start a new `--flow fixed` session for the original streamed experience.

`uv run jobhunt interview-sessions show <session_id>` includes metrics. Compare two saved sessions offline with `uv run jobhunt interview-sessions compare <fixed_id> --with-session <adaptive_id>`. Explicitly use the same turn/time/request limits for both flows so the fixed baseline also enforces shared budgets. Keep model settings unchanged. Compare output checks context, answers and declared shared policy, and reports known requests, failure/retry rates and service text-ready latency; it does not grade quality. Crash-era request counts have an explicit unknown upper bound. Do not treat synthetic timings or unknown old metrics as measured quality improvements.

## Evidence grounding

Choose the technical domain from the target role and JD, independently of interviewer style. Use the candidate's actual profile and current answers; do not fill missing education or ownership with defaults. Tutorial reproduction is learning practice, not production experience. Never invent performance data or industrial experience. Missing or invalid profile configuration must be reported rather than replaced by a fabricated identity.

## Privacy

The interview sends profile and conversation content to the configured LLM provider. Do not run for an offline-only request, and never display API secrets.

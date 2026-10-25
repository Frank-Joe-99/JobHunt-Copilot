---
name: jobhunt-mock-interview
description: Run the repository's interactive, multi-stage mock interview using the candidate profile and a target role/company. Use when the user asks to practice, simulate, or debrief a job interview.
---

# JobHunt Mock Interview

1. Clarify the target role/company and interviewer style only when not provided. Use the user's actual experience and distinguish known facts from details still needing confirmation.
2. From the repository root start `uv run jobhunt interview`, optionally passing `--target-role`, `--company`, `--role` (`strict_architect`, `practical_lead`, or `hrbp`), and `--provider`. Pass `--jd <text-or-file>` when a JD is provided. Use `--mode practice` for explanations and hints, or keep the default `--mode simulation` for a mock interview. Existing invocations remain valid.
3. Keep the practice interactive: present one question at a time, let the user answer, and do not fabricate candidate answers. If the command is being run through a terminal, relay prompts and answers faithfully.
4. Finish the interview through the application's normal flow and summarize strengths, weak spots, and specific practice tasks. Label model-generated ideal answers as examples, not as the user's real experience.
5. The app saves interview reports locally under its ignored storage output. Do not commit these files or reveal unrelated personal details.

## Evidence grounding

Choose the technical domain from the target role and JD, independently of interviewer style. Use the candidate's actual profile and current answers; do not fill missing education or ownership with defaults. Tutorial reproduction is learning practice, not production experience. Never invent performance data or industrial experience. Missing or invalid profile configuration must be reported rather than replaced by a fabricated identity.

## Privacy

The interview sends profile and conversation content to the configured LLM provider. Do not run for an offline-only request, and never display API secrets.

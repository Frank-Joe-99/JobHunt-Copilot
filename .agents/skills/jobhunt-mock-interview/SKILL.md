---
name: jobhunt-mock-interview
description: Run the repository's interactive, multi-stage mock interview using the candidate profile and a target role/company. Use when the user asks to practice, simulate, or debrief a job interview.
---

# JobHunt Mock Interview

1. Clarify the target role/company and interviewer style only when not provided. Use the user's actual experience and distinguish known facts from details still needing confirmation.
2. From the repository root start `uv run jobhunt interview`, optionally passing `--target-role`, `--company`, `--role` (`strict_architect`, `practical_lead`, or `hrbp`), and a provider if requested.
3. Keep the practice interactive: present one question at a time, let the user answer, and do not fabricate candidate answers. If the command is being run through a terminal, relay prompts and answers faithfully.
4. Finish the interview through the application's normal flow and summarize strengths, weak spots, and specific practice tasks. Label model-generated ideal answers as examples, not as the user's real experience.
5. The app saves interview reports locally under its ignored storage output. Do not commit these files or reveal unrelated personal details.

## Profile-specific grounding

For this candidate, favor AI infrastructure, HPC, GPU/CUDA, scientific computing, and semiconductor simulation when relevant. Keep evidence boundaries: tutorial Triton kernels are learning practice; they are not production integration or end-to-end inference optimization. Never invent performance data or industrial experience.

## Privacy

The interview sends profile and conversation content to the configured LLM provider. Do not run for an offline-only request, and never display API secrets.

---
name: jobhunt-job-radar
description: Batch-rank multiple local job descriptions against the JobHunt-Copilot profile and summarize common requirements and gaps. Use when the user asks to scan a folder of JDs, compare several roles, or prioritize applications in bulk.
---

# JobHunt Job Radar

1. Ask for or identify the exact folder containing `.txt` job descriptions. Never scan the entire workspace or unrelated folders.
2. Confirm the folder contains only JDs the user intends to analyze; do not move or rewrite source files.
3. From the repository root run `uv run jobhunt radar --dir <JD-folder>`. Use the configured provider only when the user wants the AI analysis.
4. Summarize the ranking, shared skill gaps, and suggested priorities. Keep the report's distinctions between strong match, stretch, and lower priority; don't imply an application was submitted.
5. Report where the generated local report was saved. Do not commit generated radar reports or private source JD files.

## Privacy and side effects

JD/profile-derived content is sent to the configured LLM provider. Do not run if the user requested offline-only analysis. The radar writes a local report but should not update the application tracker unless separately requested.

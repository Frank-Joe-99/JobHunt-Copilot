---
name: jobhunt-resume-build
description: Generate the user's local baseline resume from JobHunt-Copilot's configured profile. Use when the user asks to compile, export, or regenerate a Word/PDF resume without first tailoring it to a particular job.
---

# JobHunt Resume Build

1. Confirm the repository root and local profile/config are available. The resume is built from `config/profile.yaml`; do not inspect or quote private contact fields unless necessary to resolve a user-raised issue.
2. From the repository root run `uv run jobhunt resume --template modern`, adding `--output-name` only if the user asks for a specific filename.
3. Report the generated PDF and Word paths. The configured resume output folder is local and ignored by Git; do not stage or commit generated resumes.
4. If the user asks for a role-specific resume, use `jobhunt-application-package` instead. Do not alter the source profile as part of compiling.

This local compilation does not need an LLM call. Treat resume files as sensitive; do not paste their full contents into chat unless the user requests a content review.

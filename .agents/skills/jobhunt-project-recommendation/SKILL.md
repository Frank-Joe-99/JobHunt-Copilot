---
name: jobhunt-project-recommendation
description: Recommend GitHub learning projects and a skill-gap study path using JobHunt-Copilot's existing project recommender. Use when the user asks what to learn/build next, how to close a JD gap, or for relevant repositories to practice on.
---

# JobHunt Project Recommendation

1. Identify skill gaps from the supplied JD or a prior JD-match result. Ask for a target role or preferred language only if needed; otherwise make assumptions explicit.
2. Call `skills.project_recommender.handler.recommend_projects_report` with `core.state.SkillGap` items and the preferred language.
3. Summarize why each repository fits, the exact learning path, likely interview follow-ups, and how the work could become candidate evidence only after the user actually completes it.
4. Label generated resume wording as a planning template with placeholders, never as a completed accomplishment. Do not claim the candidate implemented a repository, feature, or metric based on a recommendation.

## Privacy and external calls

The recommender searches GitHub and sends skill-gap/repository-derived content to the configured LLM provider. Do not expose profile contact details or API keys. Do not run for an offline-only request.

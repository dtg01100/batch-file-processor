# create-instructions Skill

This is a workspace-scoped helper skill for Batch File Processor to capture the process for turning conversational requirements into a permanent agent instruction file.

## Purpose

- Convert ad-hoc user requirements into an actionable `.instructions.md` or `.SKILL.md` artifact.
- Enforce the project’s agent customization conventions while keeping instructions current.
- Make it easy for any contributor to add or update instruction guidance based on conversation context.

## When to use

- The user asks: “create an instructions file” or “add a rule for agent behavior”.
- A review request includes a reusable policy or pattern that should be persisted.
- The team wants a single source of truth for a recurring guidance pattern.

## Input (prompt for this skill)

- Conversation context and rules extracted from chat history.
- Target scope (global project, module-specific, UI, dispatch, etc.).
- Priority directive: hard rule vs preference, and whether to apply everywhere or just tracked files.
- Output file path (e.g., `docs/skills/<name>.SKILL.md`, `.github/copilot-instructions.md`).

## Workflow

1. Extract explicit requirements from conversation
   - Corrections and preferences (must/never statements, naming rules, style rules).
   - Project-specific conventions from `AGENTS.md`, `README.md`, `.github/copilot-instructions.md`.
   - Existing constraints already in the workspace (e.g., required response for name/model + formatting rules).
2. Clarify ambiguities with user questions when needed:
   - Scope: all files, codebase sections, or just the current task.
   - File types: Python scripts, markdown, YAML, extensions.
   - Is this a strict enforcement or just a preferred style.
3. Create instruction content with a standard structure:
   - Purpose, When to use, Input, Workflow, Output, Example prompts, Related customizations.
   - Include explicit, unambiguous bullet points.
4. Save to disk:
   - Preferred path: `docs/skills/<descriptive-name>.SKILL.md`.
   - If a global or stable policy, also ensure `.github/copilot-instructions.md` is updated.
5. Add a short summary and example prompts in final response.
6. Keep it up to date:
   - Re-run this skill when new conventions emerge.
   - Update the skill to include new user preferences (e.g., “respond with GitHub Copilot”, “model is Raptor mini (Preview)”).

## Output

- New or updated instructions file(s) capturing the policy.
- Short list of follow-up clarifications for ambiguous behavior if needed.

## Example prompts

- "Use create-instructions to save a rule: 'Always use .venv Python and do not use system Python' in docs/skills." 
- "Use create-instructions to add a rule that 'auto-refactor only after targeted tests pass'."

## Related customizations

- `/create-skill agent-customization` (top-level project conventions and rename rules)
- `/create-instruction dispatch-test-strategy.md` (domain-specific testing pattern)

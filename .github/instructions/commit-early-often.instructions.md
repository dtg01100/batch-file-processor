---
description: 'Encourage the agent to commit code early and often during development so work can be rolled back and reviewed incrementally.'
applyTo: '**'
---

# Commit Early and Often

This instruction tells the agent to save progress frequently during code changes, especially when implementing features, refactoring, or fixing bugs.

## Behavior

- Create or update files in small, logical increments.
- Prefer multiple safe commits over one large change when a task has distinct steps.
- Use descriptive commit messages that summarize the change and the reason.
- When a task is interrupted, leave the workspace in a recoverable state.
- Avoid large, monolithic edits unless they are truly atomic and unavoidable.

## When to apply

- Adding new functionality
- Fixing bugs or edge cases
- Refactoring code
- Updating tests or documentation
- Changing project configuration

## Why this matters

Frequent commits make it easier to rollback unintended changes, review progress in stages, and maintain a clear development history.

## Example prompts

- "Commit the current fix now so I can review the first checkpoint." 
- "Split this refactor into smaller commits and save the first working version." 
- "Update the test and commit as soon as the regression is covered."

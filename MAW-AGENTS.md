# Multi-Agent Worktree Notes

This repository uses Git worktrees so every agent (human or automated) works in
its own directory and branch. The assignments are defined in
`.agents/agents.yaml`. Each entry creates:

- a branch named `agents/<agent-name>`
- a working directory under `agents/<agent-name>/`

Use `git worktree list` to inspect the current setup. Do **not** switch an agent
worktree back to `main`; only the repository root should operate on the `main`
branch.

Coordinate through normal GitHub pull requests: merge work from
`agents/<agent-name>` into `main` only after explicit review/approval.

## 🔴 Critical Safety Rules

### Repository Usage
-   **NEVER create issues/PRs on upstream**

### Command Usage
-   **NEVER use `-f` or `--force` flags with any commands.**
-   Always use safe, non-destructive command options.
-   If a command requires confirmation, handle it appropriately without forcing.

### Git Operations
-   Never use `git push --force` or `git push -f`.
-   Never use `git checkout -f`.
-   Never use `git clean -f`.
-   Always use safe git operations that preserve history.
-   **⚠️ NEVER MERGE PULL REQUESTS WITHOUT EXPLICIT USER PERMISSION**
-   **Never use `gh pr merge` unless explicitly instructed by the user**
-   **Always wait for user review and approval before any merge**
-   Before you go through the commit -> push -> PR flow, run `gh auth status` to confirm the GitHub CLI is connected; use `gh auth login` if it is not.

### File Operations
-   Never use `rm -rf` - use `rm -i` for interactive confirmation.
-   Always confirm before deleting files.
-   Use safe file operations that can be reversed.

### Package Manager Operations
-   Never use `[package-manager] install --force`.
-   Never use `[package-manager] update` without specifying packages.
-   Always review lockfile changes before committing.

### General Safety Guidelines
-   Prioritize safety and reversibility in all operations.
-   Ask for confirmation when performing potentially destructive actions.
-   Explain the implications of commands before executing them.
-   Use verbose options to show what commands are doing.

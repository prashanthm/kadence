# Loop agent backend

Shared agent options for [PR comment fix loop](../skills/pr-comment-fix-loop/README.md),
[PR review loop](../skills/pr-review-loop/README.md), and
[engineering work loop](../skills/engineering-work-loop/README.md).

**Claude Code is the only backend.** The loops run every firing through Claude Code
(`claude`); there is no cross-tool fallback.

## Config

```yaml
agent_backend: claude   # the only supported value
# agent_cmd: claude     # optional binary override (default: claude)
agent_model: ""         # optional; AI Attribution Author model column (alias like "opus"/"sonnet")
```

| `agent_backend` | Default binary | Tool name (attribution) |
|---------------|----------------|-------------------------|
| `claude` | `claude` | Claude Code |

An unknown or empty `agent_backend` normalizes to `claude`. The runtime fallback chain
has a single entry (`claude`), so a failing firing reports `error` with the exit summary
rather than falling through to another tool.

## Claude Code CLI

```bash
# Install per https://docs.anthropic.com/en/docs/claude-code/setup
claude auth login    # interactive: uses your stored Claude Code session
claude setup-token   # once, for headless/launchd: prints a long-lived OAuth token
```

Auth resolution order at install/run time: `CLAUDE_CODE_OAUTH_TOKEN` (from `setup-token`)
→ `ANTHROPIC_API_KEY` → stored Claude Code login (`~/.claude` / `~/.claude.json`).
Non-interactive loops pass `--permission-mode bypassPermissions` automatically (via
`invoke_loop_agent.sh`) so file edits, git, and `gh` run without prompts. Claude Code
uses the working directory as its workspace.

Smoke test:

```bash
claude -p "Reply: claude-ok" --permission-mode bypassPermissions --add-dir .
```

## Scheduled runs (launchd)

Install with a loop setup script (see the loop READMEs), e.g.:

```bash
scripts/pr-comment-fix-loop-setup.sh install
```

launchd runs in your user session with `HOME` set, so a stored `claude auth login`
works headless. For a box without an interactive login, set `CLAUDE_CODE_OAUTH_TOKEN`
(from `claude setup-token`) or `ANTHROPIC_API_KEY`. The setup script bakes whichever
is present at install time into the plist; otherwise set it in the launchd env manually.
All installs need `PATH` including `~/.local/bin` and a `gh auth login`.

## Invocation

Loops call [`invoke_loop_agent.sh`](../scripts/invoke_loop_agent.sh):

| Backend | Flags |
|---------|-------|
| claude | `cd <path>; claude -p "<prompt>" --permission-mode bypassPermissions --add-dir <path> [--model <alias>]` |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `agent binary not found` | Install Claude Code CLI; set `agent_cmd` override if not named `claude` |
| Claude `Invalid API key` / auth fails under launchd | Set `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) or `ANTHROPIC_API_KEY` in the plist env |
| Cron auth fails while manual works | Ensure the Mac is awake and logged in; or set a headless token/key |

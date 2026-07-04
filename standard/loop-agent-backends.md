# Loop agent backends

Shared fix-agent options for [PR comment fix loop](../skills/pr-comment-fix-loop/README.md) and [engineering work loop](../skills/engineering-work-loop/README.md).

## Config

```yaml
agent_backend: cursor   # cursor | copilot | claude
# agent_cmd: agent      # optional binary override (default: agent | copilot | claude)
agent_model: ""         # optional; AI Attribution Author model column (claude: alias like "opus"/"sonnet")
```

| `agent_backend` | Default binary | Tool name (attribution) |
|---------------|----------------|-------------------------|
| `cursor` | `agent` | Cursor |
| `copilot` | `copilot` | GitHub Copilot |
| `claude` | `claude` | Claude Code |

## Runtime fallback chain

Each firing tries backends in order **cursor → copilot → claude**, falling through
on failure (rate limit, auth, transient API error, any non-zero exit). The first
backend that exits 0 wins; if all fail, the firing reports `error` with a summary
of what was tried. The backend that actually ran is recorded as `agent_backend`
in the firing report / AI Attribution.

- The chain runs on every firing regardless of the configured `agent_backend`.
- A configured `agent_cmd` override applies only to its matching backend; fallback
  backends always use their default binary.
- Each backend must still be installed/authenticated to succeed when reached — an
  uninstalled or unauthenticated backend simply fails and the chain moves on.

## Cursor CLI

```bash
curl https://cursor.com/install -fsS | bash
agent login
agent status    # verify login before setup
```

Smoke test:

```bash
agent -p --trust --mode ask "Reply: cursor-ok"
```

Optional: `CURSOR_API_KEY` env var or `--api-key` for headless automation without a local login session.

## GitHub Copilot CLI

```bash
# Install per https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli
copilot login
```

Non-interactive loops set `COPILOT_ALLOW_ALL=1` automatically (setup script / `invoke_loop_agent.sh`).

Smoke test:

```bash
copilot -p "Reply: copilot-ok" --allow-all-tools --add-dir .
```

## Claude Code CLI

```bash
# Install per https://docs.anthropic.com/en/docs/claude-code/setup
claude setup-token   # once: prints a long-lived OAuth token for headless/launchd use
```

Set `CLAUDE_CODE_OAUTH_TOKEN` (from `setup-token`) or `ANTHROPIC_API_KEY` in the
environment. Non-interactive loops pass `--permission-mode bypassPermissions`
automatically (via `invoke_loop_agent.sh`) so file edits, git, and `gh` run
without prompts. Claude Code uses the working directory as its workspace.

Smoke test:

```bash
claude -p "Reply: claude-ok" --permission-mode bypassPermissions --add-dir .
```

## Scheduled runs (launchd)

Install with the PR fix loop setup script (see [README](../skills/pr-comment-fix-loop/README.md)):

```bash
scripts/pr-comment-fix-loop-setup.sh install
```

Uses the **local CLI login** on your Mac (`agent login` or `copilot login`). No API key required for typical use. launchd runs in your user session with `HOME` set so credentials in `~/.local` / `~/.copilot` are available.

| Backend | Typical auth |
|---------|----------------|
| Cursor | `agent login` (verified by `agent status` on install) |
| Copilot | `copilot login` + `COPILOT_ALLOW_ALL=1` in launchd |
| Claude | `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY` in launchd env |

All need `PATH` including `~/.local/bin` and `gh auth login`. The setup script bakes
`CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY` into the plist when present at install
time; otherwise set it in the launchd env manually.

## Invocation

Loops call [`invoke_loop_agent.sh`](../scripts/invoke_loop_agent.sh):

| Backend | Flags |
|---------|-------|
| cursor | `agent -p --trust --force --workspace <path> "<prompt>"` |
| copilot | `copilot -p "<prompt>" --allow-all-tools --add-dir <path>` |
| claude | `cd <path>; claude -p "<prompt>" --permission-mode bypassPermissions --add-dir <path> [--model <alias>]` |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `agent binary not found` | Install CLI; set `agent_cmd` override |
| Copilot prompts for permission | `COPILOT_ALLOW_ALL=1` (auto-set by setup) |
| Cursor `Authentication required` | `agent login` |
| Claude `Invalid API key` / auth fails under launchd | Set `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) or `ANTHROPIC_API_KEY` in the plist env |
| Cron auth fails while manual works | Ensure Mac awake and logged in; optional `CURSOR_API_KEY` for headless |
| Wrong tool in attribution | Set `agent_backend` in operator overlay |

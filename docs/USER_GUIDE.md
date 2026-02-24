# User Guide

## Workspace modes
- `Command`: ask and configure query/runtime.
- `Evidence`: validate source snippets and claims.
- `Trace`: inspect recursive reasoning trajectory.
- `Ops`: compare, watch, security triage, evals.

## Asking good questions
- Include scope: module/service/path.
- Ask for explicit citation requirements.
- Request output format (bullets/table/deltas).

## Provider and key workflow
- Choose provider + model in the command panel before running.
- Preferred production mode: configure provider key as backend env var.
- Hosted demo mode: enter `Session API key` in the workspace.
- Session key behavior: in-memory only in the browser and sent only on run requests.

## Shortcuts and commands
- Keyboard: `Cmd/Ctrl+Enter` runs query, `Shift+Cmd/Ctrl+Enter` runs fast profile, `?` opens shortcuts, `Esc` closes modals.
- Slash commands: `/compare`, `/watch`, `/evaluate` route directly to Ops workflows.

## Evidence workflow
1. Open citation chip.
2. Use context expansion (`+/- lines`).
3. Move across citations (`previous/next`).
4. Copy snippet or markdown citation block.

## Trace workflow
1. Start with graph view for structure.
2. Switch to timeline for event detail.
3. Filter errors/subcalls.
4. Use jump shortcuts for hotspots.

## Ops Lab workflows
### Compare
- Select baseline and candidate run.
- Review overlap and citation counts.
- Save compare session for later.

### Watch
- Start corpus watcher.
- Monitor status and watcher count.

### Security
- Refresh policy findings.
- Triage findings (`new`, `accepted`, `resolved`).

### Evals
- Pick a preset (`smoke`, `regression`, `deep`).
- Run benchmark queries.
- Track status and trend.

## Export/share
- Export bundles from selected run.
- Use share preview for run metadata summary.

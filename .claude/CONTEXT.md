# .claude/: CONTEXT

Claude Code project settings shared through git.

| File | Contains / does |
|---|---|
| `settings.json` | Project settings. `env.CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-5` pins every subagent to Sonnet 5 (exact ID, so the `sonnet` alias cannot move to a later version). `env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` ignores any other model a call asks for. Takes effect from the next session. |

Not tracked (gitignored, not part of the project): `claudex/` (plugin state), `settings.local.json` (personal overrides).

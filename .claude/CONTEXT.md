# .claude/: CONTEXT

Claude Code project settings shared through git.

| File | Contains / does |
|---|---|
| `settings.json` | Project settings. `env.CLAUDE_CODE_SUBAGENT_MODEL=sonnet` sets the model for every subagent. `env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` ignores any other model a call asks for. Takes effect from the next session. |

Not tracked (gitignored, not part of the project): `claudex/` (plugin state), `settings.local.json` (personal overrides).

# AIOS Provider Prompts

ASC-0087 makes provider CLIs AIOS-aware through marker-delimited prompt blocks.
The bootstrapper is user-space only and safe-merge only: it creates or replaces
the `<!-- AIOS BEGIN ... -->` block and preserves user content outside it.

Commands:

```bash
python scripts/aios_provider_prompts.py detect --json
python scripts/aios_provider_prompts.py bootstrap --dry-run --json
python scripts/aios_provider_prompts.py bootstrap --json
python scripts/aios_provider_prompts.py status --json
python scripts/aios_provider_prompts.py refresh --json
```

Safety model:

- No sudo or system path writes.
- No provider credentials are read or written.
- Existing files without an AIOS marker are appended, not overwritten.
- Existing AIOS marker blocks are replaced in place.
- Gemini, Cursor, and Aider are experimental in V1 and are not written by
  default even when detected.
- Tests use `--home` with a temporary directory; live bootstrap should be an
  explicit operator action.

Default V1 targets:

| Provider | Target | Default write |
| --- | --- | --- |
| Claude Code | `~/.claude/CLAUDE.md` | yes |
| Codex CLI | `~/.codex/AGENTS.md` | yes if detected |
| Gemini | `~/.gemini/AIOS.md` | no, experimental |
| Cursor | `.cursorrules` | no, experimental |
| Aider | `CONVENTIONS.md` | no, experimental |

The shared template lives at
`scripts/templates/provider_prompts/_shared_invariants.md.tmpl` and is included
by every provider-specific template. Update the shared template first when
AIOS operating rules change.

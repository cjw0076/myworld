# Discovery - Codex Vercel Next.js Skill Path Gap

- date: 2026-05-13 KST
- source repo: `myworld/uri`
- reporter: codex@uri
- severity: medium

## Observation

During Uri Sprint 058, the session listed Vercel/Next.js skills, but the local
path `/home/user/.codex/plugins/cache/openai-curated/vercel/1141b764/skills`
was missing. Codex could not load the advertised `vercel:nextjs` skill and
instead used official Next.js documentation plus local verification.

## Why It Matters

AIOS capability routing should not present an unavailable skill as callable.
When a skill path is stale or absent, agents lose time probing the capability
surface and may silently degrade to ad hoc web search.

## Proposed AIOS Improvement

- Add a preflight capability health check that validates advertised skill paths
  before dispatch.
- Mark unavailable capabilities as degraded with a recommended fallback.
- Record missing plugin cache paths in a central CapabilityOS repair queue.

## Evidence

- `rg --files ... /home/user/.codex/plugins/cache/openai-curated/vercel/1141b764/skills`
  returned: `No such file or directory`.
- Uri Sprint 058 completed by falling back to:
  `https://nextjs.org/docs/app/api-reference/functions/generate-metadata`.

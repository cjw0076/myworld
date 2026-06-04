# AIOS Provider Web Design References

status: active_reference
owner: codex-ui
updated: 2026-05-17

This reference board translates current large-provider AI web patterns into
AIOS Control Center design rules. It is not a screenshot archive; it is a
source-backed pattern map for implementation.

## Reference Sources

- ChatGPT / OpenAI: file Library lives in the left sidebar, saved files can be
  searched and filtered, and the launcher Chat Bar supports quick ask, files,
  screenshots, photos, and voice.
  - https://help.openai.com/articles/20001052
  - https://help.openai.com/en/articles/9295241-accessing-the-launcher-chatgpt-macos-app%23.svg
- Claude / Anthropic: Artifacts appear in a dedicated right-side window beside
  the main chat, and the artifacts space is accessible from the app sidebar.
  - https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them
  - https://support.anthropic.com/en/articles/9547008-discovering-publishing-customizing-and-sharing-artifacts
- Gemini / Google: the web app is a direct chat surface with a bottom text box,
  optional file/image attachment, model selection, and an explicit warning to
  double-check responses.
  - https://support.google.com/android/answer/13275745
  - https://support.google.com/gemini/answer/14886647
- Perplexity: product value centers on web-grounded answers, source choice, and
  cited retrieval infrastructure. Enterprise search explicitly separates Web,
  Org Files, Web + Org Files, and None.
  - https://www.perplexity.ai/help-center/en/articles/10354842-what-is-the-api
  - https://www.perplexity.ai/help-center/en/articles/10352958-what-is-internal-knowledge-search-for-enterprise-pro-users/

## Patterns To Borrow

### 1. Chat Is The Primary Surface

Provider pattern:
- ChatGPT/Gemini make the prompt box the obvious first action.
- ChatGPT's launcher compresses "ask, attach, screenshot, voice" into one bar.

AIOS adaptation:
- Keep `Talk to AIOS` first.
- Keep the default state conversational, not dashboard-first.
- Add attachments later as governed artifacts, not raw file access.
- Expose "turn this into a goal" as a first-class mode beside normal chat.

### 2. Artifacts Need Their Own Pane

Provider pattern:
- Claude splits chat and artifact work into main conversation plus a dedicated
  artifact panel.
- Artifacts are reusable, shareable, and separately browsable from the sidebar.

AIOS adaptation:
- Evidence, screenshots, contracts, context packs, and route receipts should not
  be buried inside messages.
- The Control Center needs a persistent artifact/evidence rail with preview,
  authority, owner, and verification status.
- Chat responses should link to artifact cards rather than dumping raw paths.

### 3. Library / Memory Is A Browsable Product Surface

Provider pattern:
- ChatGPT Library makes uploaded/generated files discoverable from the sidebar,
  searchable, and filterable by type.

AIOS adaptation:
- MemoryOS should become a user-visible "Memory Library", not just JSONL.
- Required filters: accepted, draft, rejected, source, project, failure memory,
  founder preference, provider behavior.
- Memory cards must show provenance and last review state.

### 4. Source Choice Must Be Explicit

Provider pattern:
- Perplexity Enterprise separates Web, Org Files, Web + Org Files, and None.
- Perplexity's core promise is grounded answers with source control.

AIOS adaptation:
- CapabilityOS should expose source mode before execution:
  - Local repo
  - MemoryOS
  - Web
  - Provider docs
  - MCP/skill/plugin
  - None / no external retrieval
- The user should see which route was used and why.

### 5. Model / Runtime Choice Is Visible But Not Dominant

Provider pattern:
- Gemini surfaces model choice but keeps the conversation primary.
- ChatGPT/Claude expose specialized spaces without forcing users to think about
  every internal runtime detail.

AIOS adaptation:
- Show the current Gate Chair/provider as a small runtime chip.
- Put provider failover details in an expandable evidence panel.
- Do not make end users choose providers unless the route has a real tradeoff.

### 6. Warnings Should Be Calm And Close To The Action

Provider pattern:
- Gemini includes an explicit response-quality warning.
- Perplexity emphasizes source-grounded trust instead of blind confidence.

AIOS adaptation:
- Keep `Readiness Audit` honest: never say complete while monitor health is
  attention or child repos are dirty.
- Put stop conditions and missing provenance near the related action.
- Use "hold / review / degraded" states instead of dramatic error pages.

## AIOS-Specific Design Direction

The target interface should combine:

- ChatGPT-style immediate prompt surface.
- Claude-style artifact/evidence pane.
- Perplexity-style source route visibility.
- Gemini-style lightweight model/runtime awareness.
- AIOS-only readiness audit, OS Observatory, contract governance, and memory
  provenance.

## Next UI Contracts

- Add an artifact/evidence rail to `chat.html` and/or the main Control Center.
- Promote MemoryOS into a browsable Memory Library view.
- Promote CapabilityOS into a visible source/router selector.
- Convert OS Observatory weak signal bars into clickable evidence/action
  cards.


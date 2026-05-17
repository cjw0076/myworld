# AIOS User Patterns

ASC-0113 adds draft user-pattern extraction and few-shot injection.

## Extract

```bash
python scripts/aios_pattern_extractor.py --write .aios/patterns/founder/patterns.json --json
```

The extractor reads only AIOS-local durable evidence:

- founder directive records from contracts/operator sessions;
- AIOS chat history under `.aios/chat/`;
- AIOS self-observation notes.

It emits `aios.user_pattern.v1` with draft patterns and provenance refs. Pattern
memory drafts use `type=user_pattern`, `origin=pattern_extracted`, and
`status=draft`.

## Inject

```bash
python scripts/aios_few_shot_injector.py --substrate-prompt "test prompt" --user founder --json
```

The injector adds up to three draft, provenance-bound behavior hints before the
substrate prompt. It records each injection in
`.aios/patterns/<user>/injections.jsonl`.

## Guardrails

- Patterns are draft hints, not authority.
- Patterns must not override AIOS DNA, privacy rules, operator override, or
  verification gates.
- Private paths, credentials, tokens, and pins are redacted/excluded before
  injection.
- `aios_chat_router.py` records `patterns_injected` on every assistant turn so
  behavior shaping is visible.

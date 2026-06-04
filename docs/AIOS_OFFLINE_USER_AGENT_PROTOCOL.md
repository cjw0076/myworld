# AIOS Offline User Agent Protocol

AIOS must not be limited to the user's current knowledge, the active agent's
context, or a model's training distribution. It needs a governed way to reach
outside all three without pretending it already knows the answer.

This protocol treats the human operator as an offline agent:

```text
user@offline
  = embodied sensor, taste judge, field tester, private-context holder,
    real-world executor, and final authority
```

The user is not just a prompt source. The user can observe reality AIOS cannot
see, run offline experiments, judge whether an output feels wrong, provide
private context without exposing raw data, and decide which unknowns are worth
paying attention to.

## Core Loop

```text
known boundary
  -> unknown frontier question
  -> GenesisOS mutation/challenge
  -> CapabilityOS route plan
  -> web / local / offline-user observation task
  -> MemoryOS draft with provenance
  -> Hive verification or experiment
  -> operator decision
  -> ledger next
```

AIOS should use this loop whenever a task is likely constrained by:

- the user's current knowledge;
- the agent's current context window;
- stale or incomplete model training;
- missing external evidence;
- private facts that cannot be sent to providers;
- taste, embodiment, social context, or field reality.

## Packet Types

### `unknown.frontier.question`

Names the boundary of current knowledge.

Required fields:

- `question`
- `why_known_context_is_insufficient`
- `risk_if_we_guess`
- `candidate_routes`
- `stop_condition`

### `user.offline_task`

Asks `user@offline` for one bounded observation or decision.

Required fields:

- `task`
- `time_budget`
- `what_to_observe`
- `what_not_to_share`
- `return_format`
- `privacy_boundary`

Allowed examples:

- "Look at the actual app screen and say where your eye hesitates first."
- "Ask one real target user which wording makes sense."
- "Check whether this workflow is still emotionally worth doing."
- "Confirm whether this private document contains the needed fact, but do not
  paste the document."

### `field_observation`

Records a user-provided offline observation as draft evidence.

Required fields:

- `observed_by: user@offline`
- `observed_at`
- `summary`
- `confidence`
- `private_data_included: false`
- `next_question`

### `contradiction`

Records a mismatch between AIOS's internal model and external reality.

Required fields:

- `expected`
- `observed`
- `impact`
- `owner_repo`
- `next_contract_candidate`

## Non-Cheating Rules

1. AIOS must say what it does not know before using outside evidence.
2. Offline user observations enter MemoryOS as drafts, not accepted memory.
3. The user should never be asked to paste secrets, raw private exports, or
   provider credentials into shared artifacts.
4. A web result, LLM claim, or internal contract is not enough when the missing
   variable is taste, field behavior, or private context.
5. A future contract must be able to replay the reasoning path without chat
   context.

## Builder Binding

The executable primitive is:

```bash
python scripts/aios_offline_user_agent.py
```

It validates and creates `aios.offline_user_agent_packet.v1` packets. Use it
before asking the user to supply external reality.

Required behavior:

1. If the gap is model/context/training uncertainty, create an
   `unknown.frontier.question`.
2. If the missing evidence requires the embodied user, create one
   `user.offline_task` with a time budget and explicit private-data boundary.
3. If the user returns an observation, record it as `field_observation` with
   `private_data_included: false`.
4. If the observation contradicts AIOS's internal model, record
   `contradiction` and route it to a follow-up contract candidate.

The helper writes valid packets to `.aios/inbox/memoryOS/` by default so the
observation enters the draft-first MemoryOS review lane. It rejects sensitive
terms such as `.env`, tokens, passwords, credentials, raw exports, cookies,
and private history when they appear outside explicit boundary fields.

When creating a `field_observation`, the helper also writes a synthetic
`aios.chat.memory_drafts.v1` file at
`.aios/chat/offline-user/memory_drafts.json` unless `--no-memory-draft` is
set. This reuses the existing Memory Draft Queue: the observation becomes
visible, reviewable, and still unaccepted until MemoryOS reviews it.

Example:

```bash
python scripts/aios_offline_user_agent.py new-offline-task \
  --task "Open the Uri campus screen and note where your eye stops first." \
  --time-budget "3 minutes" \
  --observe "First hesitation point, confusing label, and one desired tap." \
  --not-share "Do not paste credentials, messages, raw screenshots, or files." \
  --return-format "Three bullets: hesitation / desired action / one fix." \
  --privacy-boundary "Private data and raw screenshots stay offline."
```

Field observation example:

```bash
python scripts/aios_offline_user_agent.py new-field-observation \
  --summary "The target user understood the card but hesitated on the privacy boundary." \
  --confidence 0.72 \
  --next-question "Should the privacy boundary move closer to the action button?"
```

This turns "ask the user" into a governed AIOS route, not an unstructured chat
fallback.

## Organism Role

This protocol adds a sixth practical surface without creating a sixth OS:

```text
user@offline
  -> outside-world sense organ and sovereign field executor
```

It keeps the 5-OS architecture intact. `myworld` still owns contracts and
operator checkpoints. The offline user agent supplies observations and
decisions that no model or web search can safely fabricate.

## Production Implication

AIOS is production-ready only when the product can show:

- what it knows;
- what it does not know;
- what it wants the offline user to observe;
- what it will do with that observation;
- how the observation becomes draft memory or a new contract;
- how the user can reject the system's interpretation.

This is the missing bridge from an autonomous-looking tool to a trustworthy
human-agent organism.

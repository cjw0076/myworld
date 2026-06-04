# AIOS Alignment Provider Survey

created: 2026-05-20 KST  
owner: codex@myworld  
purpose: map provider alignment papers, systems, and methods into attachable
AIOS components.

## Bottom Line

AIOS should not start with neural RLHF. It should first build a
system-alignment loop:

```text
AIOS Behavior Spec
  -> approved demos / rejected examples
  -> preference pairs from user@offline and reviewers
  -> reward ledger
  -> eval and red-team gates
  -> route / contract / prompt / stop-rule updates
  -> optional DPO/RLHF fine-tune later
```

The alignment target is the whole AIOS policy:

```text
goal -> plan -> dispatch -> execution -> evidence -> memory -> next action
```

## Provider / Method Map

| Source | Primary Method | What AIOS Should Borrow | Attach Now |
| --- | --- | --- | --- |
| OpenAI InstructGPT | SFT -> reward model -> PPO/RLHF | human demos and preference rankings for instruction following | Preference Ledger, not PPO yet |
| OpenAI summarization RLHF | comparison data -> reward model -> RL | subjective result quality beats proxy metrics alone | result/receipt quality scoring |
| OpenAI Model Spec / Evals | behavior spec + scenario evals | explicit intended behavior and tests | `AIOS_BEHAVIOR_SPEC` |
| OpenAI Deliberative Alignment | reasoning over safety specs | apply rules before acting | contract preflight |
| OpenAI Weak-to-Strong | weak supervisor guides stronger model | user can define direction even when agent knows details | `user@offline` preference loop |
| Anthropic HH-RLHF | helpful/harmless preference data | split usefulness and safety rewards | reward rubric axes |
| Anthropic Constitutional AI | principles + AI critique/revision | reduce label burden with explicit principles | GenesisOS + AIOS DNA critique |
| Anthropic red teaming | adversarial harm discovery | active attack generation | Hive/Genesis red-team packets |
| Anthropic RSP / alignment faking / MSM | risk gates and spec generalization | train-vs-deploy mismatch checks | autonomy risk gates |
| DeepMind Sparrow | preference reward + rule model | separate reward from rule violations | reward + constraint ledgers |
| Google RLAIF | AI feedback at scale | scale labels after human calibration | later |
| DeepMind Frontier Safety Framework | capability thresholds | autonomy levels and deployment gates | yes |
| Meta Llama 2 | open SFT/RLHF/safety methodology | safety training/eval disclosure | reference |
| Meta self-rewarding LMs | LLM-as-judge self-reward | self-improvement with external checks | later |
| Hugging Face TRL | SFT, reward, PPO, DPO, ORPO, KTO, GRPO | practical local post-training | later backend |
| HF Alignment Handbook | reproducible SFT/DPO/ORPO recipes | open alignment cookbook | later backend |
| OpenRLHF | scalable PPO/GRPO/DPO/Ray/vLLM | heavy RLHF/RLVR execution | later |
| NVIDIA NeMo-Aligner | enterprise DPO/RLHF/SteerLM | scalable training infra | later |
| OpenAI Evals / HarmBench / Chatbot Arena | system eval, red-team eval, pairwise preference eval | alignment measurement | attach now |

## Core Sources

Human preference foundations:

- Christiano et al., 2017, "Deep Reinforcement Learning from Human
  Preferences": https://arxiv.org/abs/1706.03741
- Stiennon et al., 2020, "Learning to summarize from human feedback":
  https://arxiv.org/abs/2009.01325 and
  https://openai.com/research/learning-to-summarize-with-human-feedback
- Ouyang et al., 2022, InstructGPT:
  https://arxiv.org/abs/2203.02155 and
  https://openai.com/index/instruction-following/

Anthropic / constitutional / red-team line:

- Helpful and Harmless RLHF: https://huggingface.co/papers/2204.05862
- HH-RLHF dataset: https://huggingface.co/datasets/Anthropic/hh-rlhf
- Constitutional AI: https://arxiv.org/abs/2212.08073
- Red teaming methods:
  https://www.anthropic.com/research/red-teaming-language-models-to-reduce-harms-methods-scaling-behaviors-and-lessons-learned
  and https://arxiv.org/abs/2202.03286
- Responsible Scaling Policy:
  https://www.anthropic.com/index/anthropics-responsible-scaling-policy
- Alignment faking: https://www.anthropic.com/research/alignment-faking
- Model Spec Midtraining: https://alignment.anthropic.com/2026/msm/

OpenAI specification / oversight line:

- Model Spec: https://model-spec.openai.com/2025-02-12.html
- Model Spec approach and evals:
  https://openai.com/index/our-approach-to-the-model-spec/
- Deliberative Alignment:
  https://openai.com/index/deliberative-alignment/
- Weak-to-Strong Generalization:
  https://openai.com/index/weak-to-strong-generalization/
- Preparedness Framework:
  https://openai.com/index/updating-our-preparedness-framework/
- Safety evaluations hub: https://openai.com/safety/evaluations-hub/
- OpenAI Evals: https://github.com/openai/evals

Google DeepMind / Meta / open ecosystem:

- Sparrow: https://deepmind.google/blog/building-safer-dialogue-agents
- RLAIF: https://huggingface.co/papers/2309.00267
- Frontier Safety Framework:
  https://deepmind.google/discover/blog/introducing-the-frontier-safety-framework/
- Llama 2 methodology: https://arxiv.org/abs/2307.09288
- Self-Rewarding LMs: https://arxiv.org/abs/2401.10020

Preference optimization / toolchains:

- DPO: https://arxiv.org/abs/2305.18290
- Safe RLHF: https://arxiv.org/abs/2310.12773
- TRL: https://huggingface.co/docs/trl
- Alignment Handbook: https://github.com/huggingface/alignment-handbook
- OpenRLHF: https://github.com/OpenRLHF/OpenRLHF
- NeMo-Aligner:
  https://docs.nvidia.com/nemo-framework/user-guide/25.02/modelalignment/index.html

Evaluation systems:

- HarmBench: https://arxiv.org/abs/2402.04249
- Chatbot Arena: https://arxiv.org/abs/2403.04132

## What AIOS Should Attach First

1. **AIOS Behavior Spec** under `myworld`.
   Equivalent to Model Spec / Constitution. It should define authority,
   privacy, browsing, offline-user use, refusal/hold, dispatch-vs-direct-edit,
   autonomy, and reversibility.

2. **Preference Ledger** under `memoryOS`.
   Draft-first records for accepted/rejected results, A/B plan preferences,
   user critiques, and private-safe `user@offline` observations.

3. **Reward Rubric** under `myworld`, consumed by Hive and CapabilityOS.
   Initial axes: helpfulness, truth/evidence, privacy, reversibility,
   user-taste fit, autonomy risk, cost/latency, and learning value. Keep it
   multi-axis; do not collapse to one scalar early.

4. **AIOS Eval Harness** under `hivemind`.
   Run spec adherence, red-team, preference, routing, memory provenance,
   refusal/hold, and train-vs-deploy mismatch checks.

5. **Alignment Policy Updater** across `CapabilityOS` and `myworld`.
   Update route weights, templates, stop conditions, GenesisOS challenge
   frequency, provider defaults, Control Center wording, and when to ask
   `user@offline`.

6. **Fine-tuning Backend** later.
   Order should be SFT on accepted demos, DPO/ORPO on preference pairs, reward
   model only after broad enough pair data, then PPO/RLHF/GRPO only after eval
   gates are stable. RLAIF/self-rewarding may scale labels, not replace user
   authority.

## Recommended Contracts

1. `ASC-0210-aios-behavior-spec`
2. `ASC-0211-preference-ledger`
3. `ASC-0212-aios-reward-rubric`
4. `ASC-0213-alignment-eval-harness`
5. `ASC-0214-policy-updater`
6. `ASC-0215-local-dpo-pilot`

## Non-Goals For Now

- Do not train a general AIOS model before the preference ledger exists.
- Do not use self-rewarding loops without external calibration.
- Do not collapse user preference into safety compliance only.
- Do not treat RLHF as full alignment; it is one behavioral optimization layer.
- Do not let AI judges overwrite `user@offline` authority.

## Decision

Attach the alignment infrastructure first:

```text
Behavior Spec + Preference Ledger + Reward Rubric + Eval Harness
```

Then attach model optimization:

```text
SFT -> DPO/ORPO -> Reward Model -> PPO/RLHF/GRPO
```

The organism-level alignment target is AIOS policy, not a single provider
model.

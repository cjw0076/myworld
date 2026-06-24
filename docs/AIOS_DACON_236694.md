# dacon 236694 — AI Agent Action Prediction × AIOS

> 2026 AI·SW중심대학 디지털 경진대회 (AI부문). The competition AIOS was built for —
> and the rallying point for the AIOS community. https://dacon.io/competitions/official/236694

## The task (why it's a perfect fit)

Predict **which action an AI agent should take** given a user request + context —
optimized for a **lightweight, fast decision *before* invoking the LLM**, in
resource-constrained environments. Accuracy AND compute efficiency both score.

This is, almost exactly, **`aios behavior predict`**: DescentNet (Sheaf-theory
backbone) + the AkashicRecord of prior agent traces → ranked next-action candidates
with confidence + an H¹ ambiguity signal, *with no LLM call*. AIOS already does the
competition's core task as a shipped capability (`scripts/aios_agent_behavior.py`,
`aios behavior predict --context ... --candidates ...`).

## Facts

- **Prize:** ~₩12.2M total pool.
- **Timeline:** registration May 26–Jun 8 (closed) · team-merge Jun 5 · **preliminary
  Jul 1–15** · finalist materials Jul 20 · results Jul 27.
- **Data:** "추후 공개" — released ~Jul 1. Input features + metric not yet public.
- **Eligibility:** students (enrolled or on-leave, any major) of the 57 AI·SW-focused
  universities. ⚠️ **Open question for founder:** are we fielding eligible students
  (community play), or is the founder eligible? This gates how we "gather people."

## AIOS as the team's edge

1. **Day-0 baseline** — point `predict_behavior` at the released data; instant
   non-LLM baseline (frequency + DescentNet descent + transition scores).
2. **Lightweight by construction** — no LLM at inference = wins the efficiency axis;
   pure local scoring.
3. **Learns from the corpus** — ingest the competition's training trajectories into
   the AkashicRecord; predictions improve as the ledger grows (the self-improving
   loop, applied to a real benchmark).
4. **Cross-trajectory transfer** — the same machinery that lets a Codex run teach a
   Claude run lets one training split inform another.

## Recruiting / community hook

The competition is the **magnet** for the AIOS-dedicated community:
- Pitch: *"Bring AIOS to dacon 236694 — a shipped behavior-predictor + a learning
  ledger, free. Win the efficiency axis without an LLM at inference."*
- Onboarding for a competitor: `curl …/install.sh | sh` → `aios onboard` →
  `aios behavior predict …`. Minutes to a baseline.
- Community channels (BUILD_ON_AIOS "where the community lives"): a dacon-236694
  team space + a chat channel; share predictor recipes, leaderboard, ingest scripts.

## Prep plan (now → Jul 1 data drop)

- ✅ `predict_behavior` shipped + verified (HRMind-era F1 work, DescentNet live).
- ☐ A `--from-dataset` path: ingest the competition's training file → AkashicRecord,
  predict on the test split, emit the submission format (once the metric/format drop).
- ☐ A one-command "compete" recipe in the community guide.
- ☐ (founder) confirm eligibility route + open the team/channel.

## Founder decisions needed

1. **Eligibility route** — eligible students (community) vs founder-direct. Determines
   recruiting.
2. **Community surface** — dacon team + which chat (Discord/KakaoTalk/Slack)?
3. **Go intensity** — light (offer AIOS + a guide) vs heavy (operator-run reference
   submission once data drops).

— AIOS brings the behavior-prediction substrate; the founder brings the people and
the eligibility route. This is the override's outside-domain proof made concrete.

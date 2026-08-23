# SIGNAL SOCIETY-25 — Persistent Cultural Evolution + Experience Intelligence

Version **0.3.0** turns the 25-agent cultural-evolution experiment into a resumable, append-only experience-learning runtime.

## Canonical experiment

A persistent 25-agent cultural-evolution simulation in which autonomous synthetic agents maintain self-narratives, memories, relationships, schedules/social interactions, and dialogue while a bounded semantic seed is introduced and allowed to propagate, mutate, reproduce, or disappear naturally. Consequential events, semantic transitions, learning transitions, and frozen experience states retain evidence and provenance so the society can be inspected and resumed across runtime restarts.

## What 0.3.0 adds

- persistent resume: opening the same DB continues the same society
- explicit `--fresh` reset only when a new controlled run is intended
- hash-chained append-only event history
- append-only Informatrons, memories, artifacts, learning examples, version history, learning history, and experience snapshots
- replayable per-agent policy adaptation
- versioned experience snapshots for all 25 agents
- deterministic restart-safe simulation randomness
- agent-specific evidence-grounded Q&A
- evidence-grounded copilot state
- lineage-aware co-creation guidance
- Canon verification and artifact genealogy
- signal / neutral / no-seed controls
- CI deployment artifact containing a resumable SQLite society plus verification metrics

## Continuity model

```text
world/social event
      ↓
append-only event chain
      ↓
Informatrons + memories + learning examples
      ↓
append-only learning-history transition
      ↓
materialized agent policy state
      ↓
replay check
      ↓
versioned experience snapshot
      ↓
cold restart / resume
```

The materialized `agent_learning_state` is an operational cache. `learning_history` records how it changed, and replay must reconstruct the same learned state.

## Experience intelligence

The learner currently adapts explicit bounded policy variables from verified outcomes:

- experience count
- prediction accuracy
- sharing bias
- question/inquiry bias
- adaptation score

An incorrect prediction can increase question pressure and reduce sharing pressure. Correct predictions can move the policy in the opposite direction. Each transition is logged with its before/after state, surprise value, source evidence, day, and tick.

This is real online state adaptation, but it is **not** uncontrolled neural self-training.

## Bootstrap all 25 learners

```bash
python bootstrap_experience.py --db signal_society_25.db
```

This writes an append-only versioned experience snapshot for each agent and reports:

- experience snapshot-chain validity
- learning-history-chain validity
- replay equivalence between history and materialized state

## Ask an agent for evidence-grounded help

```bash
python run.py \
  --db signal_society_25.db \
  --days 0 \
  --help-agent A14 \
  --objective "What have I learned about the card?"
```

The copilot searches only that agent's stored memories and exposes supporting source event IDs rather than inventing an answer when evidence is absent.

## Co-create from an artifact lineage

```bash
python run.py \
  --db signal_society_25.db \
  --days 0 \
  --help-agent A14 \
  --objective "Help me create a descendant" \
  --parent-artifact ART-SEED-001
```

Co-creation carries forward recorded inheritance, proposes a bounded mutation based on learned agent state, and preserves an open descendant handle. It does not manufacture an ancestry relation.

## Persistent run

First boot:

```bash
python run.py --fresh --db signal.db --days 5 --seed-mode signal --verify-learning-replay
```

Cold resume of the same society:

```bash
python run.py --db signal.db --days 5 --verify-learning-replay
```

The second invocation continues from the prior day/tick and appends new events instead of erasing history.

## Controls

```bash
python run_control.py
```

Runs fixed-seed signal, neutral, and no-seed conditions for comparison.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Deployment

The GitHub Actions workflow performs tests, creates a fresh seeded society, cold-resumes that exact SQLite database, bootstraps versioned experience states, runs A/B controls, and publishes the resumable DB plus metrics as a workflow artifact.

This is a deployable experimental runtime artifact, **not yet a public web service**.

## Safety / epistemic boundary

- generated beliefs do not automatically become training truth
- verified learning examples remain separate from raw dialogue
- append-only historical tables cannot be silently rewritten through normal SQL UPDATE/DELETE operations
- experience learning changes explicit inspectable state
- neural adapter/LoRA training, if added, must remain a separate frozen-dataset + pre/post-verification gate

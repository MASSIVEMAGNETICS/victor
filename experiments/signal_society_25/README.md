# SIGNAL SOCIETY-25 — Persistent Cultural Evolution + Online Learning Experiment

A controlled 25-agent synthetic society for testing cultural propagation, semantic mutation,
persistent memory, question formation, synthetic learning-data generation, and later
cognition-model replacement.

## Canonical experiment

A persistent 25-agent cultural-evolution simulation in which autonomous synthetic agents maintain
self-narratives, memories, relationships, schedules/social interactions, and dialogue while a
bounded semantic seed is introduced and allowed to propagate, mutate, reproduce, or disappear
naturally. Every consequential state transition is captured as an Informatron, allowing the society
and its cultural genealogy to be replayed across cognition-model replacement.

## v0.1 implementation

- 25 deterministic heterogeneous agent profiles
- SQLite/WAL canonical database
- deterministic per-agent daily schedules
- per-agent episodic, semantic/social, and self memory
- self-narrative updates
- relationship/familiarity tracking
- dyadic + group social dialogue
- bounded Signal Genome seed introduction
- artifact awareness + descendant-artifact genealogy
- question ledger + per-agent evidence-linked memory querying (`ask_agent`)
- evidence-linked Informatron log
- audio-ready dialogue segment log with transcript SHA-256
- real-time verified synthetic learning examples:
  - episodic recall
  - social recall
  - social prediction/outcome
  - artifact lineage
  - self-model reconstruction
- per-agent verified JSONL training-data export
- no online neural-weight mutation in v0.1; learning is immediate state/memory adaptation plus a verified experience buffer

## Why learning is separated from logging

The database stores four distinct layers:

1. **events** — what happened
2. **memories/beliefs/relationships** — what each agent currently carries forward
3. **informatrons** — evidence-linked durable semantic transitions
4. **learning_examples** — verified synthetic data suitable for later adapter/LoRA training

An agent's generated belief is never automatically treated as training truth. Synthetic examples are
created from events with explicit targets/outcomes and marked `verified=1` only when the simulation
itself provides the ground truth.

## Audio

`audio_segments` stores the evidence contract for dialogue: event ID, speaker, transcript, SHA-256,
and optional source path/timing. v0.1 is **audio-ready but does not synthesize speech**. A TTS layer can
later render the exact transcript and populate `source_path`, `start_ms`, and `end_ms` without changing
the canonical semantic event.

## Run

```bash
python run.py --db signal_society_25.db --days 30 --interactions-per-day 35 --groups-per-day 2 --seed 25 --export-training-data training_data
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Next stage

- ModelAdapter interface for local LLM cognition
- actual TTS/audio render + speech-to-text round-trip tests
- 90-day A/B runs with fixed population/random seed
- Day-45 cold model swap: Model A -> Chronos/Rograph replay -> Model B
- question-answer retrieval over each agent's personal lifetime database
- verified dataset export to JSONL for per-agent LoRA/adapters
- model update gate comparing memory accuracy, calibration, hallucination rate, and social prediction accuracy before activation

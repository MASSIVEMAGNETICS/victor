# SIGNAL SOCIETY-25 CHANGELOG

This changelog is append-only. Earlier entries remain part of the experiment record.

## 0.1.0 — Genesis scaffold

- 25 deterministic heterogeneous agents.
- SQLite/WAL state, schedules, dyadic/group dialogue.
- Episodic/social/self memory and self-narratives.
- Signal seed, descendant artifacts, questions, transcript hashes.
- Verified synthetic learning-example export.

## 0.2.0 — Evidence + Experience

- Adds an append-only, hash-chained event ledger with deterministic sequence, event hash and chain hash verification.
- Adds SQLite guards rejecting UPDATE/DELETE on events, Informatrons, memories, artifacts, learning examples and version history.
- Adds append-only version-history records and version hashes.
- Bootstraps bounded experience-based intelligence: per-agent prediction accuracy, surprise, question pressure and sharing-policy adaptation.
- Adds evidence-grounded cooperative helper queries over each agent's own memories.
- Fixes group epistemic leakage: an artifact-bearing speaker must already know the artifact.
- Replaces automatic canon assignment with a Canon Verifier using inheritance + mutation + open handle + protected-constraint checks.
- Expands Signal Genome to v1.1 with archetypes, recurring symbols, emotional carriers, mutation permissions and inheritance requirements.
- Adds question resolution when ancestry evidence is available.
- Adds signal / neutral / no-seed control modes.
- Adds stronger metrics: chain validity, chain head, materialized-state digest, canonical/non-canonical descendants, resolved questions and prediction accuracy.
- Adds CI verification and deterministic control runs.

### Boundary

v0.2.0 learns through verified experience and bounded policy adaptation. It does not continuously retrain a foundation model on self-generated text. Neural adapter/LoRA training remains gated behind frozen verified datasets and pre/post evaluation.

## 0.3.0 — Persistent Experience Copilot

- Makes runtime continuity persistent by default: reopening the same database resumes the same society instead of resetting it.
- Adds explicit `--fresh` as the only CLI path that intentionally starts a new materialized society database.
- Adds persistent runtime metadata for day, tick, seed, seed mode, and experiment version.
- Adds deterministic tick-scoped random generation so cold restart does not depend on transient process RNG state.
- Adds append-only `learning_history`, hash-chained across every bounded adaptation.
- Adds replay verification that reconstructs each agent's current learned policy state from learning history and compares it with the materialized state.
- Adds append-only, per-agent versioned `experience_snapshots` with predecessor hashes and source-history counts.
- Reinterprets `learning_version` as an explicit frozen experience-snapshot version.
- Adds `bootstrap_experience.py` to freeze all 25 current learners into versioned experience states.
- Adds an evidence-grounded agent copilot over private memory, unresolved questions, and learned policy state.
- Adds lineage-aware co-creation help that carries forward recorded parent inheritance, proposes bounded mutation, and preserves an open descendant handle.
- Adds persistent-resume, append-only learning-history, replay, snapshot-versioning, and copilot regression tests.
- Updates deployment CI to create a fresh society, cold-resume the same database, bootstrap experience snapshots, run controls, and publish the resumable database plus verification metrics as an artifact.

### Boundary

v0.3.0 implements explicit, inspectable, replayable experience learning. It does not silently fine-tune or recursively train a foundation model on its own generated text. Any neural adapter/LoRA stage remains a separately versioned, verification-gated transition.

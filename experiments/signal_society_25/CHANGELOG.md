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

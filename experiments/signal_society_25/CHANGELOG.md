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

## Clustered release train — 0.4.0 through 1.0.0

These seven releases are packaged and gated together. Every stage emits a hash-chained release receipt and passing stages are appended to the experiment `version_history` when the cluster runner executes.

### 0.4.0 — Recursive R&D Cluster

- Adds bounded recursive research cycles over signal, neutral, and no-seed control arms.
- Feeds measured uncertainty and prediction performance into the next cycle's research focus and interaction density.
- Adds append-only, hash-chained R&D cycle receipts.

### 0.5.0 — Experience Ecology

- Promotes per-agent learning replay and experience snapshot lineage to release gates.
- Requires learned materialized state to match replayed learning history.
- Preserves 25 distinct agent experience states rather than collapsing the population into one memory.

### 0.6.0 — Cultural Phylogeny

- Adds measurable lineage depth, branching, leaf/terminal branches, canon ratio, and parent integrity.
- Keeps canon compatibility distinct from transmission success.

### 0.7.0 — Cold-Swap Continuity

- Adds deterministic canonical-state export.
- Adds two independent adapter implementations that receive only canonical state and must produce equivalent operational decisions.
- Explicitly does not claim cross-foundation-model continuity yet.

### 0.8.0 — Multimodal Evidence Contract

- Audits dialogue transcript hashes.
- Separates transcript-only evidence from actual rendered physical audio.
- Keeps TTS/STT round-trip verification as an explicit future gate instead of fabricating audio completeness.

### 0.9.0 — Victor Omni Sentinel

- Adds evidence-first monitoring for Chronos, learning history, experience snapshots, append-only guards, epistemic speaker integrity, lineage integrity, learned-state replay, transcript hashes, canon observability, and question resolution.
- Adds RED / AMBER / GREEN status with hard failures separated from incomplete-but-explicit evidence states.

### 1.0.0 — Cluster Deployment

- Packages the entire seven-stage train into one deterministic deployment runner.
- Adds a read-only Omni HTTP service exposing health, sentinel, metrics, release manifest, and evidence-grounded agent copilot endpoints.
- Adds Docker and Compose deployment.
- Adds CI that runs the full tests, recursive cluster, Omni Sentinel, service health probes, container build, deployment bundle hashing, artifact upload, and GHCR publish on the authoritative branch.

### Boundary

The 1.0.0 package delivers a fully testable deployment unit and container publication path. The 0.7.0 model-swap harness still uses deterministic adapters rather than two real foundation models, and 0.8.0 reports transcript-only audio honestly until an actual TTS/STT layer is connected.

# SIGNAL SOCIETY-25 — Seven-Release Cluster Package

Package version: **1.0.0**

This package clusters the next seven Signal Society releases into one gated release train. They are executed in order and each stage emits an append-only release receipt. A later stage does not erase a failed earlier gate.

## Release train

| Version | Codename | Delivery |
|---|---|---|
| 0.4.0 | Recursive R&D Cluster | signal / neutral / no-seed research arms, recursive next-cycle selection, hash-chained R&D receipts |
| 0.5.0 | Experience Ecology | population learning metrics, replay verification, per-agent experience snapshots |
| 0.6.0 | Cultural Phylogeny | lineage depth, branching, terminal branches, canon ratio, parent integrity |
| 0.7.0 | Cold-Swap Continuity | canonical-state export + two independent deterministic adapters consuming zero predecessor context |
| 0.8.0 | Multimodal Evidence Contract | transcript SHA verification and explicit distinction between transcript-only and physical audio evidence |
| 0.9.0 | Victor Omni Sentinel | hard invariant audit, append-only guards, learning replay, lineage integrity, epistemic speaker integrity, deployment gate |
| 1.0.0 | Cluster Deployment | HTTP service, Docker packaging, CI deployment artifact, release manifest and release-receipt chain |

## Recursive R&D law

The research cluster executes controlled arms under the same seed:

```text
signal
neutral
no-seed
   ↓
measure
   ↓
compare
   ↓
identify weak/uncertain dimension
   ↓
modify only next-cycle interaction density/focus
   ↓
repeat
```

The score is an experiment-navigation convenience, not a probability, truth score, or claim of cultural fitness.

## Omni Sentinel

Victor Omni Sentinel is an evidence-first supervisory process. It does not become an authority above evidence. It reports explicit checks:

- Chronos hash chain
- learning-history hash chain
- experience-snapshot chains
- append-only database guards
- group-speaker epistemic integrity
- artifact parent integrity
- learned-state replay equivalence
- transcript hash integrity
- physical-audio completeness status
- canon observability
- question-resolution observability

A hard invariant failure produces **RED**. Missing physical audio while transcript hashes remain valid produces **AMBER**, not a fabricated claim that audio exists.

## Deployment

Build the clustered deployment:

```bash
python run_cluster.py --output-dir deployment --fresh --strict
```

Start the read-only Omni service:

```bash
python serve_omni.py --db deployment/signal_society_25.db --host 0.0.0.0 --port 8787
```

Routes:

- `GET /health`
- `GET /sentinel`
- `GET /metrics`
- `GET /releases`
- `GET /copilot?agent_id=A14&q=What%20did%20I%20learn?`
- `GET /copilot?agent_id=A14&q=Help%20me%20continue&parent=ART-SEED-001`

Docker:

```bash
docker build -t victor-omni-sentinel:1.0.0 .
docker run --rm -p 8787:8787 -v "$PWD/deployment:/data" victor-omni-sentinel:1.0.0
```

## Model-swap boundary

The 0.7.0 harness uses two independent deterministic adapters. It verifies canonical-state-only handoff and decision equivalence. It **does not yet prove Qwen -> Llama or other cross-foundation-model continuity**. That remains a next experimental extension requiring actual model runtimes.

## Neural-learning boundary

Experience learning remains explicit, bounded and replayable. The release train does not silently fine-tune a foundation model on its own generated text. Any LoRA/adapter training remains downstream of frozen verified datasets and pre/post evaluation.

# SIGNAL SOCIETY-25 Experiment Spec v0.3

## Canonical research vehicle

A persistent 25-agent cultural-evolution simulation in which autonomous synthetic agents maintain self-narratives, memories, relationships, schedules, social dialogue, questions, and explicit learned policy state while a bounded semantic seed is introduced and allowed to propagate, mutate, reproduce, fragment, or disappear naturally.

The experiment preserves separate evidence-bearing layers for:

1. what happened;
2. what each agent remembers/believes;
3. how each agent's learned policy changed;
4. what synthetic learning examples were verified;
5. which experience-state version was frozen.

## Research questions

1. Does a bounded semantic seed propagate differently from neutral/no-seed controls without a success mandate?
2. Can persistent agents maintain coherent private memory and self-narrative across cold runtime restarts?
3. Can social prediction error and surprise produce useful bounded real-time adaptation without turning generated beliefs into truth?
4. Can learned policy state be reconstructed from append-only experience history?
5. Can a learner answer questions and assist co-creation using only its own evidence-linked experience?
6. Can cultural genealogy and agent state later survive replacement of the cognition model while provenance remains intact?

## Continuity invariants

- Events are append-only and hash chained.
- Informatrons, memories, artifacts, accepted learning examples, version history, learning history, and experience snapshots reject normal UPDATE/DELETE mutation.
- Runtime restart resumes the same day/tick/seed/seed-mode unless an explicit fresh run is requested.
- Current learned policy state must equal replay of that agent's learning history.
- Experience snapshots are per-agent versioned and predecessor-hash linked.
- Artifact-bearing group speakers must already possess the referenced artifact.
- Canon is verified rather than assigned by default.

## Learning contract

Learning is split into two layers.

### Online experience adaptation

Verified outcomes and prediction error update explicit bounded policy variables such as sharing pressure, inquiry pressure, prediction accuracy, and adaptation score. The before/after transition is appended to learning history.

### Future neural adaptation

Any LoRA/adapter training remains outside the online loop. It may only consume frozen verified datasets and must pass pre/post evaluation before a new model version becomes active.

## Cooperative intelligence contract

An agent may help by:

- retrieving evidence from its private memories;
- identifying unresolved questions;
- exposing its current learned policy state;
- suggesting a lineage-compatible mutation for an existing artifact;
- preserving the parent's recorded inherited elements and open descendant handle.

The helper must return unknown when its own memory does not support an answer and must not fabricate cultural ancestry.

## Controlled variables

- 25 fixed deterministic agents
- fixed agent-generation seed
- fixed simulation seed
- signal / neutral / no-seed condition
- interaction density
- simulation duration

## Core observables

- awareness and artifact transmission
- canonical/non-canonical descendant count
- event and Informatron count
- per-agent memory count
- questions generated/resolved
- verified learning examples
- prediction accuracy
- learning-history length and integrity
- learning replay equivalence
- experience snapshot count/version/integrity
- materialized-state digest
- later: cross-model continuity

## Experimental non-goals

- The Signal is not forced to spread.
- Popularity does not define canon.
- Agent-generated beliefs are not automatically ground truth.
- v0.3 does not claim human-equivalent cognition or autonomous foundation-model self-training.

## Seed

> Carry something forward. Change something. Leave something unfinished.

The seed is introduced as an unexplained artifact. Agents receive no instruction to believe, obey, or reproduce it.

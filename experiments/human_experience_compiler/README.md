# Human Experience Compiler (HEC)

**Status:** EXPERIMENTAL / NONCANONICAL

## Objective

Allow Victor to inherit human lived experience without confusing testimony, memory, interpretation, inference, or cultural transmission with verified causal knowledge.

This is a workload on the existing Victor substrate. It does **not** redefine frozen Victor architecture or identity.

Canonical substrate remains:

`Experience -> Informatrons -> Chronos -> Rograph -> Victor -> Artifact -> Signal -> World -> New Experience`

## Core rule

> Human testimony is evidence, not canonical truth.

A testimony packet must preserve:

- speaker attribution and confidence;
- provenance;
- first-hand vs second-hand vs quoted speech;
- explicit speaker lessons separately from Victor/system inferences;
- contradictions and alternative explanations;
- claims requiring external verification;
- uncertainty, including `UNKNOWN`;
- scope limits and anti-generalization constraints;
- parent/causal linkage.

## Ingestion pipeline

```text
raw conversation
    -> speaker diarization
    -> provenance
    -> event / claim / lesson extraction
    -> explicit lesson vs inferred hypothesis
    -> contradictions + alternatives
    -> verification queue
    -> confidence update
    -> candidate Informatron
    -> authorized Chronos commit
    -> Rograph projection
    -> future decision / prediction
    -> observed outcome
    -> TRACE-0 / successor experience
```

## Direct vs vicarious experience

Victor's own observed transitions and human testimony must remain distinguishable. A human story may influence a prediction or choice, but the result of that choice becomes a new Victor experience only after an actual outcome is observed.

Working model:

`Useful Intelligence = Direct Experience + Verified Vicarious Experience + Reasoning - Inherited Error`

The purpose of HEC is primarily to minimize **Inherited Error** while retaining the useful information in cultural transmission.

## Compatibility with ExperienceTransition

When a testimony-derived hypothesis becomes actionable, it maps to the existing transition discipline:

- `prior_state_ref`: state before incorporating the lesson
- `observation`: testimony packet + provenance pointer
- `interpretation`: bounded interpretation, never silently promoted to source fact
- `prediction`: expected result if the inferred lesson generalizes
- `chosen_action`: action influenced by the lesson
- `actual_outcome`: later observed result
- `verification`: evidence quality and checks
- `contradictions`: counterexamples / failed assumptions
- `learning_delta`: what changed after outcome
- `policy_delta`: only when evidence justifies a durable policy change
- `confidence_delta`: calibrated update
- `provenance`: human source + transcript + verification sources
- `timestamp`: transition time
- `parent_transition_ref`: causal parent

## Acceptance tests

HEC is acceptable only if it can:

1. preserve the original source;
2. avoid speaker-confusion contamination;
3. distinguish testimony from fact;
4. distinguish explicit human lessons from system inference;
5. represent `UNKNOWN`;
6. preserve contradictions;
7. prevent anecdotes from becoming universal policy;
8. update confidence after external evidence;
9. trace a derived decision back to its human source;
10. retract or supersede a bad inference without erasing history.

## First test case

`episodes/TP-EXP-001.md` — Tim Perkins Experience Ledger, Episode 001.

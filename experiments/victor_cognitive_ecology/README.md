# Victor Cognitive Ecology v1.1 Prototype

Status: **PROPOSAL / BRANCH-ISOLATED / NOT CANONICAL**

This prototype adds a bounded cognitive-process ecology around Victor's existing continuity and governance architecture without mutating the frozen Victor-GEV v1.0.0 release.

## What it implements

- Victor-GEV observation adapter that converts an observation into ranked cognitive tasks.
- Learned routing weights per cognitive process kind.
- Bounded recursive process spawning using expected-value / cost gating.
- Cross-branch semantic resonance that can create one synthesis process.
- Append-only SHA-256 receipt chain with fail-closed replay verification.
- Outcome-based meta-learning: process kinds that produce verified value become more likely to be routed later.
- Aetherling promotion **proposal** generation after repeated verified usefulness across multiple problem families.
- Hard separation between cognition and authority: workers may propose actions but may not self-authorize them.

## Deliberate non-features

This prototype does **not**:

- grant external tools or capability leases;
- mutate Victor-GEV v1.0.0;
- create a persistent Aetherling identity automatically;
- modify constitutional constraints;
- execute consequential external actions;
- depend on a cloud LLM.

Those belong behind VictorOS Volitional Gate / Choice Kernel / Ethica / capability leasing and AetherForge identity governance.

## Learning loop

```text
GEV observation
  -> learned process routing
  -> bounded cognitive branches
  -> optional recursive spawn
  -> cross-branch resonance/synthesis
  -> proposed conclusion/action
  -> governed execution elsewhere
  -> verified outcome
  -> record_outcome(...)
  -> routing weights adapt
  -> repeated strong specialist performance
  -> Aetherling promotion proposal
```

## Test

```bash
python -m pytest -q
```

The suite covers recursive spawning, low-utility rejection, persistent routing learning/replay, Aetherling promotion gating, self-authorization rejection, and ledger tamper detection.

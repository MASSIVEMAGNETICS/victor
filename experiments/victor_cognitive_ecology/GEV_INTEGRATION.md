# Victor-GEV → Cognitive Ecology Integration

This file defines the minimal integration boundary for the private/full Victor-GEV runtime. Victor-GEV v1.0.0 remains immutable; integrate this only in a successor runtime or adapter layer.

## 1. Create one persistent ecology per Victor identity

```python
from pathlib import Path
from cognitive_ecology import Budget, CognitiveEcology

ecology = CognitiveEcology(
    Path(victor_state_dir) / "cognitive_ecology.jsonl",
    budget=Budget(
        max_processes=16,
        max_depth=3,
        max_cost=12.0,
        spawn_threshold=0.75,
    ),
)
```

Register bounded workers for process kinds such as `causal`, `temporal`, `adversarial`, `novelty`, and `synthesis`. A worker receives a `CognitiveTask` and returns a `CognitiveResult`. Workers are cognitive only: they must not own unrestricted external tools or authorization state.

## 2. Dispatch from a verified GEV observation

```python
from cognitive_ecology import GEVObservation

obs = GEVObservation(
    observation_id=gev_event.id,
    features=gev_event.features,
    changes=tuple(gev_event.changes),
    unknowns=tuple(gev_event.unknowns),
    confidence=gev_event.confidence,
    provenance_refs=tuple(gev_event.provenance_refs),
)

roots = ecology.tasks_from_gev(obs)
results = ecology.run(roots, problem_family="gev")
```

The returned results are proposals/findings. Any proposed consequential action must enter Victor's existing Volitional Gate → Choice Kernel → Ethica → capability-lease path.

## 3. Feed back only verified outcomes

After TRACE/Chronos has evidence for what actually happened, score the contribution of each cognitive result and record the outcome:

```python
for result in results:
    reward = verified_reward_for(result, trace_receipt)
    ecology.record_outcome(
        result,
        reward=reward,
        problem_family=classify_problem_family(obs),
        evidence_refs=(trace_receipt.trace_hash,),
    )
```

Do not reward a branch because its prose sounds persuasive. Reward must be grounded in observable prediction accuracy, useful information gain, successful falsification, verified task progress, or other evidence-backed criteria.

## 4. Let routing adapt

On later observations, `tasks_from_gev()` ranks registered process kinds by learned routing weight. High-performing cognitive styles therefore receive more routing priority while low-performing styles decay toward the configured floor.

## 5. Aetherling promotion remains governed

Periodically request:

```python
proposal = ecology.promotion_proposal("causal")
```

An eligible proposal is evidence that a cognitive specialization has repeatedly produced value. It is **not** permission to create identity, persistence, tools, or authority. Feed the proposal into AetherForge/VictorOS genesis review. Only that governed path may assign a `soul_token`, persistent memory, lifecycle, and capability leases.

## Acceptance boundary

Before successor release promotion, verify:

1. GEV observations carry stable IDs and provenance refs.
2. Worker outputs cannot directly execute external actions.
3. TRACE/Chronos outcomes are the only source of production learning rewards.
4. Restart/replay preserves learned routing exactly.
5. Tampering with the cognitive ledger fails closed.
6. Recursion depth, process count, and compute cost remain bounded under adversarial worker output.
7. Aetherling promotion never self-grants persistence or authority.

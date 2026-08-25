from __future__ import annotations

import json
from pathlib import Path

import pytest

from cognitive_ecology import (
    Budget,
    CognitiveEcology,
    CognitiveResult,
    CognitiveTask,
    GEVObservation,
    SpawnRequest,
)


def worker_with_spawn(task: CognitiveTask) -> CognitiveResult:
    spawn = ()
    if task.depth == 0:
        spawn = (
            SpawnRequest(
                process_kind="adversarial",
                question="Try to falsify the causal hypothesis.",
                expected_value=1.6,
                estimated_cost=1.0,
                rationale="high uncertainty",
            ),
        )
    return CognitiveResult(
        task.task_id,
        task.process_kind,
        answer="shared signal causal pattern with temporal structure",
        confidence=0.8,
        concepts=("shared", "signal", "causal", "pattern", "temporal"),
        spawn_requests=spawn,
    )


def plain_worker(task: CognitiveTask) -> CognitiveResult:
    return CognitiveResult(
        task.task_id,
        task.process_kind,
        answer="shared signal pattern temporal alternative",
        confidence=0.75,
        concepts=("shared", "signal", "pattern", "temporal", "alternative"),
    )


def synthesis_worker(task: CognitiveTask) -> CognitiveResult:
    return CognitiveResult(
        task.task_id,
        task.process_kind,
        answer="joint hypothesis: the shared signal has a causal temporal mechanism",
        confidence=0.7,
        concepts=("shared", "signal", "causal", "temporal", "mechanism"),
    )


def test_gev_dispatch_and_bounded_recursive_spawn(tmp_path: Path) -> None:
    eco = CognitiveEcology(tmp_path / "ledger.jsonl", budget=Budget(max_processes=6, max_depth=2, max_cost=6))
    eco.register("causal", worker_with_spawn)
    eco.register("temporal", plain_worker)
    eco.register("adversarial", plain_worker)
    eco.register("synthesis", synthesis_worker)

    obs = GEVObservation(
        observation_id="GEV-1",
        features={"object_count": 7},
        changes=("object moved east", "new object appeared"),
        unknowns=("occlusion",),
        confidence=0.9,
        provenance_refs=("frame:001", "frame:002"),
    )
    roots = eco.tasks_from_gev(obs, candidate_kinds=("causal", "temporal"), limit=2)
    results = eco.run(roots, problem_family="gev-change-detection")

    kinds = [r.process_kind for r in results]
    assert kinds.count("causal") == 1
    assert "temporal" in kinds
    assert "adversarial" in kinds
    assert "synthesis" in kinds
    assert eco.verify_ledger()


def test_low_utility_spawn_is_denied(tmp_path: Path) -> None:
    def weak_spawn(task: CognitiveTask) -> CognitiveResult:
        return CognitiveResult(
            task.task_id,
            task.process_kind,
            "answer",
            0.5,
            spawn_requests=(SpawnRequest("adversarial", "weak", expected_value=0.2, estimated_cost=1.0),),
        )

    eco = CognitiveEcology(tmp_path / "ledger.jsonl", budget=Budget(spawn_threshold=0.75))
    eco.register("causal", weak_spawn)
    eco.register("adversarial", plain_worker)
    root = CognitiveTask("root", "causal", "why?")
    results = eco.run([root])
    assert [r.process_kind for r in results] == ["causal"]
    text = (tmp_path / "ledger.jsonl").read_text()
    assert "utility_below_threshold" in text


def test_verified_outcomes_change_future_routing_and_replay(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    eco = CognitiveEcology(ledger)
    eco.register("causal", plain_worker)
    eco.register("novelty", plain_worker)

    causal = CognitiveResult("c1", "causal", "x", 0.9)
    novelty = CognitiveResult("n1", "novelty", "x", 0.9)
    for i in range(8):
        eco.record_outcome(causal, reward=0.95, problem_family=f"family-{i%3}")
        eco.record_outcome(novelty, reward=0.10, problem_family=f"family-{i%3}")

    assert eco.routing_weight("causal") > eco.routing_weight("novelty")
    assert eco.route(("novelty", "causal"), limit=1) == ["causal"]

    replayed = CognitiveEcology(ledger)
    replayed.register("causal", plain_worker)
    replayed.register("novelty", plain_worker)
    assert replayed.routing_weight("causal") == pytest.approx(eco.routing_weight("causal"))
    assert replayed.routing_weight("novelty") == pytest.approx(eco.routing_weight("novelty"))


def test_aetherling_promotion_is_proposal_not_self_grant(tmp_path: Path) -> None:
    eco = CognitiveEcology(tmp_path / "ledger.jsonl")
    eco.register("causal", plain_worker)
    result = CognitiveResult("c1", "causal", "x", 0.9)
    for i in range(24):
        eco.record_outcome(result, reward=0.9, problem_family=f"family-{i%4}")
    proposal = eco.promotion_proposal("causal")
    assert proposal.eligible is True
    assert proposal.suggested_dna["soul_token"] is None
    assert "No authority inheritance" in proposal.suggested_dna["guardrails"][0]


def test_worker_cannot_self_authorize_action(tmp_path: Path) -> None:
    def bad_worker(task: CognitiveTask) -> CognitiveResult:
        return CognitiveResult(
            task.task_id,
            task.process_kind,
            "do it",
            1.0,
            proposed_action={"type": "external_write", "authorized": True},
        )

    eco = CognitiveEcology(tmp_path / "ledger.jsonl")
    eco.register("causal", bad_worker)
    with pytest.raises(ValueError, match="self-authorize"):
        eco.run([CognitiveTask("root", "causal", "act")])


def test_ledger_tampering_fails_closed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    eco = CognitiveEcology(ledger)
    eco.register("causal", plain_worker)
    eco.run([CognitiveTask("root", "causal", "why?")])
    rows = ledger.read_text().splitlines()
    row = json.loads(rows[0])
    row["payload"]["spent"] = 999
    rows[0] = json.dumps(row)
    ledger.write_text("\n".join(rows) + "\n")
    assert eco.verify_ledger() is False
    with pytest.raises(ValueError, match="ledger failed verification"):
        eco._append("x", {})

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

CONTRACT_NAME = "ExperienceTransition"
CONTRACT_VERSION = "1.0.0"
REDUCER_VERSION = "signal_society.experience_reducer.v1"
REQUIRED_FIELDS = (
    "transition_id",
    "prior_state_ref",
    "observation",
    "interpretation",
    "prediction",
    "chosen_action",
    "actual_outcome",
    "verification",
    "contradictions",
    "learning_delta",
    "policy_delta",
    "confidence_delta",
    "provenance",
    "timestamp",
    "parent_transition_ref",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _hash(value: Any) -> str:
    if not isinstance(value, str):
        value = canonical_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def state_ref(state: dict[str, Any]) -> str:
    return "sha256:" + _hash(state)


def simulation_timestamp(day: int, tick: int) -> str:
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    dt = epoch + timedelta(days=int(day), seconds=int(tick))
    return dt.isoformat()


def _field_delta(before: Any, after: Any) -> dict[str, Any]:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        delta = after - before
    else:
        delta = None
    return {"before": before, "after": after, "delta": delta}


def _prediction_accuracy(state: dict[str, Any]) -> float | None:
    total = int(state.get("prediction_total", 0))
    correct = int(state.get("prediction_correct", 0))
    return (correct / total) if total else None


def latest_transition_ref(db, aid: str) -> str | None:
    rows = db.conn.execute(
        "SELECT payload_json FROM learning_history WHERE agent_id=? ORDER BY sequence DESC",
        (aid,),
    ).fetchall()
    for (payload_json,) in rows:
        try:
            payload = json.loads(payload_json)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and payload.get("transition_id"):
            return str(payload["transition_id"])
    return None


def build_experience_transition(
    *,
    db,
    aid: str,
    tick: int,
    day: int,
    before: dict[str, Any],
    after: dict[str, Any],
    prediction_correct: bool | None,
    surprise: float,
    source_event_id: str | None,
) -> dict[str, Any]:
    parent = latest_transition_ref(db, aid)
    learning_keys = ("experience_count", "prediction_total", "prediction_correct")
    policy_keys = ("share_bias", "question_bias", "adaptation_score")

    learning_delta = {k: _field_delta(before[k], after[k]) for k in learning_keys}
    policy_delta = {k: _field_delta(before[k], after[k]) for k in policy_keys}
    before_accuracy = _prediction_accuracy(before)
    after_accuracy = _prediction_accuracy(after)
    confidence_delta = {"prediction_accuracy": _field_delta(before_accuracy, after_accuracy)}

    if source_event_id:
        verification = {
            "status": "verified",
            "evidence_refs": [source_event_id],
            "method": "source_event_linkage+deterministic_reducer",
            "notes": "Policy adaptation is grounded in the linked Chronos event and replayed deterministically.",
        }
        sources = [{"evidence_ref": source_event_id}]
    else:
        verification = {
            "status": "inconclusive",
            "evidence_refs": [],
            "method": "deterministic_reducer_without_source_event",
            "notes": "State mutation is replayable, but no source Chronos event was supplied.",
        }
        sources = [{"source_id": "signal_society:unlinked_experience"}]

    contradictions = []
    if prediction_correct is False:
        contradictions.append({
            "type": "prediction_error",
            "source_event_id": source_event_id,
            "effect": "question_bias_increase_and_share_bias_decrease",
        })

    transition = {
        "transition_id": "",
        "prior_state_ref": state_ref(before),
        "observation": {
            "source_event_id": source_event_id,
            "surprise": float(surprise),
            "prediction_correct": prediction_correct,
        },
        "interpretation": {
            "kind": "bounded_experience_adaptation",
            "agent_id": aid,
            "foundation_model_weights_changed": False,
        },
        "prediction": {
            "content_captured_pre_outcome": False,
            "correctness_result_available": prediction_correct is not None,
            "note": "Upstream v0.3 stores prediction correctness, not the original prediction content.",
        },
        "chosen_action": {
            "type": "apply_bounded_policy_update",
            "policy": "ExperienceLearner.record_experience",
        },
        "actual_outcome": {
            "learning_state": after,
            "prediction_correct": prediction_correct,
            "surprise": float(surprise),
        },
        "verification": verification,
        "contradictions": contradictions,
        "learning_delta": learning_delta,
        "policy_delta": policy_delta,
        "confidence_delta": confidence_delta,
        "provenance": {
            "sources": sources,
            "actor_id": aid,
            "system_id": "signal_society_25:experience_learner",
            "derivation_chain": [
                "Chronos/source event",
                "ExperienceLearner.record_experience",
                "bounded deterministic reducer",
                "learning_history append",
            ],
            "reducer_version": REDUCER_VERSION,
            "contract_name": CONTRACT_NAME,
            "contract_version": CONTRACT_VERSION,
        },
        "timestamp": simulation_timestamp(day, tick),
        "parent_transition_ref": parent,
    }
    transition["transition_id"] = "ET-" + _hash({k: v for k, v in transition.items() if k != "transition_id"})[:28]
    validate_experience_transition(transition)
    return transition


def validate_experience_transition(transition: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_FIELDS if k not in transition]
    if missing:
        raise ValueError(f"ExperienceTransition missing required fields: {missing}")
    if not str(transition["transition_id"]).strip():
        raise ValueError("transition_id is required")
    prior = str(transition["prior_state_ref"])
    if not (prior.startswith("sha256:") and len(prior) == 71):
        raise ValueError("prior_state_ref must be sha256:<64 hex>")
    datetime.fromisoformat(str(transition["timestamp"]))
    verification = transition["verification"]
    if verification.get("status") not in {"verified", "contradicted", "inconclusive", "pending"}:
        raise ValueError("invalid verification.status")
    if verification.get("status") in {"verified", "contradicted"} and not verification.get("evidence_refs"):
        raise ValueError("verified/contradicted transitions require evidence_refs")
    provenance = transition["provenance"]
    if provenance.get("reducer_version") != REDUCER_VERSION:
        raise ValueError("unsupported reducer_version")
    if not provenance.get("sources"):
        raise ValueError("provenance.sources is required")


def prior_state_from_transition(transition: dict[str, Any]) -> dict[str, Any]:
    validate_experience_transition(transition)
    state = {}
    for key, item in transition["learning_delta"].items():
        state[key] = item["before"]
    for key, item in transition["policy_delta"].items():
        state[key] = item["before"]
    return state


def reduce_learning_state(prior_state: dict[str, Any], transition: dict[str, Any]) -> dict[str, Any]:
    validate_experience_transition(transition)
    if state_ref(prior_state) != transition["prior_state_ref"]:
        raise ValueError("prior_state_ref mismatch")
    out = dict(prior_state)
    for group in ("learning_delta", "policy_delta"):
        for key, item in transition[group].items():
            if out.get(key) != item["before"]:
                raise ValueError(f"delta before mismatch for {key}")
            out[key] = item["after"]
    expected = transition["actual_outcome"]["learning_state"]
    if out != expected:
        raise ValueError("deterministic reducer output does not match actual_outcome.learning_state")
    return out


def canonical_transition_rows(db, aid: str) -> list[dict[str, Any]]:
    rows = db.conn.execute(
        "SELECT payload_json FROM learning_history WHERE agent_id=? ORDER BY sequence",
        (aid,),
    ).fetchall()
    out = []
    for (payload_json,) in rows:
        payload = json.loads(payload_json)
        if isinstance(payload, dict) and payload.get("transition_id"):
            out.append(payload)
    return out


def verify_transition_history(db, aid: str, materialized_state: dict[str, Any] | None = None) -> bool:
    rows = canonical_transition_rows(db, aid)
    if not rows:
        return True
    current = prior_state_from_transition(rows[0])
    parent = None
    for transition in rows:
        validate_experience_transition(transition)
        if transition["parent_transition_ref"] != parent:
            return False
        if state_ref(current) != transition["prior_state_ref"]:
            return False
        current = reduce_learning_state(current, transition)
        parent = transition["transition_id"]
    return materialized_state is None or current == materialized_state

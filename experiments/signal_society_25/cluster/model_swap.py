from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Protocol

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def export_canonical_state(sim) -> dict[str, Any]:
    q=sim.db.conn.execute
    def rows(sql):
        return [list(r) for r in q(sql).fetchall()]
    core={
        "day":sim.day,
        "tick":sim.tick,
        "seed_mode":sim.seed_mode,
        "chronos_head":sim.db.chronos_head(),
        "agents":rows("SELECT agent_id,profile_json,self_narrative,learning_version FROM agents ORDER BY agent_id"),
        "beliefs":rows("SELECT agent_id,belief_key,belief_value_json,confidence,source_event_id,tick_updated FROM beliefs ORDER BY agent_id,belief_key"),
        "relationships":rows("SELECT source_agent_id,target_agent_id,trust,familiarity,last_tick FROM relationships ORDER BY source_agent_id,target_agent_id"),
        "questions":rows("SELECT question_id,agent_id,question,status,answer,source_event_id,resolved_event_id,tick_created,tick_resolved FROM questions ORDER BY question_id"),
        "artifacts":rows("SELECT artifact_id,creator_agent_id,medium,content,parent_artifact_id,inherited_json,mutations_json,open_handle,tick_created,canonical,canon_reasons_json FROM artifacts ORDER BY artifact_id"),
        "learning_state":rows("SELECT agent_id,experience_count,prediction_total,prediction_correct,share_bias,question_bias,adaptation_score,last_tick FROM agent_learning_state ORDER BY agent_id"),
    }
    return {**core,"state_sha256":sha256(_canonical(core).encode()).hexdigest()}

class ModelAdapter(Protocol):
    name: str
    def decide(self, canonical_state: dict[str, Any]) -> dict[str, Any]: ...

@dataclass
class AdapterA:
    name: str="deterministic_adapter_a"
    def decide(self, canonical_state: dict[str, Any]) -> dict[str, Any]:
        unresolved=sum(1 for row in canonical_state["questions"] if row[3]=="UNRESOLVED")
        canonical=sum(1 for row in canonical_state["artifacts"] if bool(row[9]))
        if unresolved>canonical:
            action="INQUIRE"
        elif canonical>0:
            action="CONTINUE"
        else:
            action="OBSERVE"
        return {"action":action,"state_sha256":canonical_state["state_sha256"]}

@dataclass
class AdapterB:
    name: str="deterministic_adapter_b"
    def decide(self, canonical_state: dict[str, Any]) -> dict[str, Any]:
        u=0; c=0
        for row in canonical_state.get("questions",()):
            if row[3]=="UNRESOLVED": u+=1
        for row in canonical_state.get("artifacts",()):
            if row[9] in (1,True): c+=1
        action="OBSERVE"
        if c:
            action="CONTINUE"
        if u>c:
            action="INQUIRE"
        return {"action":action,"state_sha256":canonical_state["state_sha256"]}

def cold_swap_check(sim) -> dict[str, Any]:
    state=export_canonical_state(sim)
    a=AdapterA().decide(state)
    b=AdapterB().decide(state)
    return {
        "state_sha256":state["state_sha256"],
        "adapter_a":a,
        "adapter_b":b,
        "decision_equivalence":a["action"]==b["action"],
        "zero_context_boundary":"canonical_state_only",
        "limitation":"Deterministic adapters are not external foundation models.",
    }

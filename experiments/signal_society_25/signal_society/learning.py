from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class Adaptation:
    agent_id: str
    experience_count: int
    prediction_accuracy: float | None
    share_bias: float
    question_bias: float
    adaptation_score: float

class ExperienceLearner:
    """Bounded evidence-driven learner with replayable adaptation history.

    Online adaptation changes explicit policy state, not hidden foundation-model
    weights. Every adaptation is appended to learning_history and may be frozen
    into a versioned experience snapshot.
    """

    def __init__(self, db):
        self.db = db

    def record_experience(
        self,
        aid: str,
        tick: int,
        *,
        day: int = 0,
        prediction_correct: bool | None = None,
        surprise: float = 0.0,
        source_event_id: str | None = None,
    ) -> None:
        row = self.db.conn.execute(
            "SELECT experience_count,prediction_total,prediction_correct,share_bias,question_bias,adaptation_score FROM agent_learning_state WHERE agent_id=?",
            (aid,),
        ).fetchone()
        if row is None:
            self.db.conn.execute("INSERT OR IGNORE INTO agent_learning_state(agent_id) VALUES(?)",(aid,))
            row=(0,0,0,0.0,0.0,0.0)
        exp,total,correct,share,qbias,adapt = row
        before={
            "experience_count":int(exp),"prediction_total":int(total),
            "prediction_correct":int(correct),"share_bias":float(share),
            "question_bias":float(qbias),"adaptation_score":float(adapt),
        }
        exp += 1
        surprise=max(0.0,min(1.0,float(surprise)))
        if prediction_correct is not None:
            total += 1
            correct += int(prediction_correct)
            if prediction_correct:
                share=max(-0.25,min(0.25,share+0.01))
                qbias=max(-0.25,min(0.35,qbias-0.003))
                error=0.0
            else:
                share=max(-0.25,min(0.25,share-0.015))
                qbias=max(-0.25,min(0.35,qbias+0.025))
                error=1.0
            adapt=min(1.0,adapt*0.97+0.03*((error+surprise)/2.0))
        else:
            adapt=min(1.0,adapt*0.995+0.005*surprise)
        after={
            "experience_count":int(exp),"prediction_total":int(total),
            "prediction_correct":int(correct),"share_bias":float(share),
            "question_bias":float(qbias),"adaptation_score":float(adapt),
        }
        self.db.conn.execute(
            "UPDATE agent_learning_state SET experience_count=?,prediction_total=?,prediction_correct=?,share_bias=?,question_bias=?,adaptation_score=?,last_tick=? WHERE agent_id=?",
            (exp,total,correct,share,qbias,adapt,tick,aid),
        )
        payload={
            "before":before,"after":after,"prediction_correct":prediction_correct,
            "surprise":surprise,
        }
        self.db.append_learning_history(aid,tick,day,payload,source_event_id)
        self.db.event(tick,day,"learning.adapted",aid,None,{
            "source_event_id":source_event_id,
            "after":after,
            "prediction_correct":prediction_correct,
            "surprise":surprise,
        })

    def state(self, aid: str) -> Adaptation:
        exp,total,correct,share,qbias,adapt = self.db.conn.execute(
            "SELECT experience_count,prediction_total,prediction_correct,share_bias,question_bias,adaptation_score FROM agent_learning_state WHERE agent_id=?",
            (aid,),
        ).fetchone()
        accuracy=(correct/total) if total else None
        return Adaptation(aid,exp,accuracy,share,qbias,adapt)

    def replay_state(self, aid: str) -> Adaptation:
        row=self.db.conn.execute(
            "SELECT payload_json FROM learning_history WHERE agent_id=? ORDER BY sequence DESC LIMIT 1",
            (aid,),
        ).fetchone()
        if not row:
            return Adaptation(aid,0,None,0.0,0.0,0.0)
        after=json.loads(row[0])["after"]
        total=int(after["prediction_total"]); correct=int(after["prediction_correct"])
        return Adaptation(
            aid,int(after["experience_count"]),
            (correct/total) if total else None,
            float(after["share_bias"]),float(after["question_bias"]),
            float(after["adaptation_score"]),
        )

    def replay_matches_materialized(self, aid: str) -> bool:
        return self.replay_state(aid) == self.state(aid)

    def snapshot(self, aid: str, tick: int, day: int) -> dict[str, Any]:
        state=asdict(self.state(aid))
        return self.db.experience_snapshot(aid,tick,day,state)

    def bootstrap(self, agent_ids, tick: int, day: int) -> dict[str, Any]:
        out={}
        for aid in sorted(agent_ids):
            out[aid]=self.snapshot(aid,tick,day)
        self.db.conn.commit()
        return out

    @staticmethod
    def _tokens(text: str):
        out=set()
        for raw in text.split():
            w=raw.lower().strip(".,!?;:'\"()[]")
            if len(w)<=2:
                continue
            aliases={"found":"find","finding":"find","told":"tell","heard":"hear","created":"create","carried":"carry"}
            w=aliases.get(w,w)
            if w.endswith("ing") and len(w)>5:
                w=w[:-3]
            elif w.endswith("ed") and len(w)>4:
                w=w[:-2]
            out.add(w)
        return out

    def help(self, aid: str, question: str, limit: int = 5) -> dict[str, Any]:
        terms=self._tokens(question)
        scored=[]
        for mt,content,eid,confidence,tick in self.db.conn.execute(
            "SELECT memory_type,content,source_event_id,confidence,tick_created FROM memories WHERE agent_id=? ORDER BY tick_created DESC",
            (aid,),
        ):
            words=self._tokens(content)
            overlap=len(terms & words)
            if overlap:
                scored.append((overlap*confidence,tick,mt,content,eid,confidence))
        scored.sort(reverse=True)
        evidence=[
            {"memory_type":r[2],"content":r[3],"source_event_id":r[4],"confidence":r[5],"tick":r[1]}
            for r in scored[:limit]
        ]
        unresolved=self.db.conn.execute(
            "SELECT question FROM questions WHERE agent_id=? AND status='UNRESOLVED' ORDER BY tick_created LIMIT 1",
            (aid,),
        ).fetchone()
        state=self.state(aid)
        return {
            "agent_id": aid,
            "question": question,
            "answer": evidence[0]["content"] if evidence else "UNKNOWN_FROM_AGENT_MEMORY",
            "evidence": evidence,
            "next_question": unresolved[0] if unresolved else None,
            "learning_state": {
                "experience_count": state.experience_count,
                "prediction_accuracy": state.prediction_accuracy,
                "share_bias": state.share_bias,
                "question_bias": state.question_bias,
                "adaptation_score": state.adaptation_score,
                "replay_matches_materialized": self.replay_matches_materialized(aid),
            },
        }

    def co_create(self, aid: str, parent_artifact_id: str) -> dict[str, Any]:
        row=self.db.conn.execute(
            "SELECT medium,content,inherited_json,open_handle,canonical FROM artifacts WHERE artifact_id=?",
            (parent_artifact_id,),
        ).fetchone()
        if not row:
            return {"status":"UNKNOWN_PARENT","agent_id":aid,"parent_artifact_id":parent_artifact_id}
        medium,content,inherited_json,open_handle,canonical=row
        inherited=json.loads(inherited_json or "[]")
        state=self.state(aid)
        if state.question_bias>0.08:
            mutation="interrogate_assumption"
        elif state.share_bias>0.08:
            mutation="change_medium_for_transmission"
        else:
            mutation="change_perspective"
        return {
            "status":"READY",
            "agent_id":aid,
            "parent_artifact_id":parent_artifact_id,
            "parent_canonical":bool(canonical),
            "carry_forward":inherited,
            "change":mutation,
            "leave_unfinished":open_handle or "Expose one unresolved question.",
            "parent_evidence":{"medium":medium,"content":content},
            "learning_state":asdict(state),
        }

    def copilot(self, aid: str, objective: str, parent_artifact_id: str | None = None) -> dict[str, Any]:
        result={"help":self.help(aid,objective)}
        if parent_artifact_id:
            result["co_create"]=self.co_create(aid,parent_artifact_id)
        return result

from __future__ import annotations

from dataclasses import dataclass
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
    """Bounded evidence-driven online learner.

    It adapts explicit policy state from verified outcomes; it does not mutate
    foundation-model weights or turn generated beliefs into truth.
    """

    def __init__(self, db):
        self.db = db

    def record_experience(
        self,
        aid: str,
        tick: int,
        *,
        prediction_correct: bool | None = None,
        surprise: float = 0.0,
    ) -> None:
        row = self.db.conn.execute(
            "SELECT experience_count,prediction_total,prediction_correct,share_bias,question_bias,adaptation_score FROM agent_learning_state WHERE agent_id=?",
            (aid,),
        ).fetchone()
        exp,total,correct,share,qbias,adapt = row
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
        self.db.conn.execute(
            "UPDATE agent_learning_state SET experience_count=?,prediction_total=?,prediction_correct=?,share_bias=?,question_bias=?,adaptation_score=?,last_tick=? WHERE agent_id=?",
            (exp,total,correct,share,qbias,adapt,tick,aid),
        )

    def state(self, aid: str) -> Adaptation:
        exp,total,correct,share,qbias,adapt = self.db.conn.execute(
            "SELECT experience_count,prediction_total,prediction_correct,share_bias,question_bias,adaptation_score FROM agent_learning_state WHERE agent_id=?",
            (aid,),
        ).fetchone()
        accuracy=(correct/total) if total else None
        return Adaptation(aid,exp,accuracy,share,qbias,adapt)

    def help(self, aid: str, question: str, limit: int = 5) -> dict[str, Any]:
        terms={x.lower().strip(".,!?;:'\"") for x in question.split() if len(x)>2}
        scored=[]
        for mt,content,eid,confidence,tick in self.db.conn.execute(
            "SELECT memory_type,content,source_event_id,confidence,tick_created FROM memories WHERE agent_id=? ORDER BY tick_created DESC",
            (aid,),
        ):
            words={x.lower().strip(".,!?;:'\"") for x in content.split()}
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
                "adaptation_score": state.adaptation_score,
            },
        }

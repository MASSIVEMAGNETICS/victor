from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    severity: str
    detail: Any

class VictorOmniSentinel:
    """Evidence-first supervisor for Signal Society.

    Sentinel does not decide truth by authority. It executes explicit integrity
    checks and reports the evidence inspected.
    """

    REQUIRED_APPEND_ONLY={
        "events","informatrons","memories","artifacts","learning_examples",
        "version_history","learning_history","experience_snapshots",
    }

    def __init__(self, sim):
        self.sim=sim
        self.db=sim.db

    def _append_only_guard_check(self) -> Check:
        rows=self.db.conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name").fetchall()
        names={r[0] for r in rows}
        missing=[]
        for table in sorted(self.REQUIRED_APPEND_ONLY):
            if f"{table}_no_update" not in names or f"{table}_no_delete" not in names:
                missing.append(table)
        return Check("append_only_guards",not missing,"hard",{"missing":missing,"trigger_count":len(names)})

    def _speaker_integrity(self) -> Check:
        failures=[]
        rows=self.db.conn.execute(
            "SELECT event_id,tick,actor_id,payload_json FROM events WHERE event_type='social.group_dialogue' ORDER BY sequence"
        ).fetchall()
        checked=0
        for eid,tick,actor,payload_json in rows:
            payload=json.loads(payload_json)
            art=payload.get("artifact_id")
            if not art:
                continue
            checked+=1
            seen=self.db.conn.execute(
                "SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id=? AND first_tick<=?",
                (actor,art,tick),
            ).fetchone()
            if not seen:
                failures.append({"event_id":eid,"speaker":actor,"artifact_id":art,"tick":tick})
        return Check("epistemic_speaker_integrity",not failures,"hard",{"checked":checked,"failures":failures[:20]})

    def _lineage_integrity(self) -> Check:
        missing=[]
        rows=self.db.conn.execute(
            "SELECT artifact_id,parent_artifact_id FROM artifacts WHERE parent_artifact_id IS NOT NULL ORDER BY artifact_id"
        ).fetchall()
        for child,parent in rows:
            if not self.db.conn.execute("SELECT 1 FROM artifacts WHERE artifact_id=?",(parent,)).fetchone():
                missing.append({"child":child,"missing_parent":parent})
        return Check("lineage_parent_integrity",not missing,"hard",{"descendants":len(rows),"missing":missing[:20]})

    def _canon_health(self) -> Check:
        canonical=self.db.conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL AND canonical=1"
        ).fetchone()[0]
        noncanonical=self.db.conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL AND canonical=0"
        ).fetchone()[0]
        total=canonical+noncanonical
        ratio=(canonical/total) if total else None
        return Check("canon_observability",True,"info",{"canonical":canonical,"noncanonical":noncanonical,"ratio":ratio})

    def _learning_replay(self) -> Check:
        mismatches=[aid for aid in sorted(self.sim.agents) if not self.sim.learn.replay_matches_materialized(aid)]
        return Check("learning_replay",not mismatches,"hard",{"mismatched_agents":mismatches})

    def _audio_contract(self) -> Check:
        bad_hash=[]; physical=0; logical=0
        rows=self.db.conn.execute(
            "SELECT audio_id,transcript,source_path,sha256 FROM audio_segments ORDER BY audio_id"
        ).fetchall()
        for aid,transcript,path,digest in rows:
            actual=sha256((transcript or "").encode()).hexdigest()
            if actual!=digest:
                bad_hash.append(aid)
            if path:
                physical+=1
            else:
                logical+=1
        return Check("audio_evidence_contract",not bad_hash,"hard",{
            "segments":len(rows),"bad_hashes":bad_hash[:20],
            "physical_audio_segments":physical,
            "transcript_only_segments":logical,
            "physical_audio_complete":logical==0 and len(rows)>0,
        })

    def _question_health(self) -> Check:
        generated=self.db.conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        resolved=self.db.conn.execute("SELECT COUNT(*) FROM questions WHERE status='RESOLVED'").fetchone()[0]
        ratio=(resolved/generated) if generated else None
        return Check("question_resolution",True,"info",{"generated":generated,"resolved":resolved,"ratio":ratio})

    def scan(self) -> dict[str, Any]:
        checks=[
            Check("chronos_chain",self.db.verify_chronos(),"hard",{"head":self.db.chronos_head()}),
            Check("learning_history_chain",self.db.verify_learning_history(),"hard",{}),
            Check("experience_snapshot_chain",self.db.verify_experience_snapshots(),"hard",{}),
            self._append_only_guard_check(),
            self._speaker_integrity(),
            self._lineage_integrity(),
            self._learning_replay(),
            self._audio_contract(),
            self._canon_health(),
            self._question_health(),
        ]
        hard_failures=[c.name for c in checks if c.severity=="hard" and not c.passed]
        amber=[]
        audio=next(c for c in checks if c.name=="audio_evidence_contract")
        if audio.passed and audio.detail["transcript_only_segments"]>0:
            amber.append("physical_audio_not_rendered")
        if hard_failures:
            status="RED"
        elif amber:
            status="AMBER"
        else:
            status="GREEN"
        core={
            "sentinel":"Victor Omni Sentinel",
            "status":status,
            "hard_failures":hard_failures,
            "advisories":amber,
            "checks":[asdict(c) for c in checks],
        }
        return {**core,"report_sha256":sha256(_canonical(core).encode()).hexdigest()}

    def deployment_gate(self) -> dict[str, Any]:
        report=self.scan()
        return {
            "deployable":report["status"] in {"GREEN","AMBER"} and not report["hard_failures"],
            "status":report["status"],
            "report_sha256":report["report_sha256"],
            "hard_failures":report["hard_failures"],
            "advisories":report["advisories"],
        }

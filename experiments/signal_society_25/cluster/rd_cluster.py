from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Any

from signal_society import SignalSociety25

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

@dataclass(frozen=True)
class ResearchArm:
    name: str
    seed_mode: str
    seed: int
    days: int
    interactions_per_day: int
    groups_per_day: int

class RecursiveRDCluster:
    """Bounded recursive R&D loop over controlled synthetic-society arms."""

    def __init__(self, output_dir: str | Path, seed: int = 25):
        self.output_dir=Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seed=int(seed)
        self.history_path=self.output_dir/"rd_history.jsonl"

    def _run_arm(self, arm: ResearchArm) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            sim=SignalSociety25(Path(td)/f"{arm.name}.db", arm.seed, arm.seed_mode)
            try:
                metrics=sim.run(
                    days=arm.days,
                    interactions_per_day=arm.interactions_per_day,
                    groups_per_day=arm.groups_per_day,
                    introduce_day=min(3, arm.days),
                )
                metrics["learning_replay_all"]=all(
                    sim.learn.replay_matches_materialized(aid) for aid in sorted(sim.agents)
                )
                metrics["learning_history_valid"]=sim.db.verify_learning_history()
                metrics["experience_snapshots_valid"]=sim.db.verify_experience_snapshots()
                return metrics
            finally:
                sim.db.close()

    def _append_history(self, row: dict[str, Any]) -> dict[str, Any]:
        if not self.verify_history():
            raise ValueError("R&D receipt chain is invalid")
        previous="GENESIS"; seq=0
        if self.history_path.exists():
            for line in self.history_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    old=json.loads(line); seq=int(old["sequence"]); previous=old["receipt_hash"]
        core={"sequence":seq+1, **row, "previous_receipt_hash":previous}
        digest=sha256(_canonical(core).encode()).hexdigest()
        out={**core, "receipt_hash":digest}
        with self.history_path.open("a",encoding="utf-8") as f:
            f.write(_canonical(out)+"\n")
        return out

    def verify_history(self) -> bool:
        if not self.history_path.exists():
            return True
        prev="GENESIS"; expected=1
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            core={k:v for k,v in row.items() if k!="receipt_hash"}
            actual=sha256(_canonical(core).encode()).hexdigest()
            if row["sequence"]!=expected or row["previous_receipt_hash"]!=prev or row["receipt_hash"]!=actual:
                return False
            prev=row["receipt_hash"]; expected+=1
        return True

    @staticmethod
    def _score(metrics: dict[str, Any]) -> float:
        aware=float(metrics.get("agents_with_artifact_awareness",0))/25.0
        canonical=float(metrics.get("canonical_descendants",0))
        noncanonical=float(metrics.get("noncanonical_descendants",0))
        canon_ratio=canonical/max(1.0,canonical+noncanonical)
        q=float(metrics.get("questions_resolved",0))/max(1.0,float(metrics.get("questions_generated",0)))
        pred=metrics.get("prediction_accuracy")
        pred=float(pred) if pred is not None else 0.0
        integrity=1.0 if metrics.get("chronos_valid") and metrics.get("learning_history_valid") else 0.0
        return round((aware+canon_ratio+q+pred+integrity)/5.0,6)

    def run(self, cycles: int = 3, days: int = 4, interactions_per_day: int = 10) -> dict[str, Any]:
        cycles=max(1,min(int(cycles),12))
        days=max(1,min(int(days),30))
        density=max(2,min(int(interactions_per_day),100))
        cycle_reports=[]
        for cycle in range(1,cycles+1):
            arms=(
                ResearchArm("signal","signal",self.seed+cycle-1,days,density,1),
                ResearchArm("neutral","neutral",self.seed+cycle-1,days,density,1),
                ResearchArm("no_seed","none",self.seed+cycle-1,days,density,1),
            )
            results={arm.name:self._run_arm(arm) for arm in arms}
            scores={name:self._score(m) for name,m in results.items()}
            signal=results["signal"]
            if not signal.get("chronos_valid") or not signal.get("learning_history_valid"):
                next_density=density
                focus="integrity_failure_stop_escalation"
            elif signal.get("questions_resolved",0) < max(1,signal.get("questions_generated",0)//4):
                next_density=min(100,density+2)
                focus="increase_social_evidence_opportunities"
            elif signal.get("prediction_accuracy") is not None and signal["prediction_accuracy"] < 0.6:
                next_density=min(100,density+1)
                focus="collect_more_prediction_outcomes"
            else:
                next_density=max(2,density-1)
                focus="reduce_density_test_persistence"
            report={
                "cycle":cycle,
                "configuration":{"days":days,"interactions_per_day":density,"seed":self.seed+cycle-1},
                "results":results,
                "scores":scores,
                "next_cycle":{"interactions_per_day":next_density,"focus":focus},
            }
            self._append_history({"kind":"rd.cycle","cycle":cycle,"report":report})
            cycle_reports.append(report)
            density=next_density
        summary={
            "cycles":cycles,
            "history_valid":self.verify_history(),
            "cycle_reports":cycle_reports,
            "last_focus":cycle_reports[-1]["next_cycle"]["focus"],
        }
        (self.output_dir/"rd_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
        return summary

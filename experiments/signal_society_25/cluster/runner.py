from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any

from signal_society import SignalSociety25
from .model_swap import cold_swap_check, export_canonical_state
from .phylogeny import phylogeny_metrics
from .rd_cluster import RecursiveRDCluster
from .release_train import RELEASES, PACKAGE_VERSION, ReleaseReceiptLedger, manifest
from .sentinel import VictorOmniSentinel

def _write(path: Path, value: Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True),encoding="utf-8")

def _fresh_db(path: Path):
    for suffix in ("","-wal","-shm"):
        p=Path(str(path)+suffix)
        if p.exists():
            p.unlink()

def run_cluster(
    output_dir: str | Path,
    *,
    seed: int=25,
    days: int=5,
    interactions_per_day: int=12,
    cycles: int=2,
    fresh: bool=False,
) -> dict[str, Any]:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    db=out/"signal_society_25.db"
    if fresh:
        _fresh_db(db)
        for stale in ("release_receipts.jsonl","deployment_manifest.json","release_manifest.json","sentinel_report.json"):
            p=out/stale
            if p.exists():
                p.unlink()
        research=out/"research"
        if research.exists():
            shutil.rmtree(research)
    receipts=ReleaseReceiptLedger(out/"release_receipts.jsonl")
    sim=SignalSociety25(db,seed,"signal")
    stage_results={}
    try:
        base_metrics=sim.run(days=days,interactions_per_day=interactions_per_day,groups_per_day=1)
        sim.learn.bootstrap(sorted(sim.agents),sim.tick,sim.day)
        sim.db.conn.commit()

        rd=RecursiveRDCluster(out/"research",seed)
        rd_result=rd.run(cycles=cycles,days=max(2,min(4,days)),interactions_per_day=max(4,min(12,interactions_per_day)))
        s040={
            "controls_present":all(k in rd_result["cycle_reports"][0]["results"] for k in ("signal","neutral","no_seed")),
            "deterministic_replay":rd_result["history_valid"],
            "research_receipt_chain":rd.verify_history(),
            "cycles":rd_result["cycles"],
            "last_focus":rd_result["last_focus"],
        }
        s040["passed"]=all(s040[k] for k in ("controls_present","deterministic_replay","research_receipt_chain"))
        stage_results["0.4.0"]=s040

        replay=all(sim.learn.replay_matches_materialized(aid) for aid in sorted(sim.agents))
        s050={
            "learning_history_valid":sim.db.verify_learning_history(),
            "replay_matches_materialized":replay,
            "experience_snapshots_valid":sim.db.verify_experience_snapshots(),
            "snapshot_count":sim.db.conn.execute("SELECT COUNT(*) FROM experience_snapshots").fetchone()[0],
        }
        s050["passed"]=all(s050[k] for k in ("learning_history_valid","replay_matches_materialized","experience_snapshots_valid"))
        stage_results["0.5.0"]=s050

        phy=phylogeny_metrics(sim)
        lineage_ok=VictorOmniSentinel(sim)._lineage_integrity().passed
        canon_rows=sim.db.conn.execute("SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL").fetchone()[0]
        s060={
            "canon_verifier_active":canon_rows==0 or (phy["canonical_descendants"]+phy["noncanonical_descendants"]==canon_rows),
            "lineage_parent_integrity":lineage_ok,
            "phylogeny_metrics":phy,
        }
        s060["passed"]=s060["canon_verifier_active"] and s060["lineage_parent_integrity"]
        stage_results["0.6.0"]=s060

        swap=cold_swap_check(sim)
        state=export_canonical_state(sim)
        s070={
            "canonical_state_export":bool(state.get("state_sha256")),
            "adapter_zero_context":swap["zero_context_boundary"]=="canonical_state_only",
            "decision_equivalence":swap["decision_equivalence"],
            "swap":swap,
        }
        s070["passed"]=all(s070[k] for k in ("canonical_state_export","adapter_zero_context","decision_equivalence"))
        stage_results["0.7.0"]=s070

        sentinel=VictorOmniSentinel(sim)
        sentinel_report=sentinel.scan()
        audio_check=next(x for x in sentinel_report["checks"] if x["name"]=="audio_evidence_contract")
        s080={
            "transcript_hash_valid":audio_check["passed"],
            "audio_evidence_status_explicit":(
                "physical_audio_segments" in audio_check["detail"] and
                "transcript_only_segments" in audio_check["detail"]
            ),
            "roundtrip_contract":"future_tts_stt_gate",
            "audio":audio_check["detail"],
        }
        s080["passed"]=s080["transcript_hash_valid"] and s080["audio_evidence_status_explicit"]
        stage_results["0.8.0"]=s080

        sentinel_gate=sentinel.deployment_gate()
        s090={
            "sentinel_green_or_explained":sentinel_gate["status"] in {"GREEN","AMBER"},
            "append_only_guards":next(x for x in sentinel_report["checks"] if x["name"]=="append_only_guards")["passed"],
            "no_silent_integrity_failure":not sentinel_gate["hard_failures"],
            "sentinel":sentinel_report,
        }
        s090["passed"]=all(s090[k] for k in ("sentinel_green_or_explained","append_only_guards","no_silent_integrity_failure"))
        stage_results["0.9.0"]=s090

        prior_pass=all(stage_results[v]["passed"] for v in ("0.4.0","0.5.0","0.6.0","0.7.0","0.8.0","0.9.0"))
        package_manifest=manifest()
        service_health={
            "route":"/health",
            "expected_status":200 if sentinel_gate["deployable"] else 503,
            "deployable":sentinel_gate["deployable"],
        }
        s100={
            "all_prior_gates_pass":prior_pass,
            "service_health":service_health,
            "artifact_manifest":bool(package_manifest["manifest_sha256"]),
            "container_build":"external_ci_gate",
        }
        s100["passed"]=prior_pass and sentinel_gate["deployable"] and s100["artifact_manifest"]
        stage_results["1.0.0"]=s100

        for stage in RELEASES:
            r=stage_results[stage.version]
            receipts.append(stage.version,"PASS" if r["passed"] else "FAIL",r)
            if r["passed"]:
                sim.db._version(stage.version,[stage.codename,stage.purpose,*stage.capabilities])
        sim.db.set_meta("release_cluster_version",PACKAGE_VERSION)
        sim.db.set_meta("release_cluster_receipts_valid",str(receipts.verify()).lower())
        sim.db.conn.commit()

        deployment={
            "package":"signal-society-25-release-cluster",
            "package_version":PACKAGE_VERSION,
            "deployable":stage_results["1.0.0"]["passed"] and receipts.verify(),
            "base_metrics":base_metrics,
            "release_manifest":package_manifest,
            "release_results":stage_results,
            "release_receipt_chain_valid":receipts.verify(),
            "sentinel_status":sentinel_gate["status"],
            "sentinel_report_sha256":sentinel_gate["report_sha256"],
            "canonical_state_sha256":state["state_sha256"],
        }
        digest_core=json.dumps(deployment,sort_keys=True,separators=(",",":"))
        deployment["deployment_sha256"]=sha256(digest_core.encode()).hexdigest()
        _write(out/"sentinel_report.json",sentinel_report)
        _write(out/"release_manifest.json",package_manifest)
        _write(out/"deployment_manifest.json",deployment)
        return deployment
    finally:
        sim.db.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default="deployment")
    p.add_argument("--seed",type=int,default=25)
    p.add_argument("--days",type=int,default=5)
    p.add_argument("--interactions-per-day",type=int,default=12)
    p.add_argument("--cycles",type=int,default=2)
    p.add_argument("--fresh",action="store_true")
    p.add_argument("--strict",action="store_true")
    a=p.parse_args()
    result=run_cluster(
        a.output_dir,seed=a.seed,days=a.days,
        interactions_per_day=a.interactions_per_day,
        cycles=a.cycles,fresh=a.fresh,
    )
    print(json.dumps(result,indent=2,sort_keys=True))
    if a.strict and not result["deployable"]:
        raise SystemExit(2)

if __name__=="__main__":
    main()

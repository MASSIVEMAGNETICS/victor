from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "1.0.0"

@dataclass(frozen=True)
class ReleaseStage:
    version: str
    codename: str
    purpose: str
    gates: tuple[str, ...]
    capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

RELEASES: tuple[ReleaseStage, ...] = (
    ReleaseStage(
        "0.4.0", "Recursive R&D Cluster",
        "Run controlled multi-arm synthetic-society experiments and recursively adapt the next research cycle from measured results.",
        ("controls_present", "deterministic_replay", "research_receipt_chain"),
        ("multi_arm_experiments", "recursive_hypothesis_loop", "cluster_reports"),
    ),
    ReleaseStage(
        "0.5.0", "Experience Ecology",
        "Measure population learning, preserve agent-specific experience state, and expose divergence rather than collapsing agents into one memory.",
        ("learning_history_valid", "replay_matches_materialized", "experience_snapshots_valid"),
        ("experience_population_metrics", "agent_snapshot_lineage", "bounded_policy_adaptation"),
    ),
    ReleaseStage(
        "0.6.0", "Cultural Phylogeny",
        "Treat cultural descendants as a graph with measurable lineage depth, branching, canon compatibility and extinction.",
        ("canon_verifier_active", "lineage_parent_integrity", "phylogeny_metrics"),
        ("lineage_depth", "branching_factor", "canon_ratio", "extinct_branch_count"),
    ),
    ReleaseStage(
        "0.7.0", "Cold-Swap Continuity",
        "Prove that a cognition adapter can be replaced after canonical state reconstruction without using the predecessor adapter's hidden context.",
        ("canonical_state_export", "adapter_zero_context", "decision_equivalence"),
        ("model_adapter_protocol", "deterministic_adapter_a", "deterministic_adapter_b", "cold_swap_harness"),
    ),
    ReleaseStage(
        "0.8.0", "Multimodal Evidence Contract",
        "Validate the dialogue/audio evidence boundary and make missing physical audio explicit rather than silently pretending transcripts are audio.",
        ("transcript_hash_valid", "audio_evidence_status_explicit", "roundtrip_contract"),
        ("audio_contract_audit", "transcript_integrity", "future_tts_stt_gate"),
    ),
    ReleaseStage(
        "0.9.0", "Victor Omni Sentinel",
        "Continuously audit continuity, epistemic integrity, lineage validity, learning replay and deployment readiness without becoming an authority over evidence.",
        ("sentinel_green_or_explained", "append_only_guards", "no_silent_integrity_failure"),
        ("omni_sentinel", "health_report", "release_gate", "evidence_receipts"),
    ),
    ReleaseStage(
        "1.0.0", "Cluster Deployment",
        "Ship the seven-stage release train as one reproducible package with service endpoints, container packaging and machine-readable deployment receipts.",
        ("all_prior_gates_pass", "service_health", "container_build", "artifact_manifest"),
        ("http_service", "docker_package", "ci_deployment_bundle", "release_manifest"),
    ),
)

def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def manifest() -> dict[str, Any]:
    stages=[stage.as_dict() for stage in RELEASES]
    core={"package":"signal-society-25-release-cluster","package_version":PACKAGE_VERSION,"releases":stages}
    return {**core, "manifest_sha256":sha256(_canonical(core).encode()).hexdigest()}

class ReleaseReceiptLedger:
    """Append-only JSONL receipt chain for release-gate execution."""

    def __init__(self, path: str | Path):
        self.path=Path(path)

    def _last(self) -> tuple[int, str]:
        if not self.path.exists() or not self.path.stat().st_size:
            return 0, "GENESIS"
        last=None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last=json.loads(line)
        if last is None:
            return 0, "GENESIS"
        return int(last["sequence"]), str(last["receipt_hash"])

    def append(self, version: str, status: str, evidence: dict[str, Any]) -> dict[str, Any]:
        if not self.verify():
            raise ValueError("release receipt chain is invalid")
        seq, previous=self._last()
        core={
            "sequence":seq+1,
            "version":version,
            "status":status,
            "evidence":evidence,
            "previous_receipt_hash":previous,
        }
        receipt_hash=sha256(_canonical(core).encode()).hexdigest()
        row={**core, "receipt_hash":receipt_hash}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(_canonical(row)+"\n")
        return row

    def verify(self) -> bool:
        previous="GENESIS"; expected=1
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            core={k:row[k] for k in ("sequence","version","status","evidence","previous_receipt_hash")}
            actual=sha256(_canonical(core).encode()).hexdigest()
            if row["sequence"]!=expected or row["previous_receipt_hash"]!=previous or row["receipt_hash"]!=actual:
                return False
            previous=row["receipt_hash"]; expected+=1
        return True

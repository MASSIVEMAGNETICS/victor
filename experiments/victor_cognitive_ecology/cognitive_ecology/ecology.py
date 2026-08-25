from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Mapping


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 2}


@dataclass(frozen=True)
class Budget:
    max_processes: int = 16
    max_depth: int = 3
    max_cost: float = 12.0
    spawn_threshold: float = 0.75

    def __post_init__(self) -> None:
        if self.max_processes < 1:
            raise ValueError("max_processes must be >= 1")
        if self.max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if self.max_cost <= 0:
            raise ValueError("max_cost must be > 0")
        if self.spawn_threshold <= 0:
            raise ValueError("spawn_threshold must be > 0")


@dataclass(frozen=True)
class SpawnRequest:
    process_kind: str
    question: str
    expected_value: float
    estimated_cost: float = 1.0
    rationale: str = ""

    @property
    def utility_ratio(self) -> float:
        return max(0.0, self.expected_value) / max(1e-9, self.estimated_cost)


@dataclass(frozen=True)
class CognitiveTask:
    task_id: str
    process_kind: str
    question: str
    context: Mapping[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
    depth: int = 0
    estimated_cost: float = 1.0


@dataclass(frozen=True)
class CognitiveResult:
    task_id: str
    process_kind: str
    answer: str
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    spawn_requests: tuple[SpawnRequest, ...] = ()
    proposed_action: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _clamp(self.confidence, 0.0, 1.0))


@dataclass
class ProcessStats:
    runs: int = 0
    reward_sum: float = 0.0
    weight: float = 1.0
    useful_runs: int = 0
    distinct_problem_families: set[str] = field(default_factory=set)

    @property
    def mean_reward(self) -> float:
        return self.reward_sum / self.runs if self.runs else 0.0


@dataclass(frozen=True)
class AetherlingPromotionProposal:
    process_kind: str
    eligible: bool
    score: float
    reasons: tuple[str, ...]
    suggested_dna: Mapping[str, Any]


@dataclass(frozen=True)
class GEVObservation:
    observation_id: str
    features: Mapping[str, Any]
    changes: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    confidence: float = 1.0
    provenance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", _clamp(self.confidence, 0.0, 1.0))


Worker = Callable[[CognitiveTask], CognitiveResult]


class CognitiveEcology:
    """Bounded cognitive-process ecology for Victor.

    The ecology may learn routing weights and approve bounded recursive thought
    spawning. It never grants tools, persistence, external authority, or
    Aetherling identity. Promotion is emitted only as a proposal for the
    existing governed identity/authority path.
    """

    LEDGER_VERSION = "victor.cognitive_ecology.ledger.v1"

    def __init__(
        self,
        ledger_path: str | Path,
        *,
        budget: Budget | None = None,
        learning_rate: float = 0.30,
        min_weight: float = 0.20,
        max_weight: float = 3.00,
        resonance_threshold: float = 0.45,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.budget = budget or Budget()
        self.learning_rate = _clamp(learning_rate, 0.01, 1.0)
        self.min_weight = float(min_weight)
        self.max_weight = float(max_weight)
        if self.min_weight <= 0 or self.max_weight < self.min_weight:
            raise ValueError("invalid routing weight bounds")
        self.resonance_threshold = _clamp(resonance_threshold, 0.0, 1.0)
        self._workers: dict[str, Worker] = {}
        self._stats: dict[str, ProcessStats] = {}
        self._replay_ledger()

    def register(self, process_kind: str, worker: Worker) -> None:
        kind = process_kind.strip()
        if not kind:
            raise ValueError("process_kind is required")
        if not callable(worker):
            raise TypeError("worker must be callable")
        self._workers[kind] = worker
        self._stats.setdefault(kind, ProcessStats())

    @property
    def stats(self) -> Mapping[str, ProcessStats]:
        return self._stats

    def routing_weight(self, process_kind: str) -> float:
        return self._stats.get(process_kind, ProcessStats()).weight

    def verify_ledger(self) -> bool:
        if not self.ledger_path.exists():
            return True
        previous = "GENESIS"
        sequence = 1
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                return False
            receipt_hash = row.pop("receipt_hash", None)
            if row.get("sequence") != sequence:
                return False
            if row.get("previous_receipt_hash") != previous:
                return False
            if row.get("ledger_version") != self.LEDGER_VERSION:
                return False
            if receipt_hash != _digest(row):
                return False
            previous = receipt_hash
            sequence += 1
        return True

    def _append(self, kind: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self.verify_ledger():
            raise ValueError("cognitive ecology ledger failed verification")
        previous = "GENESIS"
        sequence = 0
        if self.ledger_path.exists():
            for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    sequence = int(row["sequence"])
                    previous = str(row["receipt_hash"])
        core = {
            "sequence": sequence + 1,
            "ledger_version": self.LEDGER_VERSION,
            "kind": kind,
            "payload": dict(payload),
            "previous_receipt_hash": previous,
        }
        row = {**core, "receipt_hash": _digest(core)}
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical(row) + "\n")
        return row

    def _replay_ledger(self) -> None:
        if not self.verify_ledger():
            raise ValueError("cannot replay invalid cognitive ecology ledger")
        if not self.ledger_path.exists():
            return
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") != "process.outcome":
                continue
            payload = row["payload"]
            self._apply_learning(
                process_kind=str(payload["process_kind"]),
                reward=float(payload["reward"]),
                problem_family=str(payload.get("problem_family", "unknown")),
                persist=False,
            )

    def route(self, candidate_kinds: Iterable[str], *, limit: int = 4) -> list[str]:
        registered = [k for k in dict.fromkeys(candidate_kinds) if k in self._workers]
        registered.sort(key=lambda k: (-self.routing_weight(k), k))
        return registered[: max(1, int(limit))]

    def tasks_from_gev(
        self,
        observation: GEVObservation,
        *,
        candidate_kinds: Iterable[str] = ("causal", "temporal", "adversarial", "novelty"),
        limit: int = 4,
    ) -> list[CognitiveTask]:
        base_context = {
            "source": "Victor-GEV",
            "observation_id": observation.observation_id,
            "features": dict(observation.features),
            "changes": list(observation.changes),
            "unknowns": list(observation.unknowns),
            "confidence": observation.confidence,
            "provenance_refs": list(observation.provenance_refs),
        }
        tasks = []
        for kind in self.route(candidate_kinds, limit=limit):
            question = self._gev_question(kind, observation)
            task_id = "CT-" + _digest({"obs": observation.observation_id, "kind": kind, "q": question})[:20]
            tasks.append(CognitiveTask(task_id, kind, question, base_context, depth=0, estimated_cost=1.0))
        self._append(
            "gev.dispatch",
            {
                "observation_id": observation.observation_id,
                "selected_kinds": [t.process_kind for t in tasks],
                "routing_weights": {t.process_kind: self.routing_weight(t.process_kind) for t in tasks},
            },
        )
        return tasks

    @staticmethod
    def _gev_question(kind: str, observation: GEVObservation) -> str:
        changes = "; ".join(observation.changes) or "no explicit change list"
        unknowns = "; ".join(observation.unknowns) or "none supplied"
        prompts = {
            "causal": f"What plausible causes best explain these observed changes: {changes}? Separate evidence from inference.",
            "temporal": f"What prior/future state transitions are most consistent with these changes: {changes}?",
            "adversarial": f"How could our interpretation of these changes be wrong: {changes}? Unknowns: {unknowns}.",
            "novelty": f"What unusual but testable cross-domain hypothesis is suggested by these changes: {changes}?",
        }
        return prompts.get(kind, f"Analyze observation {observation.observation_id} from the {kind} perspective.")

    def run(self, roots: Iterable[CognitiveTask], *, problem_family: str = "general") -> list[CognitiveResult]:
        queue = list(roots)
        results: list[CognitiveResult] = []
        spent = 0.0
        process_count = 0
        seen_ids: set[str] = set()

        while queue and process_count < self.budget.max_processes:
            task = queue.pop(0)
            if task.task_id in seen_ids:
                continue
            seen_ids.add(task.task_id)
            if task.depth > self.budget.max_depth:
                self._append("spawn.denied", {"task_id": task.task_id, "reason": "depth_limit"})
                continue
            if spent + task.estimated_cost > self.budget.max_cost:
                self._append("spawn.denied", {"task_id": task.task_id, "reason": "cost_budget"})
                continue
            worker = self._workers.get(task.process_kind)
            if worker is None:
                self._append("process.skipped", {"task_id": task.task_id, "reason": "unregistered_kind"})
                continue

            spent += task.estimated_cost
            process_count += 1
            self._append("process.started", {"task": self._task_payload(task), "spent": spent})
            result = worker(task)
            self._validate_result(task, result)
            results.append(result)
            self._append("process.completed", {"result": self._result_payload(result)})

            for request in result.spawn_requests:
                child = self._authorize_spawn(task, request, process_count=process_count, spent=spent)
                if child is not None:
                    queue.append(child)

        self._spawn_resonance(results, queue, process_count=process_count, spent=spent)
        while queue and process_count < self.budget.max_processes:
            task = queue.pop(0)
            if task.task_id in seen_ids or task.depth > self.budget.max_depth:
                continue
            if spent + task.estimated_cost > self.budget.max_cost:
                break
            worker = self._workers.get(task.process_kind)
            if worker is None:
                continue
            seen_ids.add(task.task_id)
            spent += task.estimated_cost
            process_count += 1
            result = worker(task)
            self._validate_result(task, result)
            results.append(result)
            self._append("process.completed", {"result": self._result_payload(result), "resonance": True})

        self._append(
            "run.completed",
            {"process_count": process_count, "spent": spent, "result_ids": [r.task_id for r in results]},
        )
        return results

    def _authorize_spawn(
        self,
        parent: CognitiveTask,
        request: SpawnRequest,
        *,
        process_count: int,
        spent: float,
    ) -> CognitiveTask | None:
        reason = None
        if request.process_kind not in self._workers:
            reason = "unregistered_kind"
        elif parent.depth + 1 > self.budget.max_depth:
            reason = "depth_limit"
        elif process_count >= self.budget.max_processes:
            reason = "process_budget"
        elif spent + request.estimated_cost > self.budget.max_cost:
            reason = "cost_budget"
        elif request.utility_ratio < self.budget.spawn_threshold:
            reason = "utility_below_threshold"

        payload = {
            "parent_task_id": parent.task_id,
            "process_kind": request.process_kind,
            "expected_value": request.expected_value,
            "estimated_cost": request.estimated_cost,
            "utility_ratio": request.utility_ratio,
        }
        if reason:
            self._append("spawn.denied", {**payload, "reason": reason})
            return None

        task_id = "CT-" + _digest({"parent": parent.task_id, "request": asdict(request), "depth": parent.depth + 1})[:20]
        child = CognitiveTask(
            task_id=task_id,
            process_kind=request.process_kind,
            question=request.question,
            context={"parent_context": dict(parent.context), "spawn_rationale": request.rationale},
            parent_task_id=parent.task_id,
            depth=parent.depth + 1,
            estimated_cost=request.estimated_cost,
        )
        self._append("spawn.authorized", {**payload, "child_task_id": task_id})
        return child

    def _spawn_resonance(
        self,
        results: list[CognitiveResult],
        queue: list[CognitiveTask],
        *,
        process_count: int,
        spent: float,
    ) -> None:
        if "synthesis" not in self._workers:
            return
        if process_count >= self.budget.max_processes or spent + 1.0 > self.budget.max_cost:
            return
        best: tuple[float, CognitiveResult, CognitiveResult] | None = None
        for i, left in enumerate(results):
            for right in results[i + 1 :]:
                if left.process_kind == right.process_kind:
                    continue
                lt = _tokens(" ".join(left.concepts) + " " + left.answer)
                rt = _tokens(" ".join(right.concepts) + " " + right.answer)
                union = lt | rt
                score = len(lt & rt) / len(union) if union else 0.0
                if score >= self.resonance_threshold and (best is None or score > best[0]):
                    best = (score, left, right)
        if best is None:
            return
        score, left, right = best
        question = (
            f"Synthesize the structurally resonant findings from {left.process_kind} and "
            f"{right.process_kind}; preserve contradictions and identify a testable joint hypothesis."
        )
        task_id = "CT-" + _digest({"resonance": [left.task_id, right.task_id], "score": score})[:20]
        queue.append(
            CognitiveTask(
                task_id,
                "synthesis",
                question,
                context={"left": self._result_payload(left), "right": self._result_payload(right), "resonance": score},
                depth=1,
                estimated_cost=1.0,
            )
        )
        self._append("resonance.detected", {"left": left.task_id, "right": right.task_id, "score": score})

    def record_outcome(
        self,
        result: CognitiveResult,
        *,
        reward: float,
        problem_family: str,
        evidence_refs: Iterable[str] = (),
    ) -> ProcessStats:
        reward = _clamp(reward, 0.0, 1.0)
        stats = self._apply_learning(result.process_kind, reward, problem_family, persist=False)
        self._append(
            "process.outcome",
            {
                "task_id": result.task_id,
                "process_kind": result.process_kind,
                "reward": reward,
                "problem_family": problem_family,
                "evidence_refs": list(evidence_refs),
                "new_weight": stats.weight,
                "runs": stats.runs,
                "mean_reward": stats.mean_reward,
            },
        )
        return stats

    def _apply_learning(self, process_kind: str, reward: float, problem_family: str, *, persist: bool) -> ProcessStats:
        stats = self._stats.setdefault(process_kind, ProcessStats())
        stats.runs += 1
        stats.reward_sum += reward
        stats.useful_runs += int(reward >= 0.70)
        stats.distinct_problem_families.add(problem_family)
        centered = reward - 0.5
        stats.weight = _clamp(stats.weight + self.learning_rate * centered, self.min_weight, self.max_weight)
        return stats

    def promotion_proposal(
        self,
        process_kind: str,
        *,
        min_runs: int = 20,
        min_mean_reward: float = 0.75,
        min_problem_families: int = 3,
    ) -> AetherlingPromotionProposal:
        stats = self._stats.get(process_kind, ProcessStats())
        reasons = []
        if stats.runs < min_runs:
            reasons.append(f"needs {min_runs - stats.runs} more verified runs")
        if stats.mean_reward < min_mean_reward:
            reasons.append(f"mean reward {stats.mean_reward:.3f} below {min_mean_reward:.3f}")
        if len(stats.distinct_problem_families) < min_problem_families:
            reasons.append(
                f"needs {min_problem_families - len(stats.distinct_problem_families)} more distinct problem families"
            )
        eligible = not reasons
        run_score = min(1.0, stats.runs / max(1, min_runs))
        reward_score = min(1.0, stats.mean_reward / max(1e-9, min_mean_reward))
        diversity_score = min(1.0, len(stats.distinct_problem_families) / max(1, min_problem_families))
        score = round((run_score + reward_score + diversity_score) / 3.0, 6)
        suggested_dna = {
            "soul_token": None,
            "origin": "victor_cognitive_ecology_promotion_proposal",
            "specialization": process_kind,
            "guardrails": [
                "No authority inheritance from parent process.",
                "No self-grant of capabilities or persistence.",
                "All consequential actions require VictorOS/AetherForge authorization.",
                "Preserve provenance and append-only experience receipts.",
            ],
            "routing_evidence": {
                "runs": stats.runs,
                "mean_reward": stats.mean_reward,
                "problem_families": sorted(stats.distinct_problem_families),
                "weight": stats.weight,
            },
        }
        proposal = AetherlingPromotionProposal(process_kind, eligible, score, tuple(reasons), suggested_dna)
        self._append("aetherling.promotion_proposed", asdict(proposal))
        return proposal

    @staticmethod
    def _validate_result(task: CognitiveTask, result: CognitiveResult) -> None:
        if result.task_id != task.task_id:
            raise ValueError("worker result task_id mismatch")
        if result.process_kind != task.process_kind:
            raise ValueError("worker result process_kind mismatch")
        if not result.answer.strip():
            raise ValueError("worker result answer is required")
        if result.proposed_action and result.proposed_action.get("authorized") is True:
            raise ValueError("cognitive workers may propose actions but may not self-authorize them")

    @staticmethod
    def _task_payload(task: CognitiveTask) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "process_kind": task.process_kind,
            "question": task.question,
            "context": dict(task.context),
            "parent_task_id": task.parent_task_id,
            "depth": task.depth,
            "estimated_cost": task.estimated_cost,
        }

    @staticmethod
    def _result_payload(result: CognitiveResult) -> dict[str, Any]:
        return {
            "task_id": result.task_id,
            "process_kind": result.process_kind,
            "answer": result.answer,
            "confidence": result.confidence,
            "evidence_refs": list(result.evidence_refs),
            "contradictions": list(result.contradictions),
            "concepts": list(result.concepts),
            "spawn_requests": [asdict(r) for r in result.spawn_requests],
            "proposed_action": dict(result.proposed_action) if result.proposed_action else None,
        }

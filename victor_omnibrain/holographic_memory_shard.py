import time
from typing import Any, Dict, List, Optional
from victor_omnibrain.victor_envelope import VictorEnvelope
from victor_omnibrain.trust_policy_engine import TrustPolicyEngine
from victor_omnibrain.save3_decay import SAVE3Decay

class HolographicMemoryShard:
    def __init__(self, compaction_threshold: int = 50):
        self.shards: List[VictorEnvelope] = []
        self.index: Dict[str, int] = {}
        self.compaction_threshold = compaction_threshold
        self.trust_engine = TrustPolicyEngine()

    def append_envelope(self, envelope: VictorEnvelope) -> str:
        # Verification logic now includes trust evaluation
        verdict = envelope.verify(time.time())
        if verdict["verdict"] != "PASS":
            raise ValueError(f"Invalid envelope rejected by memory: {verdict}")

        self.shards.append(envelope)
        if envelope.purpose:
            self.index[envelope.purpose] = len(self.shards) - 1

        # Trigger compaction if needed
        if len(self.shards) >= self.compaction_threshold:
            self.compact()

        return envelope.header_hash

    def decay_all(self, current_tick: float):
        """Apply SAVE3 exponential decay to all stored shards with trust policy"""
        for env in self.shards:
            env.save3.decay(current_tick)
            # Evaluate trust after decay
            trust_score = self.trust_engine.evaluate_trust(env, current_tick)
            env.trust_score = trust_score

    def reconstruct(self, purpose: str) -> Optional[Any]:
        """Retrieve the latest high-trust content for a specific purpose"""
        idx = self.index.get(purpose)
        if idx is None:
            return None

        env = self.shards[idx]
        env.last_access = time.time() # Update access time
        trust_score = self.trust_engine.evaluate_trust(env, time.time())

        if trust_score > 0.05:  # Minimum trust threshold
            return env.content
        elif self.trust_engine.should_quarantine(trust_score):
            # Logic for handling quarantined shards could go here
            return None

        return None

    def compact(self):
        """Simple compaction strategy: Keep latest high-trust shard per purpose"""
        new_shards = []
        seen_purposes = set()

        # Iterate backwards to find latest
        for env in reversed(self.shards):
            if env.purpose and env.purpose not in seen_purposes:
                if env.trust_score > 0.05:
                    new_shards.append(env)
                    seen_purposes.add(env.purpose)
            elif not env.purpose:
                # Keep un-purposed shards if trusted? Or just discard?
                # For now, keep trusted ones
                if env.trust_score > 0.05:
                    new_shards.append(env)

        self.shards = list(reversed(new_shards))

        # Rebuild index
        self.index = {}
        for i, env in enumerate(self.shards):
            if env.purpose:
                self.index[env.purpose] = i

    def ingest_dataset_sample(self, sample: Dict[str, Any], purpose: str = "training_data"):
        """Ingest dataset sample into memory."""
        # Create VictorEnvelope for dataset sample
        content = {
            'text': sample['text'],
            'image_shape': sample['image'].shape,
            'reasoning_trace': sample['reasoning'],
            'entropy_score': sample['entropy'],
            'depth_hint': sample['depth_hint']
        }

        envelope = VictorEnvelope(content=content, purpose=purpose)
        envelope.seal("Dataset ingestion", tick=time.time())

        # Append to memory
        return self.append_envelope(envelope)

    def telemetry(self) -> Dict[str, Any]:
        """Return memory statistics."""
        return {
            "shard_count": len(self.shards),
            "indexed_count": len(self.index),
            "avg_trust": sum(s.trust_score for s in self.shards) / len(self.shards) if self.shards else 0.0
        }

import math
import time
from typing import Any

class TrustPolicyEngine:
    def __init__(self, decay_half_life: float = 100.0, quarantine_threshold: float = 0.2):
        self.decay_half_life = decay_half_life
        self.quarantine_threshold = quarantine_threshold
        self.decay_rate = math.log(2) / decay_half_life

    def evaluate_trust(self, envelope: Any, current_tick: float) -> float:
        """Calculate trust score based on SAVE3 and access patterns"""
        # Assuming envelope has save3.score and last_access
        base_score = envelope.save3.score
        decay_factor = self._exponential_decay(envelope.last_access, current_tick)
        return base_score * decay_factor

    def should_quarantine(self, trust_score: float) -> bool:
        """Determine if shard should be quarantined"""
        return trust_score < self.quarantine_threshold

    def _exponential_decay(self, last_access: float, current_tick: float) -> float:
        """Exponential decay formula for SAVE3"""
        time_diff = current_tick - last_access
        return math.exp(-self.decay_rate * time_diff)
